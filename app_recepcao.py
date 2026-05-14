# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
# Arquivo Servidor (Backend) - VERSÃO BLINDADA (Daniel & Stephen Fix)
# =========================================================================

import os
import sqlite3
import threading
import eel
from utils import apenas_numeros 
from planilha_nuvem import gari_da_nuvem

# Garante que o sistema opere na pasta correta para achar o hospital.db
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Inicializa a interface Eel
eel.init('web_recepcao')

DB_NAME = 'hospital.db'

# =========================================================================
# 🛡️ CONEXÃO ULTRA-RESISTENTE
# =========================================================================
def conectar_banco():
    """Conecta ao SQLite permitindo espera de 30s para não dar 'Database Locked'"""
    return sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)

def init_db():
    """Cria e organiza as tabelas se elas não existirem"""
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS pacientes (cpf TEXT PRIMARY KEY, sus TEXT, nome TEXT, nomeSocial TEXT, naturalidade TEXT, dn TEXT, idade TEXT, sexo TEXT, civil TEXT, raca TEXT, ocupacao TEXT, mae TEXT, responsavel TEXT, tel TEXT, endereco TEXT, numero TEXT, bairro TEXT, cidade TEXT, estado TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS atendimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, cpf TEXT, sus TEXT, data_atendimento TEXT, hora_atendimento TEXT, registro TEXT, procedencia TEXT, enviado_nuvem INTEGER DEFAULT 0)''')
    try:
        cursor.execute("ALTER TABLE atendimentos ADD COLUMN enviado_nuvem INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass 
    conn.commit()
    conn.close()

# =========================================================================
# 🔄 FUNÇÃO DE CONVERSÃO DE DATA (INTERNA)
# =========================================================================
def converter_data_para_db(data_br):
    """Converte DD/MM/AAAA para AAAA-MM-DD para o banco ficar organizado"""
    try:
        if "/" in data_br:
            partes = data_br.split('/')
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        return data_br
    except:
        return data_br

def converter_data_para_web(data_db):
    """Converte AAAA-MM-DD para DD/MM/AAAA para a tela das meninas"""
    try:
        if "-" in data_db:
            partes = data_db.split('-')
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        return data_db
    except:
        return data_db

# =========================================================================
# 🌐 FUNÇÕES EXPOSTAS (EEL)
# =========================================================================

@eel.expose
def buscar_paciente(id_procurado):
    """Busca instantânea por CPF ou SUS tratando zeros à esquerda"""
    try:
        # Limpa pontos e traços, mas MANTÉM os zeros à esquerda (Daniel 009...)
        id_limpo = apenas_numeros(str(id_procurado))
        
        conn = conectar_banco()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # A busca tenta encontrar o número puro em ambas as colunas
        cursor.execute("SELECT * FROM pacientes WHERE cpf=? OR sus=?", (id_limpo, id_limpo))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            dados = {k: row[k] for k in row.keys()}
            # Converte a data do banco para o formato de máscara (DD/MM/AAAA)
            dados['dn'] = converter_data_para_web(dados.get('dn', ''))
            return dados 
        else:
            return {"erro": "nulo"}
            
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NA BUSCA: {e}")
        return {"erro": "banco_travado"}

@eel.expose
def salvar(dados):
    """Salva os dados convertendo a data para o padrão SQLite"""
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        # Preparamos a data para o banco (AAAA-MM-DD)
        data_nascimento_db = converter_data_para_db(dados.get('dn', ''))
        
        cursor.execute('''INSERT OR REPLACE INTO pacientes (cpf, sus, nome, nomeSocial, naturalidade, dn, idade, sexo, civil, raca, ocupacao, mae, responsavel, tel, endereco, numero, bairro, cidade, estado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
        (apenas_numeros(dados.get('cpf','')), apenas_numeros(dados.get('sus','')), dados.get('nome',''), dados.get('nomeSocial',''), dados.get('naturalidade',''), data_nascimento_db, dados.get('idade',''), dados.get('sexo',''), dados.get('civil',''), dados.get('raca',''), dados.get('ocupacao',''), dados.get('mae',''), dados.get('responsavel',''), dados.get('tel',''), dados.get('endereco',''), dados.get('numero',''), dados.get('bairro',''), dados.get('cidade',''), dados.get('estado','')))
        
        cursor.execute('''INSERT INTO atendimentos (cpf, sus, data_atendimento, hora_atendimento, registro, procedencia) VALUES (?, ?, ?, ?, ?, ?)''', 
        (apenas_numeros(dados.get('cpf')), apenas_numeros(dados.get('sus')), dados.get('data_atendimento'), dados.get('hora_atendimento'), dados.get('registro'), dados.get('procedencia')))
        
        conn.commit()
        return {"status": "sucesso", "registro_gerado": dados.get('registro')}
    except Exception as e: 
        print(f"❌ ERRO AO SALVAR: {e}")
        return {"status": "erro", "mensagem": str(e)}
    finally: 
        conn.close()

# --- GARI PROTEGIDO ---
def rodar_gari():
    try:
        gari_da_nuvem()
    except:
        pass

if __name__ == '__main__':
    init_db()
    threading.Thread(target=rodar_gari, daemon=True).start()
    print("🚀 App Recepção HMPCF Iniciado...")
    eel.start('index.html', mode='msedge', size=(1250, 850), port=8000)