# 🖥️ Módulo de Interface Dinâmica e Estilização (Static)

Este diretório contém os motores visuais e lógicos do lado do cliente (Frontend) do Ecossistema H.M.P.C.F. Eles transformam a estrutura HTML bruta em uma folha A4 virtual e interativa.

## ⚙️ Arquivos e Lógicas de Negócio

### 1. `script.js` (O Cérebro do Frontend)
Muito mais que interatividade básica, este script atua como a **primeira linha de defesa** do banco de dados, poupando processamento do servidor:
* **Validação Matemática (Client-Side):** Calcula o Módulo 11 do CPF e Cartão SUS no momento da digitação. Se for inválido, a linha fica vermelha e o sistema bloqueia o salvamento.
* **Inteligência Pediátrica:** Calcula automaticamente a idade. Se for menor que 1 ano, converte para "Meses". Se for menor que 1 mês, converte para "Dias".
* **Requisições Assíncronas (Fetch API):** Ao digitar um documento válido, o JS faz uma requisição invisível ao backend e preenche a ficha do paciente em milissegundos caso ele já exista no hospital.
* **Trava Anti-Colisão (Efeito Metralhadora):** Ao pressionar a tecla de atalho `F2`, o botão é desativado no primeiro milissegundo, blindando o banco de dados contra cliques duplos acidentais.

### 2. `style.css` (O Motor de Impressão)
A interface foi projetada utilizando o conceito de "What You See Is What You Get" (O que você vê é o que você obtém).
* **Folha A4 Virtual:** Desenho estrutural exato de uma folha A4 no meio da tela (`210mm x 297mm`).
* **Design Pattern (Flexbox e Grid):** Organiza as caixas e bordas para não desmontarem independentemente do tamanho da tela.
* **Inteligência de Impressora (`@media print`):** Quando a recepcionista aperta para imprimir, o CSS remove sombras, fundos cinzas e botões interativos, enviando para a impressora apenas as bordas e os dados limpos, economizando tinta da instituição.
* **Linhas de Caligrafia (CSS Gradient):** Uso de `repeating-linear-gradient` para desenhar as linhas pautadas perfeitas para a escrita manual médica, sem precisar carregar imagens pesadas.

---
*Desenvolvido por **Fábio Gomes da Silva** em parceria com a IA (NotebookLM / Gemini) para o Hospital Municipal Presidente Café Filho.*
