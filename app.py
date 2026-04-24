# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
# Arquivo Servidor (Backend) - Versão Refatorada e Enxuta
# =========================================================================

import os
import sqlite3
import threading
from flask import Flask, render_template, request, jsonify
from utils import apenas_numeros # Importa do seu utils.py original

# ➜ IMPORTA O GARI: Puxa o seu robô lá do novo arquivo
from planilha_nuvem import gari_da_nuvem

# Blindagem de diretório
os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
DB_NAME = 'hospital.db'

# =========================================================================
# ⚙️ INICIALIZAÇÃO DO BANCO DE DADOS (Mantido exatamente igual)
# =========================================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Criação das tabelas com as chaves exatas que você definiu
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
# 🌐 ROTAS FLASK (A COMUNICAÇÃO ENTRE O SITE E O SERVIDOR)
# =========================================================================

@app.route('/')
def index(): 
    return render_template('index.html')

# --- ROTA DE BUSCA (A Lupa Exata do seu código original) ---
@app.route('/buscar/<id>', methods=['GET'])
def buscar_paciente(id):
    id_limpo = apenas_numeros(id)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Procura paciente pelo CPF ou SUS
    cursor.execute("SELECT * FROM pacientes WHERE cpf=? OR sus=?", (id_limpo, id_limpo))
    row = cursor.fetchone()
    conn.close()
    
    return jsonify(dict(row)) if row else (jsonify({"erro": "nulo"}), 404)

# --- ROTA DE SALVAMENTO (Seu UPSERT com as colunas completas) ---
@app.route('/salvar', methods=['POST'])
def salvar():
    dados = request.json
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. Atualiza ou insere o paciente (Mantém ficha cadastral sempre nova)
        cursor.execute('''INSERT OR REPLACE INTO pacientes (cpf, sus, nome, nomeSocial, naturalidade, dn, idade, sexo, civil, raca, ocupacao, mae, responsavel, tel, endereco, numero, bairro, cidade, estado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
        (apenas_numeros(dados.get('cpf','')), apenas_numeros(dados.get('sus','')), dados.get('nome',''), dados.get('nomeSocial',''), dados.get('naturalidade',''), dados.get('dn',''), dados.get('idade',''), dados.get('sexo',''), dados.get('civil',''), dados.get('raca',''), dados.get('ocupacao',''), dados.get('mae',''), dados.get('responsavel',''), dados.get('tel',''), dados.get('endereco',''), dados.get('numero',''), dados.get('bairro',''), dados.get('cidade',''), dados.get('estado','')))
        
        # 2. Cria o registro do atendimento (O 'enviado_nuvem' entra como 0 pelo DEFAULT)
        cursor.execute('''INSERT INTO atendimentos (cpf, sus, data_atendimento, hora_atendimento, registro, procedencia) VALUES (?, ?, ?, ?, ?, ?)''', 
        (apenas_numeros(dados.get('cpf')), apenas_numeros(dados.get('sus')), dados.get('data_atendimento'), dados.get('hora_atendimento'), dados.get('registro'), dados.get('procedencia')))
        
        conn.commit()
        # Avisa o frontend e devolve o ID do registro
        return jsonify({"status": "sucesso", "registro_gerado": dados.get('registro')})
        
    except Exception as e: 
        return jsonify({"status": "erro", "msg": str(e)}), 500
    finally: 
        conn.close()

# =========================================================================
# 🎬 LIGANDO OS MOTORES (INÍCIO DO PROGRAMA)
# =========================================================================
if __name__ == '__main__':
    # 1. Garante a criação e integridade das tabelas
    init_db()
    
    # 2. Lança o "Gari da Nuvem" (importado do novo arquivo)
    threading.Thread(target=gari_da_nuvem, daemon=True).start()
    
    # 3. Inicia o Flask
    # As travas de produção (debug=False, use_reloader=False) já estavam perfeitamente configuradas por você.
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)