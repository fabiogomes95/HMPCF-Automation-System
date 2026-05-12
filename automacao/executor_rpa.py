# ==============================================================================
# 🤖 ROBÔ BPA: EXECUTOR RPA (MODO CONTÍNUO E CONEXÃO DIRETA GDB)
# ==============================================================================
# OBJETIVO:
# Carregar o banco de dados apenas UMA vez para economizar tempo,
# e permitir rodar vários lotes/profissionais em sequência.
# ==============================================================================

import pyautogui    # Biblioteca Mestra de RPA para automação de mouse e teclado.
import time         # Biblioteca para pausas estratégicas (delay) entre cliques.
import os           # Módulo para lidar com caminhos de arquivos.
import sys          # Módulo para mexer nas variáveis de ambiente do Python.
import re           # Módulo de Expressões Regulares (Regex) para achar padrões.
from datetime import datetime # Módulo para pegar o ano atual e gerar o log.
import firebirdsql  # Biblioteca para ler direto do banco de dados GDB.

# ==============================================================================
# 1. CONFIGURAÇÃO E DEPENDÊNCIAS
# ==============================================================================
pasta_atual = os.path.dirname(os.path.abspath(__file__))
pasta_pai = os.path.abspath(os.path.join(pasta_atual, '..'))

if pasta_atual not in sys.path: sys.path.append(pasta_atual)
if pasta_pai not in sys.path: sys.path.append(pasta_pai)

try:
    from utils import valida_cns, apenas_numeros, valida_cpf
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: Não achei o 'utils.py'.")
    exit()

print("==================================================")
print("🤖 ROBÔ BPA: MODO CONTÍNUO (SUS & CPF)       🤖")
print("==================================================\n")

caminho_gdb = r'C:/BPA/BPAMAG.GDB'
arq_diario = os.path.join(pasta_atual, "pacientes.csv")

# ==============================================================================
# FASE 1: CARREGAR O BANCO DE DADOS NA MEMÓRIA (UMA ÚNICA VEZ)
# ==============================================================================
print(f"⏳ Conectando ao Banco de Dados do DATASUS (Isso só vai acontecer uma vez)...")
base_oficial = {}
try:
    con = firebirdsql.connect(
        host='localhost', database=caminho_gdb,
        user='SYSDBA', password='masterkey', charset='WIN1252'
    )
    cur = con.cursor()
    cur.execute("SELECT CNS, NUM_CPF, DTNASC FROM CADCNS")
    rows = cur.fetchall()
    
    for r in rows:
        sus_ds = str(r[0] or "").strip()
        cpf_ds = str(r[1] or "").strip()
        data_nasc_ds = str(r[2] or "").strip() 
        
        if len(sus_ds) == 15:
            base_oficial[sus_ds] = data_nasc_ds
        if len(cpf_ds) == 11:
            base_oficial[cpf_ds] = data_nasc_ds
            
    con.close()
    print(f"✅ Banco carregado! {len(base_oficial)} chaves de busca mapeadas na memória.")
    
except Exception as e:
    print(f"\n❌ ERRO CRÍTICO: Não foi possível acessar o banco do BPA (.GDB):\n{e}")
    exit()

# ==============================================================================
# INÍCIO DO LOOP DE REPETIÇÃO (RODA ATÉ VOCÊ MANDAR PARAR)
# ==============================================================================
while True:
    print("\n" + "="*50)
    print("📝 PREPARANDO NOVO LOTE DE DIGITAÇÃO")
    print("="*50)

    # --- COLETA DE DADOS INICIAIS ---
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
        print("❌ Opção inválida. Tente novamente.")
        continue # Volta para o início do Loop

    nome_profissional = input("\n👉 3. Digite o NOME do profissional (Ex: Dr. Carlos): ").strip().upper()
    if not nome_profissional:
        nome_profissional = "NÃO INFORMADO"

    if not os.path.exists(arq_diario):
        print(f"\n❌ ERRO: O arquivo 'pacientes.csv' não foi encontrado.")
        input("Pressione ENTER para tentar novamente...")
        continue

    pacientes_validados = []
    rejeitados = []
    ano_atual = datetime.now().year

    # ==========================================================================
    # FASE 2: LER A PLANILHA DO DIA E APLICAR FILTRO
    # ==========================================================================
    with open(arq_diario, 'r', encoding='utf-8', errors='ignore') as f_diario:
        linhas_hoje = f_diario.readlines()
        
        for num_linha, linha_texto in enumerate(linhas_hoje, start=1):
            linha_limpa = linha_texto.replace(" ", "").replace("-", "").replace(".", "")
            match_doc = re.search(r'\b\d{15}\b|\b\d{11}\b', linha_limpa)
            
            if match_doc:
                doc_limpo = match_doc.group(0)
            else:
                limpo_bruto = apenas_numeros(linha_texto)
                if len(limpo_bruto) in (11, 15):
                    doc_limpo = limpo_bruto
                else:
                    continue

            # --- TRAVA 1: VALIDAÇÃO MATEMÁTICA ---
            if len(doc_limpo) == 15:
                if not valida_cns(doc_limpo):
                    rejeitados.append(f"Linha {num_linha:03d} | SUS: {doc_limpo} -> CNS INVÁLIDO")
                    continue
            elif len(doc_limpo) == 11:
                if not valida_cpf(doc_limpo):
                    rejeitados.append(f"Linha {num_linha:03d} | CPF: {doc_limpo} -> CPF INVÁLIDO")
                    continue
                
            # --- TRAVA 2: CRUZAMENTO COM O BANCO ---
            if doc_limpo in base_oficial:
                data_nasc = base_oficial[doc_limpo]
                if len(data_nasc) == 8:
                    try:
                        ano = int(data_nasc[0:4]) 
                        if ano < 1900 or ano > ano_atual:
                            rejeitados.append(f"Linha {num_linha:03d} | DOC: {doc_limpo} -> DATA EXTRAPOLADA ({data_nasc})")
                            continue
                    except ValueError:
                        rejeitados.append(f"Linha {num_linha:03d} | DOC: {doc_limpo} -> DATA CORROMPIDA ({data_nasc})")
                        continue
                        
                pacientes_validados.append(doc_limpo)
            else:
                rejeitados.append(f"Linha {num_linha:03d} | DOC: {doc_limpo} -> NÃO ENCONTRADO NO BANCO DO BPA")

    # ==========================================================================
    # FASE 3: RELATÓRIO DE AUDITORIA
    # ==========================================================================
    if rejeitados:
        arquivo_log = os.path.join(pasta_atual, "historico_rejeitados.txt")
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        with open(arquivo_log, "a", encoding='utf-8') as f_log:
            f_log.write(f"\n[{data_hora}] ==================================================\n")
            f_log.write(f"PROFISSIONAL: {nome_profissional} | DATA: {data_atend}\n")
            f_log.write("-" * 80 + "\n")
            for r in rejeitados:
                f_log.write(r + "\n")
                
        print(f"\n⚠️ {len(rejeitados)} problemas encontrados. Verifique 'historico_rejeitados.txt'.")
        
    if not pacientes_validados:
        print("\n🛑 Nenhum paciente apto neste lote.")
    else:
        # ======================================================================
        # FASE 4: AUTOMAÇÃO RPA (O ROBÔ EM AÇÃO)
        # ======================================================================
        lotes = [pacientes_validados[i:i + 99] for i in range(0, len(pacientes_validados), 99)]

        print(f"\n✅ {len(pacientes_validados)} documentos (SUS/CPF) confirmados e prontos.")

        for i, lote in enumerate(lotes):
            print(f"\n📦 LOTE {i + 1}/{len(lotes)}")
            input("=> Vá ao BPA, abra a folha e aperte ENTER...")
            
            time.sleep(5)
            
            for p in lote:
                pyautogui.write(p)       
                pyautogui.press('f7')    
                time.sleep(1.0)          
                
                pyautogui.write(data_atend)
                pyautogui.press('tab')
                
                pyautogui.write(procedimento)
                pyautogui.press('1')     
                time.sleep(0.5)
                
                pyautogui.press(['tab', 'tab', 'tab']) 
                pyautogui.write('2')     
                time.sleep(0.3)
                
                pyautogui.press(['tab', 'tab'])
                pyautogui.press('enter') 
                
                print(f"✅ Digitado: {p}")
                time.sleep(1.2)          

        print("\n🎯 LOTE CONCLUÍDO COM SUCESSO!")

    # ==========================================================================
    # VERIFICAÇÃO DE CONTINUIDADE
    # ==========================================================================
    print("-" * 50)
    resposta = input("🔄 Deseja processar um NOVO LOTE/PROFISSIONAL? (S/N): ").strip().upper()
    if resposta != 'S':
        print("\n🚀 Encerrando o robô. Até a próxima!")
        break # Quebra o loop e fecha o programa