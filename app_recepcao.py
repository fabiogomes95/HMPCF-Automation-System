# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
# Arquivo Servidor (Backend) - Versão Refatorada para Eel (App Desktop)
# =========================================================================

import os
import sqlite3
import threading
import eel
from utils import apenas_numeros 
from planilha_nuvem import gari_da_nuvem

# Blindagem de diretório
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Define a pasta 'web' como o coração visual do sistema
eel.init('web_recepcao')

DB_NAME = 'hospital.db'

# =========================================================================
# ⚙️ INICIALIZAÇÃO DO BANCO DE DADOS 
# =========================================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Criação das tabelas com as chaves exatas
    cursor.execute('''CREATE TABLE IF NOT EXISTS pacientes (cpf TEXT PRIMARY KEY, sus TEXT, nome TEXT, nomeSocial TEXT, naturalidade TEXT, dn TEXT, idade TEXT, sexo TEXT, civil TEXT, raca TEXT, ocupacao TEXT, mae TEXT, responsavel TEXT, tel TEXT, endereco TEXT, numero TEXT, bairro TEXT, cidade TEXT, estado TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS atendimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, cpf TEXT, sus TEXT, data_atendimento TEXT, hora_atendimento TEXT, registro TEXT, procedencia TEXT, enviado_nuvem INTEGER DEFAULT 0)''')
    
    # Migração da coluna do Gari
    try:
        cursor.execute("ALTER TABLE atendimentos ADD COLUMN enviado_nuvem INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass 
        
    conn.commit()
    conn.close()

# =========================================================================
# 🌐 FUNÇÕES EXPOSTAS PARA O FRONT-END (A MÁGICA DO EEL)
# =========================================================================

@eel.expose
def buscar_paciente(id):
    """Procura paciente pelo CPF ou SUS direto no banco SQLite"""
    id_limpo = apenas_numeros(id)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM pacientes WHERE cpf=? OR sus=?", (id_limpo, id_limpo))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else {"erro": "nulo"}

@eel.expose
def salvar(dados):
    """Insere ou Atualiza a ficha cadastral e gera o atendimento"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. Atualiza ou insere o paciente 
        cursor.execute('''INSERT OR REPLACE INTO pacientes (cpf, sus, nome, nomeSocial, naturalidade, dn, idade, sexo, civil, raca, ocupacao, mae, responsavel, tel, endereco, numero, bairro, cidade, estado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
        (apenas_numeros(dados.get('cpf','')), apenas_numeros(dados.get('sus','')), dados.get('nome',''), dados.get('nomeSocial',''), dados.get('naturalidade',''), dados.get('dn',''), dados.get('idade',''), dados.get('sexo',''), dados.get('civil',''), dados.get('raca',''), dados.get('ocupacao',''), dados.get('mae',''), dados.get('responsavel',''), dados.get('tel',''), dados.get('endereco',''), dados.get('numero',''), dados.get('bairro',''), dados.get('cidade',''), dados.get('estado','')))
        
        # 2. Cria o registro do atendimento
        cursor.execute('''INSERT INTO atendimentos (cpf, sus, data_atendimento, hora_atendimento, registro, procedencia) VALUES (?, ?, ?, ?, ?, ?)''', 
        (apenas_numeros(dados.get('cpf')), apenas_numeros(dados.get('sus')), dados.get('data_atendimento'), dados.get('hora_atendimento'), dados.get('registro'), dados.get('procedencia')))
        
        conn.commit()
        return {"status": "sucesso", "registro_gerado": dados.get('registro')}
        
    except Exception as e: 
        return {"status": "erro", "mensagem": str(e)}
    finally: 
        conn.close()

# =========================================================================
# 🎬 LIGANDO OS MOTORES (INÍCIO DO PROGRAMA)
# =========================================================================
if __name__ == '__main__':
    init_db()
    
    # Lança o "Gari da Nuvem" (Backup para o Google Sheets) em segundo plano
    threading.Thread(target=gari_da_nuvem, daemon=True).start()
    
    print("🚀 App da Recepção HMPCF Iniciado...")
    # Abre a janela como um aplicativo real ('chrome' app mode) no centro da tela
    eel.start('index.html', mode='chrome', size=(1250, 850))