# 🖼️ Módulo de Estrutura Web (Templates / HTML)

Este diretório contém o esqueleto da interface gráfica do Ecossistema H.M.P.C.F. Utilizando a arquitetura do **Flask**, esta pasta armazena as páginas que serão injetadas e renderizadas para o usuário final.

## ⚙️ Arquitetura e Engenharia do HTML

Diferente de um site comum, este arquivo atua como o **Front-End de um Sistema Hospitalar**. Ele foi desenhado para maximizar a ergonomia da recepcionista e interagir em tempo real com o banco de dados.

### 1. Gatilhos de Inteligência (Event-Driven)
O HTML possui "escutas" embutidas em seus campos que acionam o Cérebro do Sistema (`script.js`) no exato momento da digitação, sem precisar recarregar a tela:
* **`oninput`:** Usado para aplicar máscaras de formatação (como colocar o traço no CPF em tempo real) e forçar todas as letras para MAIÚSCULO automaticamente (`this.value.toUpperCase()`), garantindo um banco de dados padronizado.
* **`onblur`:** Quando a recepcionista termina de digitar a Data de Nascimento e pula para a próxima caixa, esse evento aciona instantaneamente o cálculo da idade pediátrica.

### 2. Controle de Impressão (`.no-print`)
Uso estratégico da classe CSS `no-print` nas áreas de botões e triagem. Isso avisa ao navegador que aqueles elementos são exclusivos da tela do computador e devem ser sumariamente apagados quando a impressora for acionada.

### 3. Formulário Flexível (Flexbox)
A estrutura não usa tabelas arcaicas para alinhar as caixas. Utiliza o conceito moderno de `divs` com proporções lógicas (`style="flex: 1.5;"`), garantindo que o nome tenha mais espaço que a idade, preenchendo 100% da linha horizontal perfeitamente.

## 🚀 Como Funciona a Integração
Este arquivo HTML (`index.html`) puxa a estética da pasta vizinha através da tag `<link rel="stylesheet" href="../static/style.css">` e ganha vida importando a inteligência na última linha de código com `<script src="../static/script.js"></script>`. 

---
*Desenvolvido por **Fábio Gomes da Silva** em parceria com a IA (NotebookLM / Gemini) para o Hospital Municipal Presidente Café Filho.*