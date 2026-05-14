/*
=========================================================================
SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
Arquivo de Lógica (JavaScript) - VERSÃO FINAL INTEGRADORA E DIDÁTICA
=========================================================================
*/

// =========================================================================
// 1. VARIÁVEIS GLOBAIS (A memória do sistema)
// =========================================================================
let intervaloRelogio; // Caixa que vai guardar o "motor" do nosso timer
let relogioPausado = false; // O "Freio de mão". Inicia em false para o relógio rodar livre!

// =========================================================================
// 2. A ENGRENAGEM DO RELÓGIO E A TRAVA DE REGISTRO
// =========================================================================
function atualizarDataHora() {
    // 1ª Regra: Se a recepcionista começou a digitar, a hora congela na tela.
    if (relogioPausado) return;
    
    // O comando 'new Date()' acessa o sistema operacional para pegar o tempo exato de agora.
    const agora = new Date();
    
    // --- PREPARANDO A DATA ---
    const dia = String(agora.getDate()).padStart(2, '0');
    const mes = String(agora.getMonth() + 1).padStart(2, '0');
    const ano = agora.getFullYear();
    document.getElementById('data_atendimento').value = `${ano}-${mes}-${dia}`;
    
    // --- PREPARANDO A HORA ---
    const horas = String(agora.getHours()).padStart(2, '0');
    const minutos = String(agora.getMinutes()).padStart(2, '0');
    document.getElementById('hora_atendimento').value = `${horas}:${minutos}`;
}

// Inicia o loop (timer) que atualiza a hora a cada 60.000 milissegundos (1 minuto).
function iniciarRelogio() {
    relogioPausado = false; 
    atualizarDataHora(); // Roda 1 vez na hora pra não nascer em branco.
    intervaloRelogio = setInterval(atualizarDataHora, 60000);

    // 🛡️ MÁGICA: Conserta o seu HTML e adiciona o gatilho automático!
    const campoData = document.getElementById('db_dn');
    if (campoData) {
        // Transforma o campo em texto restrito a 10 espaços e tira a "agenda" do navegador
        campoData.setAttribute('type', 'text');
        campoData.setAttribute('maxlength', '10');
        campoData.setAttribute('placeholder', 'DD/MM/AAAA');
        
        // 🚀 O GATILHO QUE FALTAVA: A cada número que você digita, ele chama a máscara automaticamente!
        campoData.addEventListener('input', function() {
            mascaraData(this);
        });
    }
}

// Impede que a hora mude enquanto o usuário preenche dados retroativos.
function pausarRelogio() {
    relogioPausado = true;
}

// Assim que a janela inteira terminar de carregar, liga o motor do relógio.
window.onload = iniciarRelogio;

// =========================================================================
// 3. CÁLCULO INTELIGENTE DE IDADE E MÁSCARA DE DATA COM PULO AUTOMÁTICO
// =========================================================================
function mascaraData(c) {
    // 1. Pega apenas os números puros
    let v = c.value.replace(/\D/g, ""); 
    
    // 2. Trava Absoluta: Não permite passar de 8 números puros (DDMMAAAA)
    if (v.length > 8) {
        v = v.substring(0, 8); 
    }

    // 3. Formatação Progressiva (A regex que coloca as barras)
    if (v.length > 4) {
        v = v.replace(/(\d{2})(\d{2})(\d{1,4})/, "$1/$2/$3");
    } else if (v.length > 2) {
        v = v.replace(/(\d{2})(\d{1,2})/, "$1/$2");
    }
    
    // 4. Devolve o texto perfeitamente mascarado (As barras aparecem sozinhas)
    c.value = v;

    // 5. O PULO AUTOMÁTICO: Chegou a 10 caracteres (Ex: 14/12/1995)? 
    if (c.value.length === 10) {
        calcularIdade(); // Calcula a idade imediatamente
        
        // Pula para a caixa de Idade de forma suave em milissegundos
        setTimeout(() => {
            const campoIdade = document.getElementById('db_idade');
            if (campoIdade) campoIdade.focus();
        }, 10);
    }
}

function calcularIdade() {
    const d = document.getElementById('db_dn').value;
    if (!d || d.length !== 10) return; // Só calcula se a data estiver completamente digitada (DD/MM/AAAA)
    
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

    // Se o formato veio travado em AAAA-MM-DD
    if (dataStr.includes('-')) {
        const partes = dataStr.split('-');
        if (partes.length !== 3) return false;
        ano = parseInt(partes[0]);
        mes = parseInt(partes[1]);
        dia = parseInt(partes[2]);
    } 
    // Se o formato for o nosso do Brasil DD/MM/AAAA
    else if (dataStr.includes('/')) {
        const partes = dataStr.split('/');
        if (partes.length !== 3) return false;
        dia = parseInt(partes[0]);
        mes = parseInt(partes[1]);
        ano = parseInt(partes[2]);
    } else {
        return false;
    }

    // A TRAVA DE SÉCULO: Não salva se o ano for maluco (Maior que 2100 ou menor que 1900)
    if (ano > 2100 || ano < 1900) return false;
    if (mes < 1 || mes > 12) return false;
    if (dia < 1 || dia > 31) return false;

    return true;
}

// =========================================================================
// 4. MÁSCARA DINÂMICA DO CPF E SUS (COM GATILHO INSTANTÂNEO DE BUSCA)
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
        buscarNoBanco(numLimpo);
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
        buscarNoBanco(numLimpo);
    }
}

// =========================================================================
// 5. VALIDAÇÃO MATEMÁTICA DO CPF E SUS 
// =========================================================================
function validarCpfFinal(c) {
    let cpf = c.value.replace(/\D/g, "");
    if (cpf === "") {
        c.classList.remove("invalid-input");
        return true;
    }
    
    const invalidos = ["00000000000", "11111111111", "22222222222", "33333333333", "44444444444", "55555555555", "66666666666", "77777777777", "88888888888", "99999999999"];
    
    if (cpf.length !== 11 || invalidos.includes(cpf)) {
        c.classList.add("invalid-input"); 
        return false;
    }
    
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
    if (sus === "") {
        c.classList.remove("invalid-input");
        return true;
    }
    
    if (sus.length !== 15 || !['1', '2', '7', '8', '9'].includes(sus.charAt(0))) {
        c.classList.add("invalid-input");
        return false;
    }
    
    let valido = false;
    if (['7', '8', '9'].includes(sus.charAt(0))) {
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
    
    if (!valido) {
        c.classList.add("invalid-input");
        return false;
    }
    
    c.classList.remove("invalid-input");
    c.value = sus.replace(/(\d{3})(\d{4})(\d{4})(\d{4})/, "$1 $2 $3 $4");
    return true;
}

// =========================================================================
// 6. MÁSCARA DINÂMICA DE TELEFONE
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
// 7. O INSPETOR DE FORMULÁRIO (Validações Obrigatórias antes de Salvar)
// =========================================================================
function validarFormulario() {
    const nome = document.getElementById('db_nome').value.trim();
    const cpf = document.getElementById('db_cpf').value.trim();
    const sus = document.getElementById('db_sus').value.trim();
    const registro = document.getElementById('db_registro').value.trim();
    const sexoSelecionado = document.querySelector('input[name="sexo"]:checked');
    
    if (registro === "") {
        alert("⚠ O Número do Registro (Boletim) é obrigatório!");         
        document.getElementById('db_registro').focus();
        return false;
    }
    if (nome.length < 3) {
        alert("⚠ O Nome do paciente é obrigatório e deve estar completo!");
        document.getElementById('db_nome').focus();
        return false;
    }
    if (cpf === "" && sus === "") {
        alert("⚠ É obrigatório informar o CPF ou o Cartão SUS do paciente!");
        document.getElementById('db_cpf').focus();
        return false;
    }
    if (!sexoSelecionado) {
        alert("⚠ Por favor, marque o Sexo do paciente (M ou F)!");         
        return false;
    }
    return true;
}

// =========================================================================
// 8. INTEGRAÇÃO COM O BANCO DE DADOS E AUTO-PREENCHIMENTO INSTANTÂNEO
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

function buscarNoBanco(id) {
    if (!id) return;

    async function executaBusca() {
        try {
            console.log(`Buscando dados instantaneamente para o ID: ${id}`);
            let paciente = await eel.buscar_paciente(id)();
            
            if (paciente.erro === "banco_travado") {
                alert("⚠️ O sistema está ocupado no momento. Por favor, apague o último dígito do CPF/SUS e digite novamente.");
                return;
            }

            if (paciente.erro === "nulo" || paciente.erro) {
                console.log("Paciente é novo, não existe no banco de dados.");
                return; 
            }
            
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
            console.log("Paciente carregado com sucesso!");
            
        } catch (erro) {
            console.error("Erro ao puxar dados do Python:", erro);
        }
    }
    executaBusca();
}

// =========================================================================
// 9. SALVAR PACIENTE NO BANCO DE DADOS (Botão de Envio Anti-Colisão)
// =========================================================================
function salvarPaciente() {
    const dataNasc = document.getElementById('db_dn').value;
    if (!validarDataReal(dataNasc)) {
        alert("❌ DATA INVÁLIDA! Verifique se digitou o dia, mês e ano corretamente (Ex: 10/05/2007).");
        document.getElementById('db_dn').focus();
        return;
    }

    if (!validarFormulario()) return;
    
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
            if(data.status === "sucesso") {
                if(data.registro_gerado) {
                    document.getElementById('db_registro').value = data.registro_gerado;
                }
                botaoSalvar.style.backgroundColor = "#0056b3";
                botaoSalvar.style.color = "#fff";
                botaoSalvar.innerHTML = "✅ SALVO COM SUCESSO!";
                alert(`✅ Salvo com sucesso! Ficha número [ ${data.registro_gerado} ] registrada no sistema. Já pode Imprimir!`);
            } else {
                alert("❌ Erro ao salvar no banco de dados: " + data.mensagem);
                botaoSalvar.disabled = false; 
                botaoSalvar.style.backgroundColor = "";
                botaoSalvar.style.color = "";
                botaoSalvar.innerHTML = "💾 Salvar (F2)";
            }
        } catch (erro) {
            console.error('Erro do sistema Eel:', erro);
            alert("⚠ Ocorreu um erro ao comunicar com o servidor. O arquivo de banco de dados pode estar trancado.");         
            botaoSalvar.disabled = false;
            botaoSalvar.style.backgroundColor = "";
            botaoSalvar.style.color = "";
            botaoSalvar.innerHTML = "💾 Salvar (F2)";
        }
    }
    executaSalvar();
}

// =========================================================================
// 10. LIMPEZA INTELIGENTE (Resetar tela para o próximo paciente)
// =========================================================================
function limparTudo() {
    const camposParaLimpar = [
        'db_nome', 'db_nome_social', 'db_dn', 'db_idade', 'db_naturalidade',
        'db_cpf', 'db_sus', 'db_registro', 'db_ocupacao', 'db_mae',
        'db_responsavel', 'db_tel', 'db_endereco', 'db_numero', 'db_bairro'
    ];
    
    camposParaLimpar.forEach(id => {
        const caixa = document.getElementById(id);
        if (caixa) caixa.value = '';
    });
    
    if (document.getElementById('db_cidade')) document.getElementById('db_cidade').value = "EXTREMOZ";
    if (document.getElementById('db_estado')) document.getElementById('db_estado').value = "RN";
    
    const todasBolinhas = document.querySelectorAll('input[type="radio"]:not([name="procedencia"])');
    todasBolinhas.forEach(bolinha => bolinha.checked = false);
    
    const radioNormal = document.getElementById('radioNormal');
    if (radioNormal) radioNormal.checked = true;
    
    document.getElementById('db_cpf').classList.remove("invalid-input");
    document.getElementById('db_sus').classList.remove("invalid-input");
    
    const botaoSalvar = document.querySelector('.btn-save');
    if(botaoSalvar) {
        botaoSalvar.disabled = false;
        botaoSalvar.style.backgroundColor = "";
        botaoSalvar.style.color = "";
        botaoSalvar.innerHTML = "💾 Salvar (F2)";
    }
    
    atualizarDataHora();
    if (intervaloRelogio) clearInterval(intervaloRelogio);
    iniciarRelogio();
    
    document.getElementById('db_cpf').focus(); 
}

// =========================================================================
// 11. ATALHOS DO TECLADO (Ação do F2)
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