/*
SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
Arquivo de Lógica (JavaScript) - Versão com Toasts, Dark Mode, Draft, Histórico
=================================================================================
*/

// =========================================================================
// 1. VARIÁVEIS GLOBAIS
// =========================================================================
let intervaloRelogio;
let relogioPausado = false;
let enderecoAnterior = null;
let buscaTimeout = null;
let buscaNomeTimeout = null;

// =========================================================================
// 2. TOASTS (substitui alert())
// =========================================================================
function mostrarToast(mensagem, tipo) {
    tipo = tipo || 'info';
    const container = document.getElementById('toastContainer');
    const id = 'toast_' + Date.now();
    const bgMap = {
        success: 'bg-success text-white',
        danger: 'bg-danger text-white',
        warning: 'bg-warning text-dark',
        info: 'bg-info text-dark'
    };
    const iconeMap = {
        success: '✅',
        danger: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    const html = `
    <div id="${id}" class="toast align-items-center ${bgMap[tipo] || bgMap.info} border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
        <div class="d-flex">
            <div class="toast-body">
                ${iconeMap[tipo] || ''} ${mensagem}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    </div>`;

    container.insertAdjacentHTML('beforeend', html);

    const el = document.getElementById(id);
    const toast = new bootstrap.Toast(el);
    toast.show();

    el.addEventListener('hidden.bs.toast', function() {
        el.remove();
    });
}

// =========================================================================
// 3. RELÓGIO
// =========================================================================
function atualizarDataHora() {
    if (relogioPausado) return;
    const agora = new Date();
    const dia = String(agora.getDate()).padStart(2, '0');
    const mes = String(agora.getMonth() + 1).padStart(2, '0');
    const ano = agora.getFullYear();
    document.getElementById('data_atendimento').value = `${ano}-${mes}-${dia}`;
    const horas = String(agora.getHours()).padStart(2, '0');
    const minutos = String(agora.getMinutes()).padStart(2, '0');
    document.getElementById('hora_atendimento').value = `${horas}:${minutos}`;
}

function iniciarRelogio() {
    relogioPausado = false;
    atualizarDataHora();
    intervaloRelogio = setInterval(atualizarDataHora, 60000);

    const campoData = document.getElementById('db_dn');
    if (campoData) {
        campoData.addEventListener('input', function() {
            mascaraData(this);
        });
    }
}

function pausarRelogio() {
    relogioPausado = true;
}

window.onload = function() {
    iniciarRelogio();
    carregarDraft();
    atualizarStatusGari();
    setInterval(atualizarStatusGari, 15000);
    aplicarTemaSalvo();

    // Listener para busca por nome ao digitar
    const campoNome = document.getElementById('db_nome');
    if (campoNome) {
        campoNome.addEventListener('input', function() {
            const val = this.value.trim();
            if (val.length >= 5) {
                debouncedBuscaNome(val);
            }
        });
    }
};

// =========================================================================
// 4. MÁSCARA DE DATA E CÁLCULO DE IDADE
// =========================================================================
function mascaraData(c) {
    let v = c.value.replace(/\D/g, "");
    if (v.length > 8) v = v.substring(0, 8);
    if (v.length > 4) {
        v = v.replace(/(\d{2})(\d{2})(\d{1,4})/, "$1/$2/$3");
    } else if (v.length > 2) {
        v = v.replace(/(\d{2})(\d{1,2})/, "$1/$2");
    }
    c.value = v;
    if (c.value.length === 10) {
        calcularIdade();
        setTimeout(() => {
            const campoIdade = document.getElementById('db_idade');
            if (campoIdade) campoIdade.focus();
        }, 10);
    }
}

function calcularIdade() {
    const d = document.getElementById('db_dn').value;
    if (!d || d.length !== 10) return;
    const partes = d.split('/');
    if (partes.length !== 3) return;
    const dataAmericana = `${partes[2]}-${partes[1]}-${partes[0]}`;
    const nasc = new Date(dataAmericana);
    const hoje = new Date();
    let idade = hoje.getFullYear() - nasc.getFullYear();
    if (hoje.getMonth() < nasc.getMonth() || (hoje.getMonth() === nasc.getMonth() && hoje.getDate() < nasc.getDate())) {
        idade--;
    }
    let resultadoFinal;
    if (idade > 0) {
        resultadoFinal = idade === 1 ? "1 Ano" : idade + " Anos";
    } else {
        let meses = (hoje.getFullYear() - nasc.getFullYear()) * 12 + (hoje.getMonth() - nasc.getMonth());
        if (hoje.getDate() < nasc.getDate()) meses--;
        if (meses > 0) {
            resultadoFinal = meses === 1 ? "1 Mês" : meses + " Meses";
        } else {
            const diferencaMilissegundos = hoje.getTime() - nasc.getTime();
            const dias = Math.floor(diferencaMilissegundos / (1000 * 60 * 60 * 24));
            resultadoFinal = dias === 1 ? "1 Dia" : dias + " Dias";
        }
    }
    document.getElementById('db_idade').value = resultadoFinal;
}

function validarDataReal(dataStr) {
    if (!dataStr) return true;
    let dia, mes, ano;
    if (dataStr.includes('-')) {
        const partes = dataStr.split('-');
        if (partes.length !== 3) return false;
        ano = parseInt(partes[0]); mes = parseInt(partes[1]); dia = parseInt(partes[2]);
    } else if (dataStr.includes('/')) {
        const partes = dataStr.split('/');
        if (partes.length !== 3) return false;
        dia = parseInt(partes[0]); mes = parseInt(partes[1]); ano = parseInt(partes[2]);
    } else {
        return false;
    }
    if (ano > 2100 || ano < 1900) return false;
    if (mes < 1 || mes > 12) return false;
    if (dia < 1 || dia > 31) return false;
    return true;
}

// =========================================================================
// 5. MÁSCARA CPF E SUS (COM DEBOUNCE NA BUSCA)
// =========================================================================
function executarCpf(c) {
    let numLimpo = c.value.replace(/\D/g, "");
    if (numLimpo.length > 11) numLimpo = numLimpo.substring(0, 11);
    let v = numLimpo;
    v = v.replace(/(\d{3})(\d)/, "$1.$2")
         .replace(/(\d{3})(\d)/, "$1.$2")
         .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    c.value = v;
    if (numLimpo.length === 11) {
        pausarRelogio();
        debouncedBusca(numLimpo);
    }
}

function soNumerosSus(c) {
    let numLimpo = c.value.replace(/\D/g, "").substring(0, 15);
    let v = numLimpo;
    if (v.length > 0) {
        v = v.replace(/^(\d{3})(\d)/, "$1 $2")
             .replace(/^(\d{3})\s(\d{4})(\d)/, "$1 $2 $3")
             .replace(/^(\d{3})\s(\d{4})\s(\d{4})(\d)/, "$1 $2 $3 $4");
    }
    c.value = v;
    if (numLimpo.length === 15) {
        pausarRelogio();
        debouncedBusca(numLimpo);
    }
}

// =========================================================================
// 6. DEBOUNCE — Aguarda 300ms de pausa na digitação antes de buscar
// =========================================================================
function debouncedBusca(id) {
    if (buscaTimeout) clearTimeout(buscaTimeout);
    buscaTimeout = setTimeout(function() {
        buscarNoBanco(id);
    }, 300);
}

// =========================================================================
// 7. VALIDAÇÃO CPF E SUS
// =========================================================================
function validarCpfFinal(c) {
    let cpf = c.value.replace(/\D/g, "");
    if (cpf === "") { c.classList.remove("invalid-input"); return true; }
    const invalidos = ["00000000000","11111111111","22222222222","33333333333","44444444444","55555555555","66666666666","77777777777","88888888888","99999999999"];
    if (cpf.length !== 11 || invalidos.includes(cpf)) { c.classList.add("invalid-input"); return false; }
    let soma = 0, resto;
    for (let i = 1; i <= 9; i++) soma += parseInt(cpf.substring(i-1, i)) * (11 - i);
    resto = (soma * 10) % 11;
    if ((resto === 10) || (resto === 11)) resto = 0;
    if (resto !== parseInt(cpf.substring(9, 10))) { c.classList.add("invalid-input"); return false; }
    soma = 0;
    for (let i = 1; i <= 10; i++) soma += parseInt(cpf.substring(i-1, i)) * (12 - i);
    resto = (soma * 10) % 11;
    if ((resto === 10) || (resto === 11)) resto = 0;
    if (resto !== parseInt(cpf.substring(10, 11))) { c.classList.add("invalid-input"); return false; }
    c.classList.remove("invalid-input");
    return true;
}

function validarSusFinal(c) {
    let sus = c.value.replace(/\D/g, "");
    if (sus === "") { c.classList.remove("invalid-input"); return true; }
    if (sus.length !== 15 || !['1','2','7','8','9'].includes(sus.charAt(0))) { c.classList.add("invalid-input"); return false; }
    let valido = false;
    if (['7','8','9'].includes(sus.charAt(0))) {
        let soma = 0;
        for (let i = 0; i < 15; i++) soma += parseInt(sus.charAt(i)) * (15 - i);
        valido = (soma % 11 === 0);
    } else {
        let pis = sus.substring(0, 11);
        let soma = 0;
        for (let i = 0; i < 11; i++) soma += parseInt(pis.charAt(i)) * (15 - i);
        let resto = soma % 11;
        let dv = 11 - resto;
        if (dv === 11) dv = 0;
        let resultado = dv === 10 ? pis + "001" + (11 - (soma + 2) % 11) : pis + "000" + dv;
        valido = (sus === resultado);
    }
    if (!valido) { c.classList.add("invalid-input"); return false; }
    c.classList.remove("invalid-input");
    c.value = sus.replace(/(\d{3})(\d{4})(\d{4})(\d{4})/, "$1 $2 $3 $4");
    return true;
}

// =========================================================================
// 8. MÁSCARA DE TELEFONE
// =========================================================================
function mascaraTel(c) {
    let v = c.value.replace(/\D/g, "");
    if (v.length > 11) v = v.substring(0, 11);
    if (v.length > 10) {
        v = v.replace(/^(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
    } else if (v.length > 5) {
        v = v.replace(/^(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3");
    } else if (v.length > 2) {
        v = v.replace(/^(\d{2})(\d{0,5})/, "($1) $2");
    }
    c.value = v;
}

// =========================================================================
// 9. VALIDAÇÃO DO FORMULÁRIO
// =========================================================================
function validarFormulario() {
    const nome = document.getElementById('db_nome').value.trim();
    const cpf = document.getElementById('db_cpf').value.trim();
    const sus = document.getElementById('db_sus').value.trim();
    const registro = document.getElementById('db_registro').value.trim();
    const sexoSelecionado = document.querySelector('input[name="sexo"]:checked');

    if (registro === "") {
        mostrarToast("O Número do Registro (Boletim) é obrigatório!", "warning");
        document.getElementById('db_registro').focus();
        return false;
    }
    if (nome.length < 3) {
        mostrarToast("O Nome do paciente é obrigatório e deve estar completo!", "warning");
        document.getElementById('db_nome').focus();
        return false;
    }
    if (cpf === "" && sus === "") {
        mostrarToast("É obrigatório informar o CPF ou o Cartão SUS do paciente!", "warning");
        document.getElementById('db_cpf').focus();
        return false;
    }
    if (!sexoSelecionado) {
        mostrarToast("Por favor, marque o Sexo do paciente (M ou F)!", "warning");
        return false;
    }
    return true;
}

// =========================================================================
// 10. FORMATAÇÃO CPF/SUS EXIBIÇÃO
// =========================================================================
function formatarCPFExibicao(v) {
    v = String(v).replace(/\D/g, "");
    if (v.length !== 11) return v;
    return v.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
}

function formatarSUSExibicao(v) {
    v = String(v).replace(/\D/g, "");
    if (v.length !== 15) return v;
    return v.replace(/(\d{3})(\d{4})(\d{4})(\d{4})/, "$1 $2 $3 $4");
}

// =========================================================================
// 11. BUSCA POR CPF/SUS NO BANCO + HISTÓRICO
// =========================================================================
function buscarNoBanco(id) {
    if (!id) return;

    async function executaBusca() {
        try {
            let paciente = await eel.buscar_paciente(id)();

            if (paciente.erro === "banco_travado") {
                mostrarToast("O sistema está ocupado. Apague o último dígito e digite novamente.", "warning");
                return;
            }
            if (paciente.erro === "nulo" || paciente.erro) {
                return;
            }

            preencherFormulario(paciente);
            mostrarHistorico(paciente.cpf || paciente.sus);

        } catch (erro) {
            console.error("Erro ao puxar dados do Python:", erro);
        }
    }
    executaBusca();
}

function preencherFormulario(paciente) {
    document.getElementById('db_nome').value = paciente.nome || "";
    document.getElementById('db_nome_social').value = paciente.nomeSocial || "";
    document.getElementById('db_dn').value = paciente.dn || "";
    calcularIdade();
    document.getElementById('db_mae').value = paciente.mae || "";
    document.getElementById('db_responsavel').value = paciente.responsavel || "";
    document.getElementById('db_tel').value = paciente.tel || "";
    document.getElementById('db_endereco').value = paciente.endereco || "";
    document.getElementById('db_numero').value = paciente.numero || "";
    document.getElementById('db_bairro').value = paciente.bairro || "";
    document.getElementById('db_cidade').value = paciente.cidade || "EXTREMOZ";
    document.getElementById('db_naturalidade').value = paciente.naturalidade || "";
    document.getElementById('db_ocupacao').value = paciente.ocupacao || "";

    if (paciente.cpf) document.getElementById('db_cpf').value = formatarCPFExibicao(paciente.cpf);
    if (paciente.sus) document.getElementById('db_sus').value = formatarSUSExibicao(paciente.sus);

    if (paciente.sexo) {
        const r = document.getElementById(paciente.sexo === "M" ? 'db_sexo_m' : 'db_sexo_f');
        if (r) r.checked = true;
    }
    if (paciente.civil) {
        const r = document.querySelector(`input[name="civil"][value="${paciente.civil}"]`);
        if (r) r.checked = true;
    }
    if (paciente.raca) {
        const r = document.querySelector(`input[name="cor"][value="${paciente.raca}"]`);
        if (r) r.checked = true;
    }

    document.getElementById('db_cpf').classList.remove("invalid-input");
    document.getElementById('db_sus').classList.remove("invalid-input");

    pausarRelogio();

    salvarEnderecoAnterior();
}

function salvarEnderecoAnterior() {
    enderecoAnterior = {
        endereco: document.getElementById('db_endereco').value,
        numero: document.getElementById('db_numero').value,
        bairro: document.getElementById('db_bairro').value,
        cidade: document.getElementById('db_cidade').value,
        estado: document.getElementById('db_estado').value,
        tel: document.getElementById('db_tel').value
    };
    const btn = document.getElementById('btnFamilia');
    if (btn) btn.style.display = 'inline-block';
}

// =========================================================================
// 12. HISTÓRICO DO PACIENTE
// =========================================================================
function mostrarHistorico(cpfOuSus) {
    if (!cpfOuSus) return;

    async function buscaHist() {
        try {
            const hist = await eel.buscar_historico(cpfOuSus)();
            const panel = document.getElementById('historyPanel');
            const list = document.getElementById('historyList');

            if (!hist || hist.length === 0) {
                panel.classList.remove('visible');
                return;
            }

            list.innerHTML = hist.map(function(h) {
                const proc = h.procedencia ? ` (${h.procedencia})` : '';
                return `<div class="history-item">📅 ${h.data} às ${h.hora}${proc}</div>`;
            }).join('');

            panel.classList.add('visible');
        } catch (e) {
            console.error("Erro ao buscar histórico:", e);
        }
    }
    buscaHist();
}

// =========================================================================
// 13. BUSCA POR NOME
// =========================================================================
function debouncedBuscaNome(termo) {
    if (buscaNomeTimeout) clearTimeout(buscaNomeTimeout);
    buscaNomeTimeout = setTimeout(function() {
        buscarPorNome(termo);
    }, 400);
}

function buscarPorNome(termo) {
    if (!termo || termo.length < 5) return;

    async function executa() {
        try {
            const resultados = await eel.buscar_por_nome(termo)();
            if (!resultados || resultados.length === 0) return;

            if (resultados.length === 1) {
                const r = resultados[0];
                if (r.cpf) {
                    buscarNoBanco(r.cpf);
                } else if (r.sus) {
                    buscarNoBanco(r.sus);
                }
                return;
            }

            let msg = "Pacientes encontrados com nome semelhante:\n\n";
            resultados.forEach(function(r, i) {
                msg += `${i+1}. ${r.nome} — CPF: ${r.cpf || '---'} SUS: ${r.sus || '---'} DN: ${r.dn || '---'}\n`;
            });
            msg += "\nDigite o CPF ou SUS para carregar os dados completos.";
            mostrarToast(msg, "info");
        } catch (e) {
            console.error("Erro na busca por nome:", e);
        }
    }
    executa();
}

// =========================================================================
// 14. COPIAR ENDEREÇO (FAMÍLIA)
// =========================================================================
function copiarEndereco() {
    if (!enderecoAnterior) {
        mostrarToast("Nenhum endereço anterior encontrado. Cadastre um paciente primeiro.", "warning");
        return;
    }

    document.getElementById('db_endereco').value = enderecoAnterior.endereco || "";
    document.getElementById('db_numero').value = enderecoAnterior.numero || "";
    document.getElementById('db_bairro').value = enderecoAnterior.bairro || "";
    document.getElementById('db_cidade').value = enderecoAnterior.cidade || "EXTREMOZ";
    document.getElementById('db_estado').value = enderecoAnterior.estado || "RN";
    if (enderecoAnterior.tel) {
        document.getElementById('db_tel').value = enderecoAnterior.tel;
    }

    mostrarToast("Endereço copiado do paciente anterior!", "success");
    document.getElementById('db_nome').focus();
}

// =========================================================================
// 15. DRAFT — AUTO-SALVAR RASCUNHO NO localStorage
// =========================================================================
function salvarDraft() {
    const campos = [
        'db_nome', 'db_nome_social', 'db_dn', 'db_naturalidade',
        'db_cpf', 'db_sus', 'db_registro', 'db_ocupacao', 'db_mae',
        'db_responsavel', 'db_tel', 'db_endereco', 'db_numero', 'db_bairro',
        'db_cidade', 'db_estado', 'data_atendimento', 'hora_atendimento'
    ];
    const draft = {};
    campos.forEach(function(id) {
        const el = document.getElementById(id);
        if (el) draft[id] = el.value;
    });

    const sexo = document.querySelector('input[name="sexo"]:checked');
    draft.sexo = sexo ? sexo.value : '';
    const civil = document.querySelector('input[name="civil"]:checked');
    draft.civil = civil ? civil.value : '';
    const raca = document.querySelector('input[name="cor"]:checked');
    draft.raca = raca ? raca.value : '';

    localStorage.setItem('draft_recepcao', JSON.stringify(draft));
    localStorage.setItem('draft_recepcao_time', Date.now());
}

function carregarDraft() {
    const draftRaw = localStorage.getItem('draft_recepcao');
    if (!draftRaw) return;

    const draftTime = localStorage.getItem('draft_recepcao_time');
    if (draftTime && (Date.now() - parseInt(draftTime) > 3600000)) {
        localStorage.removeItem('draft_recepcao');
        localStorage.removeItem('draft_recepcao_time');
        return;
    }

    try {
        const draft = JSON.parse(draftRaw);
        if (!draft.db_nome && !draft.db_cpf) return;

        Object.keys(draft).forEach(function(key) {
            const el = document.getElementById(key);
            if (el && typeof el.value !== 'undefined') {
                el.value = draft[key];
            }
        });

        if (draft.sexo) {
            const r = document.getElementById(draft.sexo === "M" ? 'db_sexo_m' : 'db_sexo_f');
            if (r) r.checked = true;
        }
        if (draft.civil) {
            const r = document.querySelector(`input[name="civil"][value="${draft.civil}"]`);
            if (r) r.checked = true;
        }
        if (draft.raca) {
            const r = document.querySelector(`input[name="cor"][value="${draft.raca}"]`);
            if (r) r.checked = true;
        }

        if (draft.db_dn && draft.db_dn.length === 10) calcularIdade();
        mostrarToast("Rascunho recuperado! Revise os dados antes de salvar.", "info");
    } catch (e) {
        console.error("Erro ao carregar draft:", e);
    }
}

function limparDraft() {
    localStorage.removeItem('draft_recepcao');
    localStorage.removeItem('draft_recepcao_time');
}

// Auto-salvar draft a cada 30 segundos
setInterval(salvarDraft, 30000);

// =========================================================================
// 16. VERIFICAÇÃO DE DUPLICATA
// =========================================================================
function verificarDuplicata(nome, dn) {
    if (!nome || !dn) return Promise.resolve(null);

    return new Promise(function(resolve) {
        async function executa() {
            try {
                const dups = await eel.verificar_duplicata(nome, dn)();
                resolve(dups);
            } catch (e) {
                console.error("Erro ao verificar duplicata:", e);
                resolve(null);
            }
        }
        executa();
    });
}

// =========================================================================
// 17. SALVAR PACIENTE
// =========================================================================
async function salvarPaciente() {
    const dataNasc = document.getElementById('db_dn').value;
    if (!validarDataReal(dataNasc)) {
        mostrarToast("DATA INVÁLIDA! Verifique dia, mês e ano (Ex: 10/05/2007).", "danger");
        document.getElementById('db_dn').focus();
        return;
    }
    if (!validarFormulario()) return;

    // Verifica duplicata antes de salvar
    const nome = document.getElementById('db_nome').value.trim().toUpperCase();
    const dups = await verificarDuplicata(nome, dataNasc);
    if (dups && dups.length > 0 && dups[0].cpf !== document.getElementById('db_cpf').value.replace(/\D/g, "")) {
        const confirma = confirm(
            `⚠️ ATENÇÃO: Já existe um paciente com o mesmo nome e data de nascimento!\n\n` +
            `Paciente: ${dups[0].nome}\n` +
            `CPF: ${dups[0].cpf || '---'}\n` +
            `SUS: ${dups[0].sus || '---'}\n\n` +
            `Deseja continuar mesmo assim?`
        );
        if (!confirma) return;
    }

    const botaoSalvar = document.querySelector('.btn-save');
    botaoSalvar.disabled = true;
    botaoSalvar.style.backgroundColor = "#ffc107";
    botaoSalvar.style.color = "#000";
    botaoSalvar.innerHTML = "⏳ Salvando no Banco...";

    const procElement = document.querySelector('input[name="procedencia"]:checked');
    const procedenciaValor = procElement ? procElement.value : "";

    const pacoteDados = {
        data_atendimento: document.getElementById('data_atendimento').value,
        hora_atendimento: document.getElementById('hora_atendimento').value,
        cpf: document.getElementById('db_cpf').value.replace(/\D/g, ""),
        sus: document.getElementById('db_sus').value.replace(/\D/g, ""),
        registro: document.getElementById('db_registro').value,
        nome: document.getElementById('db_nome').value.toUpperCase(),
        nomeSocial: document.getElementById('db_nome_social').value.toUpperCase(),
        dn: document.getElementById('db_dn').value,
        idade: document.getElementById('db_idade').value,
        naturalidade: document.getElementById('db_naturalidade').value.toUpperCase(),
        sexo: (document.querySelector('input[name="sexo"]:checked') || {}).value || "",
        civil: (document.querySelector('input[name="civil"]:checked') || {}).value || "",
        raca: (document.querySelector('input[name="cor"]:checked') || {}).value || "",
        ocupacao: document.getElementById('db_ocupacao').value.toUpperCase(),
        mae: document.getElementById('db_mae').value.toUpperCase(),
        responsavel: document.getElementById('db_responsavel').value.toUpperCase(),
        tel: document.getElementById('db_tel').value,
        endereco: document.getElementById('db_endereco').value.toUpperCase(),
        numero: document.getElementById('db_numero').value,
        bairro: document.getElementById('db_bairro').value.toUpperCase(),
        cidade: document.getElementById('db_cidade').value.toUpperCase(),
        estado: document.getElementById('db_estado').value.toUpperCase(),
        procedencia: procedenciaValor
    };

    async function executaSalvar() {
        try {
            let data = await eel.salvar(pacoteDados)();
            if (data.status === "sucesso") {
                if (data.registro_gerado) {
                    document.getElementById('db_registro').value = data.registro_gerado;
                }
                botaoSalvar.style.backgroundColor = "#0056b3";
                botaoSalvar.style.color = "#fff";
                botaoSalvar.innerHTML = "✅ SALVO COM SUCESSO!";

                mostrarToast(`Salvo! Ficha [${data.registro_gerado}] registrada no sistema.`, "success");

                document.getElementById('statusUltimoSave').textContent =
                    `Último save: ${new Date().toLocaleTimeString('pt-BR')} | Ficha #${data.registro_gerado}`;

                limparDraft();
                salvarEnderecoAnterior();

                setTimeout(function() {
                    if (botaoSalvar) {
                        botaoSalvar.disabled = false;
                        botaoSalvar.style.backgroundColor = "";
                        botaoSalvar.style.color = "";
                        botaoSalvar.innerHTML = "💾 Salvar (F2)";
                    }
                }, 3000);

            } else {
                mostrarToast("Erro ao salvar: " + data.mensagem, "danger");
                botaoSalvar.disabled = false;
                botaoSalvar.style.backgroundColor = "";
                botaoSalvar.style.color = "";
                botaoSalvar.innerHTML = "💾 Salvar (F2)";
            }
        } catch (erro) {
            console.error('Erro do sistema Eel:', erro);
            mostrarToast("Erro ao comunicar com o servidor. O banco pode estar ocupado.", "danger");
            botaoSalvar.disabled = false;
            botaoSalvar.style.backgroundColor = "";
            botaoSalvar.style.color = "";
            botaoSalvar.innerHTML = "💾 Salvar (F2)";
        }
    }
    executaSalvar();
}

// =========================================================================
// 18. LIMPAR TUDO
// =========================================================================
function limparTudo() {
    const camposParaLimpar = [
        'db_nome', 'db_nome_social', 'db_dn', 'db_idade', 'db_naturalidade',
        'db_cpf', 'db_sus', 'db_registro', 'db_ocupacao', 'db_mae',
        'db_responsavel', 'db_tel', 'db_endereco', 'db_numero', 'db_bairro'
    ];

    camposParaLimpar.forEach(function(id) {
        const caixa = document.getElementById(id);
        if (caixa) caixa.value = '';
    });

    if (document.getElementById('db_cidade')) document.getElementById('db_cidade').value = "EXTREMOZ";
    if (document.getElementById('db_estado')) document.getElementById('db_estado').value = "RN";

    const todasBolinhas = document.querySelectorAll('input[type="radio"]:not([name="procedencia"])');
    todasBolinhas.forEach(function(bolinha) { bolinha.checked = false; });

    const radioNormal = document.getElementById('radioNormal');
    if (radioNormal) radioNormal.checked = true;

    document.getElementById('db_cpf').classList.remove("invalid-input");
    document.getElementById('db_sus').classList.remove("invalid-input");

    const botaoSalvar = document.querySelector('.btn-save');
    if (botaoSalvar) {
        botaoSalvar.disabled = false;
        botaoSalvar.style.backgroundColor = "";
        botaoSalvar.style.color = "";
        botaoSalvar.innerHTML = "💾 Salvar (F2)";
    }

    document.getElementById('historyPanel').classList.remove('visible');

    atualizarDataHora();
    if (intervaloRelogio) clearInterval(intervaloRelogio);
    iniciarRelogio();

    limparDraft();

    document.getElementById('db_cpf').focus();
}

// =========================================================================
// 19. DARK MODE
// =========================================================================
function toggleDarkMode() {
    const body = document.body;
    const btn = document.getElementById('btnDarkMode');
    const isDark = body.classList.toggle('dark-mode');

    btn.textContent = isDark ? '☀️ Claro' : '🌙 Escuro';
    localStorage.setItem('darkmode_recepcao', isDark ? '1' : '0');
}

function aplicarTemaSalvo() {
    const saved = localStorage.getItem('darkmode_recepcao');
    if (saved === '1') {
        document.body.classList.add('dark-mode');
        const btn = document.getElementById('btnDarkMode');
        if (btn) btn.textContent = '☀️ Claro';
    }
}

// =========================================================================
// 20. STATUS DO GARI DA NUVEM
// =========================================================================
function atualizarStatusGari() {
    async function checa() {
        try {
            const status = await eel.status_gari()();
            const el = document.getElementById('statusGari');
            if (el) {
                const dot = status === 'rodando' ? 'online' : 'offline';
                const label = status === 'rodando' ? 'Gari: Ativo' :
                              status === 'erro' ? 'Gari: Erro' : 'Gari: --';
                el.innerHTML = `<span class="status-dot ${dot}"></span> ${label}`;
            }
        } catch (e) {
            const el = document.getElementById('statusConexao');
            if (el) {
                el.innerHTML = `<span class="status-dot offline"></span> Servidor Offline`;
            }
        }
    }
    checa();
}

// =========================================================================
// 21. ATALHO DE TECLADO F2
// =========================================================================
document.addEventListener('keydown', function(event) {
    if (event.key === 'F2') {
        event.preventDefault();
        const botaoSalvar = document.querySelector('.btn-save');
        if (botaoSalvar && !botaoSalvar.disabled) {
            salvarPaciente();
        }
    }
});
