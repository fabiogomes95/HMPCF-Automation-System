/*
=========================================================================
SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
Arquivo de Lógica (JavaScript) - VERSÃO FINAL INTEGRADORA E DIDÁTICA
=========================================================================
*/

// =========================================================================
// 1. VARIÁVEIS GLOBAIS (A memória do sistema)
// =========================================================================
let intervaloRelogio; // Caixa vazia que vai guardar o "motor" do nosso timer (o loop de 1 minuto)
let relogioPausado = false; // O "Freio de mão". Inicia em false para o relógio rodar livre!

// =========================================================================
// 2. A ENGRENAGEM DO RELÓGIO E A TRAVA DE REGISTRO
// =========================================================================
function atualizarDataHora() {
    // 1ª Regra: Se a recepcionista começou a digitar, ejetamos a função e a hora congela na tela.
    if (relogioPausado) return;
    
    // O comando 'new Date()' é a forma do JavaScript acessar o sistema operacional e pegar o tempo de agora.
    const agora = new Date();
    
    // --- PREPARANDO A DATA ---
    // Formata a data (YYYY-MM-DD) garantindo o "0" à esquerda em dias/meses menores que 10.
    const dia = String(agora.getDate()).padStart(2, '0');
    const mes = String(agora.getMonth() + 1).padStart(2, '0');
    const ano = agora.getFullYear();
    document.getElementById('data_atendimento').value = `${ano}-${mes}-${dia}`;
    
    // --- PREPARANDO A HORA ---
    const horas = String(agora.getHours()).padStart(2, '0');
    const minutos = String(agora.getMinutes()).padStart(2, '0');
    document.getElementById('hora_atendimento').value = `${horas}:${minutos}`;
}

// FUNÇÃO: Inicia o loop (timer) que chama a atualização de hora a cada 60.000ms (1 minuto).
function iniciarRelogio() {
    relogioPausado = false; // Garante que comece despausado.
    atualizarDataHora(); // Roda 1 vez na hora pra não nascer em branco.
    intervaloRelogio = setInterval(atualizarDataHora, 60000); 
}

// FUNÇÃO: Puxa o freio de mão! Impede que a hora mude enquanto o usuário preenche dados retroativos.
function pausarRelogio() {
    relogioPausado = true; 
}

// GATILHO INICIAL DO SISTEMA
// Assim que a janela inteira (window) terminar de carregar, chama o motor do relógio.
window.onload = iniciarRelogio;


// =========================================================================
// 3. CÁLCULO INTELIGENTE DE IDADE (Lógica de Pediatria inclusa)
// =========================================================================
function calcularIdade() {
    // 1. A "Garra": Pega a data preenchida e cancela se estiver vazia.
    const d = document.getElementById('db_dn').value;
    if (!d) return; 
    
    // 2. Fotos do Tempo: Converte o texto da data num objeto matemático do JS.
    const nasc = new Date(d);
    const hoje = new Date();
    
    // 3. Calcula a idade base (anos).
    let idade = hoje.getFullYear() - nasc.getFullYear();
    
    // Regra do Aniversário: Se o mês ou dia ainda não chegou neste ano, tira 1 ano.
    if (hoje.getMonth() < nasc.getMonth() || (hoje.getMonth() === nasc.getMonth() && hoje.getDate() < nasc.getDate())) {
        idade--;
    }
    
    // Criamos uma variável vazia que vai guardar o texto final
    let resultadoFinal;
    
    if (idade > 0) {
        // CORREÇÃO DO PLURAL: Se for 1, escreve "Ano", senão escreve "Anos"
        if (idade === 1) {
            resultadoFinal = "1 Ano";
        } else {
            resultadoFinal = idade + " Anos"; 
        }
    } else {
        // SENÃO (Se idade for 0), entramos na lógica de bebês.
        // Multiplicamos a diferença de anos por 12 para cobrir casos da virada de ano.
        let meses = (hoje.getFullYear() - nasc.getFullYear()) * 12 + (hoje.getMonth() - nasc.getMonth());
        
        // Se o dia do "mêsversário" ainda não chegou neste mês, subtrai 1 mês.
        if (hoje.getDate() < nasc.getDate()) {
            meses--;
        }
        
        if (meses > 0) {
            // Se o bebê já tem pelo menos 1 mês
            resultadoFinal = meses === 1 ? "1 Mês" : meses + " Meses";
        } else {
            // SENÃO (Se meses também for 0), é um recém-nascido. Calculamos em dias.
            // O JS calcula a diferença de datas em milissegundos.
            const diferencaMilissegundos = hoje.getTime() - nasc.getTime();
            // O 'Math.floor' arredonda o número para baixo.
            const dias = Math.floor(diferencaMilissegundos / (1000 * 60 * 60 * 24));
            resultadoFinal = dias === 1 ? "1 Dia" : dias + " Dias";
        }
    }
    // 5. Injeta o prato pronto na caixa HTML de Idade.
    document.getElementById('db_idade').value = resultadoFinal;
}

// =========================================================================
// 4. MÁSCARA DINÂMICA DO CPF E SUS (Com Gatilho de Busca)
// =========================================================================
function executarCpf(c) {
    // 1. O Filtro Mágico: Pega o que foi digitado, acha tudo que NÃO é número e apaga.
    let v = c.value.replace(/\D/g, ""); 
    
    // 2. A Trava de Tamanho: Impede que o usuário digite mais que 11 números.
    if (v.length > 11) v = v.substring(0, 11); 
    
    // 3. A Máscara Progressiva: Injeta os pontos e traço progressivamente.
    v = v.replace(/(\d{3})(\d)/, "$1.$2")
         .replace(/(\d{3})(\d)/, "$1.$2")
         .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    
    // 4. Devolve o texto formatado para a tela.
    c.value = v;
    
    // 5. Gatilho de Banco de Dados: Se bateu 11 dígitos, pausa o relógio e aciona o radar!
    if (v.replace(/\D/g, "").length === 11) {
        pausarRelogio();
        buscarNoBanco(v); 
    }
}

function soNumerosSus(c) {
    // Remove letras e limita a 15 números para o Cartão SUS
    let v = c.value.replace(/\D/g, "").substring(0, 15);
    c.value = v;
    if (v.length === 15) {
        pausarRelogio();
        buscarNoBanco(v); 
    }
}

// =========================================================================
// 5. VALIDAÇÃO MATEMÁTICA DO CPF E SUS (Ao sair da caixa)
// =========================================================================
function validarCpfFinal(c) {
    // 1. LIMPEZA: Pega apenas os números.
    let cpf = c.value.replace(/\D/g, "");
    
    // 2. TOLERÂNCIA: Se vazio, limpa erros e aborta.
    if (cpf === "") {
        c.classList.remove("invalid-input");
        return true;
    }
    
    // 3. A LISTA NEGRA: Sequências que enganam a matemática.
    const invalidos = [
        "00000000000", "11111111111", "22222222222", "33333333333", "44444444444",
        "55555555555", "66666666666", "77777777777", "88888888888", "99999999999"
    ];
    
    // 4. PRIMEIRA BARREIRA: Se não tem 11 dígitos ou tá na lista negra, pinta de vermelho!
    if (cpf.length !== 11 || invalidos.includes(cpf)) {
        c.classList.add("invalid-input");
        return false;
    }
    
    // 5. SEGUNDA BARREIRA: Matemática da Receita Federal (Módulo 11)
    let soma = 0, resto;
    for (let i = 1; i <= 9; i++) {
        soma += parseInt(cpf.substring(i-1, i)) * (11 - i);
    }
    resto = (soma * 10) % 11;
    if ((resto === 10) || (resto === 11)) resto = 0;
    if (resto !== parseInt(cpf.substring(9, 10))) {
        c.classList.add("invalid-input"); return false;
    }
    soma = 0;
    for (let i = 1; i <= 10; i++) {
        soma += parseInt(cpf.substring(i-1, i)) * (12 - i);
    }
    resto = (soma * 10) % 11;
    if ((resto === 10) || (resto === 11)) resto = 0;
    if (resto !== parseInt(cpf.substring(10, 11))) {
        c.classList.add("invalid-input"); return false;
    }
    
    // 6. ABSOLVIÇÃO: Se passou, tira o vermelho e autoriza.
    c.classList.remove("invalid-input");
    return true;
}

function validarSusFinal(c) {
    let sus = c.value.replace(/\D/g, "");
    
    if (sus === "") {
        c.classList.remove("invalid-input");
        return true;
    }
    
    // Trava 1: Tamanho e número inicial (Só existe SUS começando com 1, 2, 7, 8 e 9)
    if (sus.length !== 15 || !['1', '2', '7', '8', '9'].includes(sus.charAt(0))) {
        c.classList.add("invalid-input");
        return false;
    }

    let valido = false;

    // MATEMÁTICA 1: Cartões Definitivos (Começam com 7, 8 ou 9)
    if (['7', '8', '9'].includes(sus.charAt(0))) {
        let soma = 0;
        for (let i = 0; i < 15; i++) {
            soma += parseInt(sus.charAt(i)) * (15 - i);
        }
        valido = (soma % 11 === 0);
    } 
    // MATEMÁTICA 2: Cartões Provisórios (Começam com 1 ou 2)
    else {
        let pis = sus.substring(0, 11);
        let soma = 0;
        for (let i = 0; i < 11; i++) {
            soma += parseInt(pis.charAt(i)) * (15 - i);
        }
        
        let resto = soma % 11;
        let dv = 11 - resto;
        if (dv === 11) dv = 0;

        let resultado;
        if (dv === 10) {
            soma += 2;
            resto = soma % 11;
            dv = 11 - resto;
            resultado = pis + "001" + dv;
        } else {
            resultado = pis + "000" + dv;
        }
        
        valido = (sus === resultado);
    }

    // O Veredito
    if (!valido) {
        c.classList.add("invalid-input");
        return false;
    }

    // Se passou, limpa o vermelho de erro e coloca os espaços bonitinhos
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
    const registro = document.getElementById('db_registro').value.trim(); // <-- Nova variável
    const sexoSelecionado = document.querySelector('input[name="sexo"]:checked');
    
    // <-- NOVA TRAVA DO REGISTRO -->
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
// 8. INTEGRAÇÃO COM O BANCO DE DADOS (A Busca Oculta)
// =========================================================================
// Funções utilitárias para formatar documentos que voltam do banco
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

// FUNÇÃO MESTRE DE BUSCA: Vai até o Python procurar o paciente.
function buscarNoBanco(id) {
    // O 'fetch' faz uma requisição assíncrona para a rota '/buscar/' do Python.
    fetch('/buscar/' + id)
    .then(resposta => resposta.json())
    .then(paciente => {
        // Se o Python devolver erro (não achou), a tela continua vazia.
        if (paciente.erro) return;
        
        // Se achou, injeta os dados em cada caixinha correspondente como mágica!
        document.getElementById('db_nome').value = paciente.nome || "";
        document.getElementById('db_nome_social').value = paciente.nomeSocial || "";
        document.getElementById('db_dn').value = paciente.dn || "";
        document.getElementById('db_idade').value = paciente.idade || "";
        calcularIdade(); // Recalcula a idade na hora
        document.getElementById('db_mae').value = paciente.mae || "";
        document.getElementById('db_responsavel').value = paciente.responsavel || "";
        document.getElementById('db_tel').value = paciente.tel || "";
        document.getElementById('db_endereco').value = paciente.endereco || "";
        document.getElementById('db_numero').value = paciente.numero || "";
        document.getElementById('db_bairro').value = paciente.bairro || "";
        document.getElementById('db_cidade').value = paciente.cidade || "EXTREMOZ";
        document.getElementById('db_naturalidade').value = paciente.naturalidade || "";
        document.getElementById('db_ocupacao').value = paciente.ocupacao || "";
        
        // NOTA VITAL: O 'db_registro' não é puxado aqui, para que cada ficha nova gere um número novo!
        
        if (paciente.cpf) document.getElementById('db_cpf').value = formatarCPFExibicao(paciente.cpf);
        if (paciente.sus) document.getElementById('db_sus').value = formatarSUSExibicao(paciente.sus);
        
        // Marca automaticamente os Radio Buttons (Bolinhas)
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
        
        // Remove alertas de erro vermelhos, pois os dados vieram validados do cofre.
        document.getElementById('db_cpf').classList.remove("invalid-input");
        document.getElementById('db_sus').classList.remove("invalid-input");
    })
    .catch(erro => console.log("Paciente não encontrado localmente.", erro));
}

// =========================================================================
// 9. SALVAR PACIENTE (Envio Real para o Banco e Mutação Visual)
// =========================================================================
function salvarPaciente() {
    // 1. A Catraca: Verifica as obrigatoriedades antes de mandar pro banco.
    if (!validarFormulario()) {
        return;
    }
    
    // 2. Mutação 1 (Em Processamento): Deixa o botão amarelo e travado!
    const botaoSalvar = document.querySelector('.btn-save');
    botaoSalvar.disabled = true;
    botaoSalvar.style.backgroundColor = "#ffc107";
    botaoSalvar.style.color = "#000";
    botaoSalvar.innerHTML = "⏳ Salvando no Banco...";
    
    const procElement = document.querySelector('input[name="procedencia"]:checked');
    const procedenciaValor = procElement ? procElement.value : "";
    
    // 3. Empacotamento: Monta um "pacote" idêntico ao que o Python espera receber.
    const pacoteDados = {
        data_atendimento: document.getElementById('data_atendimento').value,
        hora_atendimento: document.getElementById('hora_atendimento').value,
        cpf: document.getElementById('db_cpf').value.replace(/\D/g, ""), // Manda só números limpos
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

    // 4. O Motoboy do JS (O fetch leva os dados pro Python e aguarda a resposta)
    fetch('/salvar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pacoteDados)
    })
    .then(resposta => resposta.json()) // Transforma a resposta do banco em formato legível
    .then(data => {
  if(data.status === "sucesso") {
            
            // Mantém o número na tela caso a recepcionista precise conferir
            if(data.registro_gerado) {
                document.getElementById('db_registro').value = data.registro_gerado;
            }

            // Mutação 2 (Sucesso): Ficou azul e travado!
            botaoSalvar.style.backgroundColor = "#0056b3";
            botaoSalvar.style.color = "#fff";
            botaoSalvar.innerHTML = "✅ SALVO COM SUCESSO!";
            
            // Alerta limpo e direto confirmando o número manual
            alert(`✅ Salvo com sucesso! Ficha número [ ${data.registro_gerado} ] registrada no sistema. Já pode Imprimir!`);
        } else {
            alert("❌ Erro ao salvar no banco de dados: " + data.mensagem);
            botaoSalvar.disabled = false; // Destrava se der erro pra tentar de novo.
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
// 11. LIMPEZA INTELIGENTE (Preparar a tela para o próximo paciente)
// =========================================================================
function limparTudo() {
    // 1. Esvazia todas as caixas de texto escritas.
    const camposParaLimpar = [
        'db_nome', 'db_nome_social', 'db_dn', 'db_idade', 'db_naturalidade',
        'db_cpf', 'db_sus', 'db_registro', 'db_ocupacao', 'db_mae',
        'db_responsavel', 'db_tel', 'db_endereco', 'db_numero', 'db_bairro'
    ];
    camposParaLimpar.forEach(id => {
        const caixa = document.getElementById(id);
        if (caixa) {
            caixa.value = '';
        }
    });
    
    // 2. Preserva os padrões da cidade base.
    if (document.getElementById('db_cidade')) document.getElementById('db_cidade').value = "EXTREMOZ";
    if (document.getElementById('db_estado')) document.getElementById('db_estado').value = "RN";
    
    // 3. Desmarca todas as bolinhas, menos a Procedência.
    const todasBolinhas = document.querySelectorAll('input[type="radio"]:not([name="procedencia"])');
    todasBolinhas.forEach(bolinha => bolinha.checked = false);
    
    // 4. Força a Procedência voltar pro NORMAL.
    const radioNormal = document.getElementById('radioNormal');
    if (radioNormal) radioNormal.checked = true;
    
    // 5. RESET DO BOTÃO DE SALVAR: Devolve ele para o verde de fábrica.
    const botaoSalvar = document.querySelector('.btn-save');
    if(botaoSalvar) {
        botaoSalvar.disabled = false;
        botaoSalvar.style.backgroundColor = ""; 
        botaoSalvar.style.color = "";
        botaoSalvar.innerHTML = "💾 Salvar (F2)";
    }
    
    // 6. Atualiza a data e hora para o presente e liga o relógio novamente.
    atualizarDataHora();
    if (intervaloRelogio) clearInterval(intervaloRelogio);
    iniciarRelogio();
    
    // 7. Joga o cursor do mouse de volta para o CPF, pronto pra digitar!
    document.getElementById('db_cpf').focus();
}

// =========================================================================
// 12. ATALHOS DO TECLADO (F2 para Salvar)
// =========================================================================
document.addEventListener('keydown', function(event) {
    if (event.key === 'F2') {
        event.preventDefault(); // Bloqueia qualquer função padrão do navegador
        
        const botaoSalvar = document.querySelector('.btn-save');
        // A TRAVA DE SEGURANÇA: Só deixa salvar se o botão não estiver desativado!
        // Isso impede a "Metralhadora" caso a recepcionista segure a tecla F2.
        if (botaoSalvar && !botaoSalvar.disabled) {
            salvarPaciente(); 
        }
    }
});
