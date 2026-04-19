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
}

// Impede que a hora mude enquanto o usuário preenche dados retroativos.
function pausarRelogio() {
    relogioPausado = true;
}

// Assim que a janela inteira terminar de carregar, liga o motor do relógio.
window.onload = iniciarRelogio;

// =========================================================================
// 3. CÁLCULO INTELIGENTE DE IDADE (Lógica de Pediatria)
// =========================================================================
function calcularIdade() {
    const d = document.getElementById('db_dn').value;
    if (!d) return; // Se a data estiver vazia, cancela a ação.
    
    const nasc = new Date(d);
    const hoje = new Date();
    
    // Calcula a idade base em anos.
    let idade = hoje.getFullYear() - nasc.getFullYear();
    
    // Regra do Aniversário: Se o mês ou dia ainda não chegou neste ano, tira 1 ano.
    if (hoje.getMonth() < nasc.getMonth() || (hoje.getMonth() === nasc.getMonth() && hoje.getDate() < nasc.getDate())) {
        idade--;
    }
    
    let resultadoFinal;
    
    if (idade > 0) {
        // CORREÇÃO DO PLURAL
        resultadoFinal = idade === 1 ? "1 Ano" : idade + " Anos";
    } else {
        // LÓGICA DE BEBÊS (Menos de 1 ano de idade)
        let meses = (hoje.getFullYear() - nasc.getFullYear()) * 12 + (hoje.getMonth() - nasc.getMonth());
        
        // Se o dia do "mêsversário" ainda não chegou neste mês, subtrai 1 mês.
        if (hoje.getDate() < nasc.getDate()) meses--;
        
        if (meses > 0) {
            resultadoFinal = meses === 1 ? "1 Mês" : meses + " Meses";
        } else {
            // RECÉM-NASCIDOS: Calculamos em dias matemáticos (milissegundos)
            const diferencaMilissegundos = hoje.getTime() - nasc.getTime();
            const dias = Math.floor(diferencaMilissegundos / (1000 * 60 * 60 * 24));
            resultadoFinal = dias === 1 ? "1 Dia" : dias + " Dias";
        }
    }
    
    // Injeta o prato pronto na caixa HTML de Idade.
    document.getElementById('db_idade').value = resultadoFinal;
}

// =========================================================================
// 4. MÁSCARA DINÂMICA DO CPF E SUS (Com Gatilho de Busca)
// =========================================================================
function executarCpf(c) {
    // Pega o que foi digitado, acha tudo que NÃO é número (\D) e apaga.
    let v = c.value.replace(/\D/g, "");
    
    // Trava de Tamanho.
    if (v.length > 11) v = v.substring(0, 11);
    
    // Máscara Progressiva: Injeta os pontos e traço.
    v = v.replace(/(\d{3})(\d)/, "$1.$2")
         .replace(/(\d{3})(\d)/, "$1.$2")
         .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
         
    c.value = v;
    
    // Gatilho do Banco: Se bateu 11 dígitos, aciona o radar no Python!
    if (v.replace(/\D/g, "").length === 11) {
        pausarRelogio();
        buscarNoBanco(v);
    }
}

function soNumerosSus(c) {
    let v = c.value.replace(/\D/g, "").substring(0, 15);
    c.value = v;
    if (v.length === 15) {
        pausarRelogio();
        buscarNoBanco(v);
    }
}

// =========================================================================
// 5. VALIDAÇÃO MATEMÁTICA DO CPF E SUS (Módulo 11)
// =========================================================================
function validarCpfFinal(c) {
    let cpf = c.value.replace(/\D/g, "");
    if (cpf === "") {
        c.classList.remove("invalid-input");
        return true;
    }
    
    // A LISTA NEGRA: Sequências que enganam a matemática.
    const invalidos = ["00000000000", "11111111111", "22222222222", "33333333333", "44444444444", "55555555555", "66666666666", "77777777777", "88888888888", "99999999999"];
    
    if (cpf.length !== 11 || invalidos.includes(cpf)) {
        c.classList.add("invalid-input"); // Pinta de vermelho no CSS
        return false;
    }
    
    // Matemática da Receita Federal
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
    
    // ABSOLVIÇÃO: Se passou, tira o vermelho e autoriza.
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
    
    // MATEMÁTICA 1: Cartões Definitivos (7, 8 ou 9)
    if (['7', '8', '9'].includes(sus.charAt(0))) {
        let soma = 0;
        for (let i = 0; i < 15; i++) soma += parseInt(sus.charAt(i)) * (15 - i);
        valido = (soma % 11 === 0);
    } 
    // MATEMÁTICA 2: Cartões Provisórios (1 ou 2)
    else {
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
        v = v.replace(/^(\d{2})(\d{5})(\d{4})/, "($1) $2-$3"); // Celular
    } else if (v.length > 5) {
        v = v.replace(/^(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3"); // Fixo
    } else if (v.length > 2) {
        v = v.replace(/^(\d{2})(\d{0,5})/, "($1) $2"); // Só DDD
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
// 8. INTEGRAÇÃO COM O BANCO DE DADOS (API Assíncrona via Fetch)
// =========================================================================
function formatarCPFExibicao(v) {
    v = v.replace(/\D/g, "");
    if (v.length !== 11) return v;
    return v.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
}

function formatarSUSExibicao(v) {
    v = v.replace(/\D/g, "");
    if (v.length !== 15) return v;
    return v.replace(/(\d{3})(\d{4})(\d{4})(\d{4})/, "$1 $2 $3 $4");
}

function buscarNoBanco(id) {
    // O 'fetch' faz uma requisição silenciosa para a rota '/buscar/' do servidor Python.
    fetch('/buscar/' + id)
        .then(resposta => resposta.json())
        .then(paciente => {
            if (paciente.erro) return; // Paciente novo, mantem a tela vazia
            
            // Injeta os dados mágicamente nas caixas de texto
            document.getElementById('db_nome').value = paciente.nome || "";
            document.getElementById('db_nome_social').value = paciente.nomeSocial || "";
            document.getElementById('db_dn').value = paciente.dn || "";
            document.getElementById('db_idade').value = paciente.idade || "";
            calcularIdade(); // Recalcula idade com base no ano atual
            
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
            
            // Marca automaticamente os botões Radio
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
            
            // Remove bordas vermelhas caso o CPF/SUS venha do banco
            document.getElementById('db_cpf').classList.remove("invalid-input");
            document.getElementById('db_sus').classList.remove("invalid-input");
        })
        .catch(erro => console.log("Erro na rede ou paciente inexistente.", erro));
}

// =========================================================================
// 9. SALVAR PACIENTE (O Botão de Envio Anti-Colisão)
// =========================================================================
function salvarPaciente() {
    if (!validarFormulario()) return;
    
    // MUTAÇÃO VISUAL E TRAVA ANTI-METRALHADORA
    const botaoSalvar = document.querySelector('.btn-save');
    botaoSalvar.disabled = true; // Impede duplo clique e "Efeito Cartesiano"
    botaoSalvar.style.backgroundColor = "#ffc107";
    botaoSalvar.style.color = "#000";
    botaoSalvar.innerHTML = "⏳ Salvando no Banco...";
    
    const procElement = document.querySelector('input[name="procedencia"]:checked');
    const procedenciaValor = procElement ? procElement.value : "";
    
    // Empacotamento JSON (Objeto chave-valor) que o Python vai ler
    const pacoteDados = {
        data_atendimento: document.getElementById('data_atendimento').value,
        hora_atendimento: document.getElementById('hora_atendimento').value,
        cpf: document.getElementById('db_cpf').value.replace(/\D/g, ""), // Manda limpo para o banco
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
    
    fetch('/salvar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pacoteDados)
    })
    .then(resposta => resposta.json())
    .then(data => {
        if(data.status === "sucesso") {
            // Mantém o número na tela pra recepcionista ver
            if(data.registro_gerado) {
                document.getElementById('db_registro').value = data.registro_gerado;
            }
            
            // Sucesso Visual (Fica Azul)
            botaoSalvar.style.backgroundColor = "#0056b3";
            botaoSalvar.style.color = "#fff";
            botaoSalvar.innerHTML = "✅ SALVO COM SUCESSO!";
            
            alert(`✅ Salvo com sucesso! Ficha número [ ${data.registro_gerado} ] registrada no sistema. Já pode Imprimir!`);
        } else {
            alert("❌ Erro ao salvar no banco de dados: " + data.mensagem);
            botaoSalvar.disabled = false; // Destrava pra poder tentar corrigir o erro
            botaoSalvar.style.backgroundColor = "";
            botaoSalvar.style.color = "";
            botaoSalvar.innerHTML = "💾 Salvar (F2)";
        }
    })
    .catch(erro => {
        console.error('Erro na rede:', erro);
        alert("⚠ O Servidor do Hospital parece estar fora do ar.");         
        botaoSalvar.disabled = false;
        botaoSalvar.style.backgroundColor = "";
        botaoSalvar.style.color = "";
        botaoSalvar.innerHTML = "💾 Salvar (F2)";
    });
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
    
    // Preserva padrões
    if (document.getElementById('db_cidade')) document.getElementById('db_cidade').value = "EXTREMOZ";
    if (document.getElementById('db_estado')) document.getElementById('db_estado').value = "RN";
    
    // Desmarca Radios
    const todasBolinhas = document.querySelectorAll('input[type="radio"]:not([name="procedencia"])');
    todasBolinhas.forEach(bolinha => bolinha.checked = false);
    
    const radioNormal = document.getElementById('radioNormal');
    if (radioNormal) radioNormal.checked = true;
    
    // Restaura o botão de salvar
    const botaoSalvar = document.querySelector('.btn-save');
    if(botaoSalvar) {
        botaoSalvar.disabled = false;
        botaoSalvar.style.backgroundColor = "";
        botaoSalvar.style.color = "";
        botaoSalvar.innerHTML = "💾 Salvar (F2)";
    }
    
    // Despausa e roda o relógio para a hora exata
    atualizarDataHora();
    if (intervaloRelogio) clearInterval(intervaloRelogio);
    iniciarRelogio();
    
    document.getElementById('db_cpf').focus(); // Foco ergonômico no CPF
}

// =========================================================================
// 11. ATALHOS DO TECLADO (F2)
// =========================================================================
document.addEventListener('keydown', function(event) {
    if (event.key === 'F2') {
        event.preventDefault(); // Corta o padrão do navegador
        const botaoSalvar = document.querySelector('.btn-save');
        
        // A Catraca Final: Só deixa rodar a função se o botão não estiver congelado pelo milissegundo inicial.
        if (botaoSalvar && !botaoSalvar.disabled) {
            salvarPaciente();
        }
    }
});