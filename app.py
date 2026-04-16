# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
# Arquivo Servidor (Backend) - Versão Final Otimizada e Didática
# =========================================================================

import os
import sqlite3
import gspread
import threading
import time
from datetime import datetime
from google.oauth2.service_account import Credentials
from flask import Flask, render_template, request, jsonify

# --- IMPORTANTE: Buscando as ferramentas centralizadas no seu utils.py ---
# Isso evita repetição de código (Princípio DRY - Don't Repeat Yourself)
from utils import apenas_numeros, remove_accents

# Configura o Python para rodar sempre na pasta onde o script está salvo
os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
DB_NAME = 'hospital.db'

# =========================================================================
# ☁️ CONFIGURAÇÕES DO GOOGLE SHEETS
# =========================================================================
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
NOME_PLANILHA = "DADOS BPA" 

# =========================================================================
# ⚙️ FUNÇÃO 1: O PREPARADOR DO BANCO DE DADOS LOCAL
# =========================================================================
def init_db():
    """
    CONCEITO: PERSISTÊNCIA DE DADOS
    Cria as tabelas caso elas não existam no SQLite.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de Pacientes (Dados que não mudam com frequência)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            cpf TEXT PRIMARY KEY, sus TEXT, nome TEXT, nomeSocial TEXT, naturalidade TEXT,
            dn TEXT, idade TEXT, sexo TEXT, civil TEXT, raca TEXT, ocupacao TEXT,
            mae TEXT, responsavel TEXT, tel TEXT, endereco TEXT, numero TEXT,
            bairro TEXT, cidade TEXT, estado TEXT
        )
    ''')
    
    # Tabela de Atendimentos (O registro de cada visita ao hospital)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT, sus TEXT, data_atendimento TEXT, hora_atendimento TEXT,
            registro TEXT, procedencia TEXT, 
            enviado_nuvem INTEGER DEFAULT 0 
        )
    ''')
    
    # Verifica se a coluna de controle de sincronização existe (migração segura)
    try:
        cursor.execute("ALTER TABLE atendimentos ADD COLUMN enviado_nuvem INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass 
        
    conn.commit()
    conn.close()

# =========================================================================
# 🚀 FUNÇÃO 2: O MOTOR DO GOOGLE (ENVIO PARA A PLANILHA)
# =========================================================================
def enviar_para_planilha(dados):
    """
    CONCEITO: INTEGRAÇÃO DE APIs
    Trata os dados e envia para a aba correspondente ao mês atual no Google Sheets.
    """
    try:
        # 1. Autenticação com a API do Google
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPE)
        client = gspread.authorize(creds)
        spreadsheet = client.open(NOME_PLANILHA)

        # 2. Gestão de Abas Mensais
        agora = datetime.now()
        meses_pt = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO',
                    7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}
        nome_aba = f"{meses_pt[agora.month]} {agora.year}"

        try:
            sheet = spreadsheet.worksheet(nome_aba)
        except gspread.exceptions.WorksheetNotFound:
            # Cria a aba do mês caso ela não exista
            sheet = spreadsheet.add_worksheet(title=nome_aba, rows="1000", cols="15")
            cabecalho = ["REGISTRO", "NOME", "DATA", "IDADE", "SEXO", "RAÇA", "CIDADE", "HORA", "CPF", "SUS", "OBS", "ENDEREÇO", "TEL"]
            sheet.append_row(cabecalho)

        # 3. Tratamento de Dados (Usando o utils.py)
        
        # Limpeza e Padronização de Nomes e Endereços
        nome_limpo = remove_accents(dados.get('nome', ''))
        rua = remove_accents(dados.get('endereco', '')).strip()
        num = apenas_numeros(dados.get('numero', '')).strip() or "S/N"
        bairro = remove_accents(dados.get('bairro', '')).strip()
        
        # Montagem do endereço para o Google Sheets
        rua_num = f"{rua}, {num}" if rua and num else (rua or num)
        endereco_formatado = f"{rua_num} - {bairro}" if rua_num and bairro else (rua_num or bairro)

        # Máscara de CPF para leitura humana na planilha
        cpf_limpo = apenas_numeros(dados.get('cpf', ''))
        cpf_com_mask = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_limpo

        # SUS limpo
        sus_limpo = apenas_numeros(dados.get('sus', ''))

        # Formatação de Data de Nascimento para o padrão BR
        dn_raw = dados.get('dn', '')
        dn_br = datetime.strptime(dn_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if (dn_raw and '-' in dn_raw) else dn_raw

        # Observação baseada na Procedência
        procedencia = str(dados.get('procedencia', '')).upper()
        obs = "" if procedencia == "NORMAL" else procedencia

        # 4. Montagem da Linha Final
        linha = [
            dados.get('registro'),      # A
            nome_limpo,                 # B
            dn_br,                      # C
            dados.get('idade'),         # D
            dados.get('sexo'),          # E
            dados.get('raca'),          # F
            dados.get('cidade'),        # G
            dados.get('hora_atendimento'), # H
            cpf_com_mask,               # I
            sus_limpo,                  # J
            obs,                        # K
            endereco_formatado,         # L
            dados.get('tel')            # M
        ]
        
        sheet.append_row(linha)
        return True
    
    except Exception as e:
        print(f"❌ Erro na Sincronização Google: {e}")
        return False

# =========================================================================
# 🧹 FUNÇÃO 3: O GARI DA NUVEM (BACKGROUND WORKER)
# =========================================================================
def gari_da_nuvem():
    """
    CONCEITO: MULTITHREADING
    Roda em segundo plano procurando atendimentos que ainda não foram para a nuvem.
    """
    while True:
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Busca registros pendentes
            cursor.execute('''
                SELECT a.id as id_atend, a.registro, a.data_atendimento, a.hora_atendimento, 
                       a.procedencia, p.* FROM atendimentos a 
                JOIN pacientes p ON a.cpf = p.cpf 
                WHERE a.enviado_nuvem = 0 
                ORDER BY a.id ASC
            ''')
            pendentes = cursor.fetchall()
            
            for p in pendentes:
                dados_dict = dict(p)
                if enviar_para_planilha(dados_dict):
                    cursor.execute("UPDATE atendimentos SET enviado_nuvem = 1 WHERE id = ?", (dados_dict['id_atend'],))
                    conn.commit()
                    print(f"✅ Registro {dados_dict['registro']} enviado com sucesso!")
                else:
                    break # Se falhar (sem internet), para e tenta no próximo ciclo
                    
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro no processamento em segundo plano: {e}")
            
        time.sleep(2) # Verifica a cada 2 segundos

# =========================================================================
# 🌐 ROTAS DO FLASK (API)
# =========================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buscar/<identificador>', methods=['GET'])
def buscar_paciente(identificador):
    """
    Busca paciente por CPF ou SUS ignorando qualquer formatação.
    """
    # Usa a função do utils para garantir que a busca seja feita apenas com números
    id_busca = apenas_numeros(identificador)
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Busca simplificada e rápida
    cursor.execute("SELECT * FROM pacientes WHERE cpf=? OR sus=?", (id_busca, id_busca))
    row = cursor.fetchone()
    conn.close()
    
    return jsonify(dict(row)) if row else (jsonify({"erro": "nao encontrado"}), 404)

@app.route('/salvar', methods=['POST'])
def salvar():
    """
    Recebe os dados do front-end e salva no banco de dados local.
    """
    dados = request.json
    # Garante que CPF e SUS sejam salvos apenas como números no banco de dados
    cpf = apenas_numeros(dados.get('cpf', ''))
    sus = apenas_numeros(dados.get('sus', ''))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # 1. Salva/Atualiza o Cadastro do Paciente
        cursor.execute('''
            INSERT OR REPLACE INTO pacientes (
                cpf, sus, nome, nomeSocial, naturalidade, dn, idade, sexo, civil, 
                raca, ocupacao, mae, responsavel, tel, endereco, numero, bairro, cidade, estado
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            cpf, sus, dados.get('nome',''), dados.get('nomeSocial',''), 
            dados.get('naturalidade',''), dados.get('dn',''), dados.get('idade',''), 
            dados.get('sexo',''), dados.get('civil',''), dados.get('raca',''), 
            dados.get('ocupacao',''), dados.get('mae',''), dados.get('responsavel',''), 
            dados.get('tel',''), dados.get('endereco',''), dados.get('numero',''), 
            dados.get('bairro',''), dados.get('cidade',''), dados.get('estado','')
        ))

        # 2. Registra o Atendimento (Evita duplicidade no mesmo minuto)
        cursor.execute('''
            SELECT id FROM atendimentos 
            WHERE cpf = ? AND data_atendimento = ? AND hora_atendimento = ?
        ''', (cpf, dados.get('data_atendimento'), dados.get('hora_atendimento')))
        
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO atendimentos (cpf, sus, data_atendimento, hora_atendimento, registro, procedencia) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                cpf, sus, dados.get('data_atendimento'), 
                dados.get('hora_atendimento'), dados.get('registro'), dados.get('procedencia')
            ))
            conn.commit()
            return jsonify({"status": "sucesso", "registro_gerado": dados.get('registro')})
            
        return jsonify({"status": "sucesso"})
        
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        conn.close()

# =========================================================================
# 🎬 LIGANDO OS MOTORES
# =========================================================================
if __name__ == '__main__':
    init_db()
    
    # Inicia o "Gari da Nuvem" em uma thread separada (Segundo Plano)
    threading.Thread(target=gari_da_nuvem, daemon=True).start()
    
    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)