# ==============================================================================
# 🤖 ROBÔ BPA: EXECUTOR RPA (MODO DATASUS NATIVO)
# ==============================================================================
# OBJETIVO:
# Ler o arquivo diário da recepção (pacientes.csv), extrair o SUS de forma blindada,
# validar se o SUS passa na regra matemática e CRUZAR com o arquivo oficial
# do Ministério da Saúde (ExpPaciente.txt). Só digita se existir lá e a data for sã.
# ==============================================================================

import pyautogui    # Biblioteca Mestra de RPA para automação de mouse e teclado.
import time         # Biblioteca para pausas estratégicas (delay) entre cliques.
import os           # Módulo para lidar com caminhos de arquivos.
import sys          # Módulo para mexer nas variáveis de ambiente do Python.
import re           # Módulo de Expressões Regulares (Regex) para achar padrões.
from datetime import datetime # Módulo para pegar o ano atual e gerar o log.

# ==============================================================================
# 1. CONFIGURAÇÃO E DEPENDÊNCIAS (BLINDAGEM DE ROTAS)
# ==============================================================================
# 🎯 CORREÇÃO: Descobre o caminho ABSOLUTO e exato de onde este script está salvo no HD.
pasta_atual = os.path.dirname(os.path.abspath(__file__))
# Descobre o caminho da pasta "pai" (um nível acima)
pasta_pai = os.path.abspath(os.path.join(pasta_atual, '..'))

# Injeta as duas pastas no "radar" de busca de módulos do Python
if pasta_atual not in sys.path: sys.path.append(pasta_atual)
if pasta_pai not in sys.path: sys.path.append(pasta_pai)

try:
    # Agora o Python consegue achar o utils.py independente de onde você rodar o comando
    from utils import valida_cns, apenas_numeros
except ImportError as e:
    # Se falhar, avisa exatamente onde ele tentou procurar para facilitar sua auditoria
    print(f"❌ ERRO CRÍTICO: Não achei o 'utils.py'.")
    print(f"🔍 O sistema procurou nestas pastas:\n 1. {pasta_atual}\n 2. {pasta_pai}")
    exit()

print("==================================================")
print("🤖 ROBÔ BPA: MODO DATASUS (ExpPaciente.txt)   🤖")
print("==================================================\n")

# --- COLETA DE DADOS INICIAIS (MENU DO ROBÔ) ---
data_atend = input("👉 1. Digite a DATA do atendimento (Ex: 15042026): ").strip()
print("\n👉 2. Escolha o PROCEDIMENTO:")
print("   [1] Médico     (0301060029)")
print("   [2] Enfermeiro (0301010048)")
opcao_proc = input("=> Digite a opção (1 ou 2): ").strip()

if opcao_proc == '1':
    procedimento = "0301060029"
elif opcao_proc == '2':
    procedimento = "0301010048"
else:
    print("❌ Opção inválida. O robô foi encerrado.")
    exit()

nome_profissional = input("\n👉 3. Digite o NOME do profissional (Ex: Dr. Carlos): ").strip().upper()
if not nome_profissional:
    nome_profissional = "NÃO INFORMADO"

# --- LOCALIZAÇÃO DOS ARQUIVOS ---
# 🎯 CORREÇÃO: Usamos a variável 'pasta_atual' para garantir que ele ache o CSV e o TXT
# arq_diario: A planilha que as meninas geram hoje com quem foi atendido
arq_diario = os.path.join(pasta_atual, "pacientes.csv")
# arq_datasus: O arquivo oficial exportado do BPA com a base de pacientes
arq_datasus = os.path.join(pasta_atual, "ExpPaciente.txt")

if not os.path.exists(arq_diario):
    print(f"\n❌ ERRO: O arquivo da recepção não foi encontrado em:\n{arq_diario}")
    exit()

if not os.path.exists(arq_datasus):
    print(f"\n❌ ERRO: A base do SUS não foi encontrada em:\n{arq_datasus}")
    exit()

# Listas de separação para o relatório de erros
pacientes_validados = []
rejeitados = []
ano_atual = datetime.now().year

print(f"\n⏳ Carregando a base oficial do DATASUS na memória...")

# ==============================================================================
# FASE 1: CARREGAR O ARQUIVO DO DATASUS NA MEMÓRIA (DICIONÁRIO)
# ==============================================================================
# Um dicionário em Python (dict) permite buscas instantâneas. Vamos mapear o SUS para a Data.
# Usamos 'latin-1' pois é a codificação padrão dos arquivos antigos do Governo/Datasus.
base_oficial = {}
with open(arq_datasus, 'r', encoding='latin-1', errors='ignore') as f_sus:
    for linha in f_sus:
        # A linha do DATASUS é fixa. Se for menor que 53, é lixo ou final de arquivo.
        if len(linha) >= 53:
            # SUS começa no índice 0 e vai até o 15.
            sus_ds = linha[0:15].strip()
            # A data começa após o nome. Posição 45 até a 53 (Formato AAAAMMDD).
            data_nasc_ds = linha[45:53].strip()
            
            # Só guarda no dicionário se o número tiver 15 caracteres exatos
            if len(sus_ds) == 15:
                base_oficial[sus_ds] = data_nasc_ds
                
print(f"✅ Base carregada! {len(base_oficial)} pacientes encontrados no ExpPaciente.txt.")
print(f"🔍 Cruzando arquivo diário com a base do DATASUS...\n")

# ==============================================================================
# FASE 2: LER A PLANILHA DO DIA E APLICAR AS TRAVAS DE SEGURANÇA (FILTRO TRIPLO)
# ==============================================================================
with open(arq_diario, 'r', encoding='utf-8', errors='ignore') as f_diario:
    linhas_hoje = f_diario.readlines()
    
    # Enumera as linhas para informar no log onde exatamente está o erro
    for num_linha, linha_texto in enumerate(linhas_hoje, start=1):
        
        # --- BLINDAGEM DO SUS ---
        # Tira espaços e traços que possam existir misturados no CSV.
        linha_limpa = linha_texto.replace(" ", "").replace("-", "")
        
        # A Expressão Regular \b\d{15}\b procura um bloco isolado de 15 números.
        # Isso impede que o Python junte um CPF (11) com um CEP (8) e ache que é um SUS.
        match_sus = re.search(r'\b\d{15}\b', linha_limpa)
        
        if match_sus:
            sus_limpo = match_sus.group(0)
        else:
            # Fallback antigo: limpa a linha toda e vê se sobram só 15 números
            limpo_bruto = apenas_numeros(linha_texto)
            if len(limpo_bruto) == 15:
                sus_limpo = limpo_bruto
            else:
                continue # Linha vazia ou ilegível, pula.

        # --- TRAVA 1: VALIDAÇÃO MATEMÁTICA OFICIAL (Módulo 11) ---
        if not valida_cns(sus_limpo):
            rejeitados.append(f"Linha {num_linha:03d} | SUS: {sus_limpo} -> CNS INVÁLIDO (Erro Matemático/Digitação)")
            continue
            
        # --- TRAVA 2: CRUZAMENTO COM O EXPPACIENTE.TXT ---
        if sus_limpo in base_oficial:
            # O SUS existe no Datasus! Vamos testar a sanidade da data de nascimento.
            data_nasc = base_oficial[sus_limpo]
            
            if len(data_nasc) == 8:
                try:
                    ano = int(data_nasc[0:4]) # Pega apenas os 4 primeiros dígitos (O Ano)
                    
                    # Trava 3: Segurança Humana (Bloqueia datas bizarras antes de digitar)
                    if ano < 1900 or ano > ano_atual:
                        rejeitados.append(f"Linha {num_linha:03d} | SUS: {sus_limpo} -> DATA EXTRAPOLADA NO BPA ({data_nasc})")
                        continue
                except ValueError:
                    rejeitados.append(f"Linha {num_linha:03d} | SUS: {sus_limpo} -> DATA CORROMPIDA NO BPA ({data_nasc})")
                    continue
                    
            # Se sobreviveu a todas as travas, está apto para o robô!
            pacientes_validados.append(sus_limpo)
        else:
            # O SUS passou no cálculo matemático, mas não está registrado na base do Ministério
            rejeitados.append(f"Linha {num_linha:03d} | SUS: {sus_limpo} -> NÃO ENCONTRADO NO ExpPaciente.txt")

# ==============================================================================
# FASE 3: RELATÓRIO DE AUDITORIA (LOG DE REJEITADOS)
# ==============================================================================
if rejeitados:
    # 🎯 CORREÇÃO: Garante que o log de erros salve na pasta exata do script
    arquivo_log = os.path.join(pasta_atual, "historico_rejeitados.txt")
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Modo 'a' = Append. Adiciona os erros novos sem apagar o histórico de dias anteriores.
    with open(arquivo_log, "a", encoding='utf-8') as f_log:
        f_log.write(f"\n[{data_hora}] ==================================================\n")
        f_log.write(f"PROFISSIONAL: {nome_profissional}\n")
        f_log.write(f"DATA ATEND. : {data_atend} | PROCEDIMENTO: {procedimento}\n")
        f_log.write("-" * 80 + "\n")
        for r in rejeitados:
            f_log.write(r + "\n")
            
    print(f"⚠️ {len(rejeitados)} problemas encontrados. Veja o log acumulado em 'historico_rejeitados.txt'.")
    
if not pacientes_validados:
    print("\n🛑 Nenhum paciente apto para digitação. O robô parou.")
    exit()

# ==============================================================================
# FASE 4: AUTOMAÇÃO RPA (O ROBÔ EM AÇÃO)
# ==============================================================================
# List Comprehension avançada: Quebra a lista gigante em lotes exatos de 99 
# pacientes para respeitar o limite máximo da "folha" dentro do sistema BPA.
lotes = [pacientes_validados[i:i + 99] for i in range(0, len(pacientes_validados), 99)]

print(f"✅ {len(pacientes_validados)} pacientes confirmados no DATASUS e prontos.")

for i, lote in enumerate(lotes):
    print(f"\n📦 LOTE {i + 1}/{len(lotes)}")
    input("=> Vá ao BPA, abra a folha e aperte ENTER...")
    
    time.sleep(5) # 5 segundos de tolerância para você clicar na tela do BPA e tirar a mão do mouse
    
    for p in lote:
        pyautogui.write(p)       # Simula o teclado digitando o Cartão SUS
        pyautogui.press('f7')    # Comando de atalho do BPA para executar a busca
        time.sleep(1.0)          # Delay obrigatório para o BPA pensar e não travar
        
        pyautogui.write(data_atend)
        pyautogui.press('tab')
        
        pyautogui.write(procedimento)
        pyautogui.press('1')     # Quantidade
        time.sleep(0.5)
        
        pyautogui.press(['tab', 'tab', 'tab']) # Pula campos irrelevantes
        pyautogui.write('2')     # Finalizador
        time.sleep(0.3)
        
        pyautogui.press(['tab', 'tab'])
        pyautogui.press('enter') # Confirma e salva a linha preenchida
        
        print(f"✅ Digitado: {p}")
        time.sleep(1.2)          # Respiro para o sistema salvar antes de reiniciar o loop

print("\n🎯 MISSÃO CUMPRIDA!")