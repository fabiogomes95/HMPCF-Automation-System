# ==============================================================================
# IMPORTADOR EM LOTE COM ATUALIZAÇÃO CIRÚRGICA
# ==============================================================================
# OBJETIVO: 
# Este script varre uma pasta em busca de planilhas CSV geradas pela recepção.
# Ele lê cada paciente e cruza o Cartão do SUS com o banco de dados (hospital.db).
# - Se o paciente NÃO existe: Cadastra do zero (nome, dn, sexo, cpf, sus).
# - Se o paciente JÁ existe: Verifica campo a campo. Se o banco estiver vazio
#   mas o CSV tiver a informação, ele atualiza apenas aquele campo.
# - Ao final, gera um relatório de auditoria (.txt) com os novos cadastros.
# ==============================================================================

import sqlite3  # Biblioteca nativa do Python para gerenciar e executar comandos em bancos de dados SQL.
import csv      # Módulo para manipulação de arquivos separados por vírgula (formato exportado pelo Excel).
import os       # Módulo para interagir com o Sistema Operacional (ex: ler caminhos de pastas e arquivos).
import sys      # Permite alterar parâmetros do sistema do Python (usado aqui para achar o utils.py).
import glob     # 🌟 Motor de Lote: Biblioteca que permite buscar múltiplos arquivos de uma vez usando padrões (ex: *.csv).
from datetime import datetime # Módulo de tempo, usado para registrar a data e hora exata no relatório de auditoria.

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E IMPORTAÇÃO DE MÓDULOS EXTERNOS
# ==============================================================================
# O comando sys.path.append adiciona a pasta "pai" (um nível acima) ao escopo do Python.
# Isso é fundamental em Análise de Sistemas para modularização: permite que este script 
# encontre e use as funções que estão dentro do seu arquivo 'utils.py'.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Importação das regras de negócio do seu utils.py
    # 'apenas_numeros' limpa sujeiras como pontos e traços.
    # 'valida_cns' é a trava matemática oficial do DATASUS.
    from utils import apenas_numeros, valida_cns
except ImportError:
    # Tratamento de Exceção: Se o arquivo utils.py for deletado ou movido, o programa não "crasha" 
    # de forma feia, ele avisa o usuário elegantemente e encerra a execução (exit).
    print("❌ ERRO CRÍTICO: As funções 'apenas_numeros' e 'valida_cns' não foram encontradas no utils.py.")
    exit()

# ==============================================================================
# 2. FUNÇÕES AUXILIARES (PROGRAMAÇÃO DEFENSIVA)
# ==============================================================================
def pega_coluna_segura(linha, indice):
    """
    Função de Prevenção de Erros (Tratamento de Exceções Silencioso).
    O Excel frequentemente 'corta' o final de uma linha CSV se as últimas colunas estiverem vazias.
    Se tentarmos acessar linha[12] e a linha só for até o 9, o Python dá erro 'IndexError' e quebra.
    Essa função verifica: "A linha é maior que o índice que quero pegar?". Se sim, pega. Se não, devolve vazio.
    O método .strip() limpa espaços acidentais no começo ou fim do texto.
    """
    if len(linha) > indice:
        return linha[indice].strip() 
    return ""

# ==============================================================================
# 3. FUNÇÃO PRINCIPAL DE IMPORTAÇÃO (CORE DO SISTEMA)
# ==============================================================================
def executar_importacao_lote():
    print("=========================================================")
    print("📥 IMPORTADOR EM LOTE RECEPÇÃO -> HOSPITAL.DB")
    print("🧠 MODO INTELIGENTE + RELATÓRIO TXT DE AUDITORIA")
    print("=========================================================\n")

    # --- DEFINIÇÃO DO CAMINHO DO BANCO DE DADOS ---
    # os.path.dirname(__file__) pega o diretório exato onde este arquivo .py está rodando agora.
    # Ele tenta achar o hospital.db na mesma pasta. Se não achar, procura uma pasta para trás ('..').
    caminho_db = os.path.join(os.path.dirname(__file__), 'hospital.db')
    if not os.path.exists(caminho_db):
        caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')

    # --- BUSCA AUTOMÁTICA DE ARQUIVOS (O MOTOR DE LOTE) ---
    # glob.glob("*.csv") cria uma lista com TODOS os arquivos da pasta que terminam com a extensão .csv.
    arquivos_csv = glob.glob("*.csv")
    
    # List Comprehension (Filtro): Cria uma nova lista ignorando o arquivo "pacientes.csv" 
    # porque esse é o arquivo do seu robô diário do BPA, não da recepção.
    arquivos_csv = [arq for arq in arquivos_csv if arq.lower() != "pacientes.csv"]

    # Se a lista estiver vazia após o filtro, avisa e encerra.
    if not arquivos_csv:
        print("❌ Nenhum arquivo CSV da recepção encontrado na pasta.")
        return

    print(f"📁 Encontrados {len(arquivos_csv)} arquivos CSV para processar!")

    # Pede a configuração do arquivo apenas uma vez para aplicar em todos os lotes.
    separador = input("👉 Os arquivos usam vírgula (,) ou ponto e vírgula (;)? ").strip()
    if separador not in [',', ';']:
        separador = ';'

    # --- INICIALIZAÇÃO DE VARIÁVEIS DE CONTROLE E ESTATÍSTICA ---
    # Essas variáveis guardam o histórico do que aconteceu para montar o painel final.
    inseridos_novos = 0
    atualizados_parciais = 0
    intactos_perfeitos = 0
    ignorados_erro = 0
    
    # Lista em memória que vai guardar os dados brutos de quem foi cadastrado para gerar o .txt no final.
    detalhes_novos = [] 

    try:
        # --- ABERTURA DA CONEXÃO COM O BANCO DE DADOS ---
        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor() # O cursor é o objeto responsável por executar as queries (SQL) no banco.
        
        print("\n⏳ Iniciando varredura das planilhas...\n")

        # --- LOOP 1: PERCORRE CADA ARQUIVO CSV ENCONTRADO NA PASTA ---
        for arquivo in arquivos_csv:
            print(f"🔄 Lendo planilha: {arquivo}...")
            
            # Abre o arquivo em modo leitura ('r'). 'encoding=utf-8' previne erros de acentuação.
            # 'errors=ignore' garante que se houver um caractere estranho no Excel, o script não trava.
            with open(arquivo, mode='r', encoding='utf-8', errors='ignore') as f:
                leitor = csv.reader(f, delimiter=separador)
                next(leitor, None) # Pula a linha 1 (cabeçalho) para não salvar a palavra "NOME" como paciente.
                
                # --- LOOP 2: PERCORRE CADA LINHA DENTRO DO CSV ATUAL ---
                for linha in leitor:
                    
                    # --- TRAVA DE SEGURANÇA 1: LINHAS VAZIAS OU CORROMPIDAS ---
                    # Se a linha tiver menos de 10 colunas, ela não tem a coluna SUS (índice 9). Pula a linha.
                    if len(linha) < 10:
                        continue 
                    
                    # --- EXTRAÇÃO E LIMPEZA DE DADOS ---
                    # Mapeamento oficial: 0=REG, 1=NOME, 2=DN, 3=IDADE, 4=SEXO, 5=RACA, 6=CIDADE, 7=HORA, 8=CPF, 9=SUS
                    nome_csv = pega_coluna_segura(linha, 1).upper()
                    dn_csv   = pega_coluna_segura(linha, 2)
                    sexo_csv = pega_coluna_segura(linha, 4).upper()
                    
                    # Passa os documentos pela função que arranca pontos e traços.
                    cpf_csv  = apenas_numeros(pega_coluna_segura(linha, 8))
                    sus_csv  = apenas_numeros(pega_coluna_segura(linha, 9))

                    # --- TRAVA DE SEGURANÇA 2: VALIDAÇÃO DO SUS ---
                    # O SUS é obrigatório. Se não tiver ou falhar na matemática, conta como erro e pula.
                    if not sus_csv or not valida_cns(sus_csv):
                        ignorados_erro += 1
                        continue 

                    # ======================================================================
                    # LÓGICA DE NEGÓCIO: CONSULTA DE EXISTÊNCIA (O PACIENTE JÁ ESTÁ NO BANCO?)
                    # ======================================================================
                    # O sinal de '?' protege contra ataques de SQL Injection.
                    cursor.execute("SELECT cpf, nome, dn, sexo FROM pacientes WHERE sus = ?", (sus_csv,))
                    paciente_banco = cursor.fetchone() # Traz a primeira correspondência encontrada.

                    if paciente_banco:
                        # --------------------------------------------------------------
                        # PACIENTE JÁ EXISTE: LÓGICA DE ATUALIZAÇÃO CIRÚRGICA (SMART UPDATE)
                        # --------------------------------------------------------------
                        # Extraímos os dados que o banco já tem para comparar com o CSV
                        db_cpf, db_nome, db_dn, db_sexo = paciente_banco
                        
                        # Essas listas vão guardar APENAS os campos que precisam ser alterados
                        campos_para_atualizar = []
                        valores_para_atualizar = []

                        # --- ANÁLISE CAMPO A CAMPO ---
                        # A regra é: Se o dado no banco está vazio (not db_cpf) E o CSV tem o dado (cpf_csv), atualize.
                        
                        # Verifica o CPF
                        if (not db_cpf or db_cpf.strip() == "") and cpf_csv:
                            campos_para_atualizar.append("cpf = ?")
                            valores_para_atualizar.append(cpf_csv)

                        # Verifica o Nome
                        if (not db_nome or db_nome.strip() == "") and nome_csv:
                            campos_para_atualizar.append("nome = ?")
                            valores_para_atualizar.append(nome_csv)

                        # Verifica a Data de Nascimento (dn)
                        if (not db_dn or db_dn.strip() == "") and dn_csv:
                            campos_para_atualizar.append("dn = ?")
                            valores_para_atualizar.append(dn_csv)

                        # Verifica o Sexo (Garante que só aceita M, F ou I)
                        if (not db_sexo or db_sexo.strip() == "") and sexo_csv in ['M', 'F', 'I']:
                            campos_para_atualizar.append("sexo = ?")
                            valores_para_atualizar.append(sexo_csv)

                        # --- EXECUÇÃO DO UPDATE (SE NECESSÁRIO) ---
                        # Se algum campo foi adicionado na lista, montamos o SQL.
                        if campos_para_atualizar:
                            # O comando .join cria a string dinamicamente. Ex: "UPDATE pacientes SET cpf = ?, nome = ?"
                            sql_update = f"UPDATE pacientes SET {', '.join(campos_para_atualizar)} WHERE sus = ?"
                            
                            # O SUS precisa ir para o final da lista de valores para suprir o '?' do WHERE
                            valores_para_atualizar.append(sus_csv) 
                            
                            try:
                                cursor.execute(sql_update, valores_para_atualizar)
                                atualizados_parciais += 1
                            except sqlite3.IntegrityError:
                                # Trata o erro caso tente injetar um CPF que já é usado por outro paciente (Chave Única)
                                ignorados_erro += 1
                        else:
                            # Se as listas continuaram vazias, o banco já tinha tudo. Não fazemos nada.
                            intactos_perfeitos += 1

                    else:
                        # --------------------------------------------------------------
                        # PACIENTE NÃO EXISTE: LÓGICA DE INSERÇÃO (NOVO CADASTRO)
                        # --------------------------------------------------------------
                        try:
                            # Insere estritamente as 5 colunas estipuladas. As outras da sua tabela ficarão NULL.
                            cursor.execute('''
                                INSERT INTO pacientes (sus, cpf, nome, dn, sexo)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (sus_csv, cpf_csv, nome_csv, dn_csv, sexo_csv))
                            
                            inseridos_novos += 1
                            
                            # 🌟 SALVANDO PARA AUDITORIA: Adiciona o nome e SUS na lista do relatório de texto
                            detalhes_novos.append(f"NOME: {nome_csv} | SUS: {sus_csv}")
                            
                        except sqlite3.IntegrityError:
                            # O SUS não existia, mas o CPF lido do CSV pode já estar cadastrado em outra pessoa.
                            ignorados_erro += 1

        # Terminamos de ler todos os arquivos. O commit efetiva (salva fisicamente) todas as mudanças no banco.
        conn.commit()
        # Fecha a conexão para liberar a memória e evitar bloqueio do arquivo hospital.db.
        conn.close()

        # ==============================================================================
        # 4. GERAÇÃO DO ARQUIVO DE RELATÓRIO (.TXT) - AUDITORIA FINAL
        # ==============================================================================
        if detalhes_novos:
            nome_relatorio = "relatorio_importacao.txt"
            # Modo 'w' (write): cria um arquivo novo ou sobrescreve se já existir.
            with open(nome_relatorio, "w", encoding="utf-8") as f_txt:
                f_txt.write(f"RELATÓRIO DE NOVOS PACIENTES CADASTRADOS\n")
                f_txt.write(f"DATA DO PROCESSAMENTO: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                f_txt.write("-" * 60 + "\n")
                
                # Descarrega a memória escrevendo paciente por paciente no bloco de notas
                for registro in detalhes_novos:
                    f_txt.write(registro + "\n")
                    
            print(f"\n📄 Auditoria salva! Relatório detalhado gerado em: '{nome_relatorio}'")

        # ==============================================================================
        # 5. EXIBIÇÃO DO PAINEL DE RESULTADOS NO TERMINAL
        # ==============================================================================
        print("\n=========================================================")
        print("✅ PROCESSAMENTO EM LOTE CONCLUÍDO COM SUCESSO!")
        print("=========================================================")
        print(f"📁 Arquivos lidos: {len(arquivos_csv)}")
        print(f"➕ Novos pacientes (Do zero): {inseridos_novos}")
        print(f"💉 Atualizados (Preencheu apenas o que faltava): {atualizados_parciais}")
        print(f"🛡️ Cadastros intactos (Já estavam 100% completos): {intactos_perfeitos}")
        print(f"🚫 Ignorados (Linhas vazias, SUS Inválido ou Conflito de CPF): {ignorados_erro}")
        print("=========================================================")

    except Exception as e:
        # Tratamento global de erros para o script não fechar repentinamente caso o banco esteja corrompido, etc.
        print(f"\n❌ Ocorreu um erro durante a importação: {e}")

# Essa estrutura garante que a função principal só seja executada se você rodar este arquivo diretamente.
# É um padrão ouro em Python.
if __name__ == "__main__":
    executar_importacao_lote()