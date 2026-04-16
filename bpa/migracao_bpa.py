# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - MÓDULO DE MIGRAÇÃO (ETL)
# Desenvolvido para migrar dados históricos do BPA preservando a integridade.
# =========================================================================
import pandas as pd
import sqlite3
import re
import os

# =========================================================================
# 1. O GPS ABSOLUTO (Garante que vai achar o banco de dados)
# =========================================================================
# Descobre a pasta exata onde este script (migracao_bpa.py) está rodando (Pasta BPA)
pasta_script = os.path.dirname(os.path.abspath(__file__))

# Volta uma pasta para trás para achar a raiz (Gestao-BPA-Digital) onde fica o banco
pasta_principal = os.path.dirname(pasta_script)

# Monta o endereço inquebrável do arquivo do banco de dados (hospital.db)
caminho_banco = os.path.join(pasta_principal, 'hospital.db')

# Força o Python a trabalhar na pasta BPA para conseguir ler a planilha CSV local
os.chdir(pasta_script)

# Função utilitária para limpar as pontuações do CPF/SUS [3]
def limpar_numeros(valor):
    if pd.isna(valor): # Se a célula estiver vazia no Excel (Not A Number)
        return ""
    # O re.sub pega o texto e apaga tudo (\D) que NÃO for número [3]
    return re.sub(r'\D', '', str(valor)) 

print(f"🔍 Conectando ao cofre do hospital em: {caminho_banco}")
print("⏳ Iniciando a leitura da planilha dados_bpa.csv...")

try:
    # ==================================================================
    # 2. LEITURA BLINDADA DA PLANILHA (O Fim do Aviso Amarelo)
    # Lemos o arquivo pedindo pro Pandas tratar todas as colunas como
    # texto (dtype=str) e ler o arquivo inteiro de uma vez (low_memory=False).
    # ==================================================================
    df = pd.read_csv('dados_bpa.csv', dtype=str, low_memory=False)
    
    # Abre a porta do cofre do banco de dados [3]
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()

    # ==================================================================
    # 3. TRAVA DE SEGURANÇA MÁXIMA (Prevenção de Banco Vazio)
    # Se, por acidente, o banco de dados tiver sido apagado, o robô 
    # constrói todas as gavetas e colunas sozinho antes de trabalhar! [3]
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            cpf TEXT PRIMARY KEY, sus TEXT, nome TEXT, nomeSocial TEXT, naturalidade TEXT,
            dn TEXT, idade TEXT, sexo TEXT, civil TEXT, raca TEXT, ocupacao TEXT,
            mae TEXT, responsavel TEXT, tel TEXT, endereco TEXT, numero TEXT,
            bairro TEXT, cidade TEXT, estado TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, cpf TEXT, sus TEXT,
            data_atendimento TEXT, hora_atendimento TEXT, registro TEXT, procedencia TEXT
        )
    ''')
    conn.commit() # Salva a criação das tabelas

    # Contadores para mostrar o resumo no final
    adicionados = 0
    ignorados = 0

    # ==================================================================
    # 4. COMEÇA A MIGRAÇÃO DOS DADOS (O Motor de Análise)
    # Varre a planilha linha por linha (iterrows)
    # ==================================================================
    for index, row in df.iterrows():
        
        # Pega os documentos e já passa pelo "espremedor" para tirar pontuações
        cpf_limpo = limpar_numeros(row.get('cpf', ''))
        sus_limpo = limpar_numeros(row.get('cns', ''))
        
        # Pega as informações básicas e garante que fiquem em MAIÚSCULO
        # O pd.notna() garante que o código não exploda se a célula vier vazia do Excel
        nome = str(row.get('nome', '')).strip().upper() if pd.notna(row.get('nome')) else ""
        sexo = str(row.get('sexo', '')).strip().upper() if pd.notna(row.get('sexo')) else ""
        raca = str(row.get('raca', '')).strip().upper() if pd.notna(row.get('raca')) else ""
        
        # --------------------------------------------------------------
        # FILTRO RESTRITO 1: A DATA DE NASCIMENTO
        # --------------------------------------------------------------
        # Pega a data crua do CSV
        dn_bruto = str(row.get('dn', '')).strip() if pd.notna(row.get('dn')) else ""
        dn_final = "" # Nasce vazia por segurança
        
        # O Regex exige que a data seja escrita EXATAMENTE como: 2 Números / 2 Números / 4 Números
        if re.match(r'^\d{2}/\d{2}/\d{4}$', dn_bruto):
            # Se for aprovada, quebra a data nos 3 pedaços
            dia, mes, ano = dn_bruto.split('/')
            # E monta ela virada ao contrário (AAAA-MM-DD) que é o formato que o seu site entende
            dn_final = f"{ano}-{mes}-{dia}"
        # ATENÇÃO: Se a data estiver bagunçada (ex: "20-05-80"), ela reprova no teste
        # e a variável dn_final continua sendo "", mandando VAZIO para o banco de dados!

        # --------------------------------------------------------------
        # FILTRO RESTRITO 2: O ENDEREÇO
        # --------------------------------------------------------------
        endereco_bruto = str(row.get('endereco', '')).strip().upper() if pd.notna(row.get('endereco')) else ""
        endereco_rua = ""
        numero = ""
        bairro = ""
        
        # Só tenta fatiar se existir alguma coisa escrita na célula
        if endereco_bruto != "" and endereco_bruto != "NAN":
            # Quebra a frase inteira toda vez que achar uma vírgula
            partes = endereco_bruto.split(',')
            
            # REGRA SUPER ESTRITA: Só faz a divisão se tiverem EXATAMENTE 3 partes!
            if len(partes) == 3:
                # O Python separa inteligentemente cada pedaço para sua respectiva variável provisória
                rua_temp, num_temp, bairro_temp = partes 
                
                # O comando .strip() limpa os espaços invisíveis antes de guardar na variável final
                endereco_rua = rua_temp.strip()
                numero = num_temp.strip()
                bairro = bairro_temp.strip()
            
            # ATENÇÃO: Se o endereço vier com 1, 2 ou mais de 3 vírgulas, ele reprova no teste.
            # Como reprovou, o Python pula isso e todas as 3 variáveis ficam completamente VAZIAS ("")!

        # Se depois de todo o processo, a linha do Excel não tiver CPF nem SUS, ele pula esse "paciente fantasma"
        if cpf_limpo == "" and sus_limpo == "":
            continue
            
        # --------------------------------------------------------------
        # 5. INSERÇÃO BLINDADA NO BANCO DE DADOS
        # O comando INSERT OR IGNORE é a chave: Ele tenta inserir. Mas se o CPF 
        # já existir lá dentro, o SQLite cruza os braços e protege a ficha que a recepcionista já fez!
        # --------------------------------------------------------------
        cursor.execute('''
            INSERT OR IGNORE INTO pacientes (
                cpf, sus, nome, dn, sexo, raca, endereco, numero, bairro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (cpf_limpo, sus_limpo, nome, dn_final, sexo, raca, endereco_rua, numero, bairro))
        
        # Verifica se alguma linha nova foi realmente adicionada
        if cursor.rowcount > 0:
            adicionados += 1
        else:
            ignorados += 1 # Conta quantas vezes a trava de segurança entrou em ação [2]

    # Salva o arquivo permanentemente (fecha a gaveta) [3]
    conn.commit()
    # Desliga o banco para não pesar a memória do computador [3]
    conn.close()

    print("✅ Migração Concluída com Sucesso!")
    print(f"📈 Novos pacientes adicionados: {adicionados}")
    print(f"🛡️ Pacientes ignorados (Preservando dados da Recepção): {ignorados}")

except FileNotFoundError:
    print("❌ ERRO: O arquivo 'dados_bpa.csv' não foi encontrado na pasta BPA.")
except Exception as e:
    print(f"❌ ERRO GRAVE DURANTE A MIGRAÇÃO: {e}")