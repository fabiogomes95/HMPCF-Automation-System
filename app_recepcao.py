"""
APP_RECEPCAO.PY — Servidor Web da Recepção (Eel | Porta 8000)
===============================================================
Esse é o coração da RECEPÇÃO do hospital.

O que faz:
- Sobe um servidor web Eel na porta 8000
- Serve a interface web_recepcao/ (HTML+CSS+JS)
- Expõe funções Python pro frontend chamar:
    * buscar_paciente() — procura por CPF/SUS no SQLite
    * salvar() — salva o atendimento no banco
- Inicia o Gari da Nuvem (thread em background)

O fluxo:
1. Recepcionista abre index.html no navegador
2. Digita CPF ou SUS → frontend chama buscar_paciente()
3. Preenche o formulário → clica F2 → frontend chama salvar()
4. salvar() insere no SQLite
5. Gari da Nuvem (outra thread) pega do SQLite e manda pro Google Sheets
"""

import os
import sqlite3
import threading
import eel
from utils import apenas_numeros
from planilha_nuvem import gari_da_nuvem

# Mudo pro diretório do script pra garantir que o hospital.db seja achado
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Inicializo o Eel apontando pra pasta web_recepcao/
# É lá que estão os arquivos HTML, CSS e JS
eel.init('web_recepcao')

DB_NAME = 'hospital.db'


def conectar_banco():
    """
    Abre conexão com o SQLite.
    timeout=30 segundos pra evitar "Database Locked" quando
    o Gari da Nuvem também estiver acessando ao mesmo tempo.
    check_same_thread=False permite que o Eel (que roda em outra thread)
    use a mesma conexão.
    """
    return sqlite3.connect(
        DB_NAME, timeout=30.0, check_same_thread=False
    )


def init_db():
    """
    Cria as tabelas se elas não existirem.
    Roda só uma vez, na inicialização do servidor.
    
    Tabela pacientes: um registro por CPF (PK)
    Tabela atendimentos: múltiplos atendimentos por paciente
    - enviado_nuvem: 0=pendente, 1=enviado, 2=processando
    """
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            cpf TEXT PRIMARY KEY,
            sus TEXT, nome TEXT, nomeSocial TEXT,
            naturalidade TEXT, dn TEXT, idade TEXT,
            sexo TEXT, civil TEXT, raca TEXT,
            ocupacao TEXT, mae TEXT, responsavel TEXT,
            tel TEXT, endereco TEXT, numero TEXT,
            bairro TEXT, cidade TEXT, estado TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT, sus TEXT,
            data_atendimento TEXT, hora_atendimento TEXT,
            registro TEXT, procedencia TEXT,
            enviado_nuvem INTEGER DEFAULT 0
        )
    ''')

    # Tento adicionar a coluna enviado_nuvem (pode já existir)
    try:
        cursor.execute(
            "ALTER TABLE atendimentos "
            "ADD COLUMN enviado_nuvem INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Se já existe, ignoro o erro

    conn.commit()
    conn.close()


def converter_data_para_db(data_br):
    """
    Converte DD/MM/AAAA → AAAA-MM-DD (formato ISO pro SQLite).
    O frontend manda data no formato brasileiro (dd/mm/aaaa)
    mas no banco eu guardo como ISO pra ordenar corretamente.
    """
    try:
        if "/" in data_br:
            partes = data_br.split('/')
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        return data_br
    except Exception:
        return data_br


def converter_data_para_web(data_db):
    """
    Converte AAAA-MM-DD → DD/MM/AAAA (formato brasileiro pro frontend).
    Quando devolvo os dados pro navegador, converto de volta.
    """
    try:
        if "-" in data_db:
            partes = data_db.split('-')
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        return data_db
    except Exception:
        return data_db


# =====================================================================
# FUNÇÕES EXPORTADAS PRO JAVASCRIPT (via @eel.expose)
# O frontend chama essas funções como se fossem JS
# =====================================================================

@eel.expose
def buscar_paciente(id_procurado):
    """
    Busca paciente por CPF ou SUS.
    O frontend chama quando a recepcionista digita o CPF/SUS e aperta TAB.
    
    Retorna dict com os dados do paciente, ou {"erro": "nulo"} se não achar.
    """
    try:
        # Limpo a string: tiro pontos, traços, espaços
        id_limpo = apenas_numeros(str(id_procurado))

        conn = conectar_banco()
        conn.row_factory = sqlite3.Row  # Linhas como dicionários
        cursor = conn.cursor()

        # Busco nas duas colunas (cpf e sus) com o mesmo valor
        cursor.execute(
            "SELECT * FROM pacientes WHERE cpf=? OR sus=?",
            (id_limpo, id_limpo)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            # Converte pra dict e formata a data pro padrão BR
            dados = {k: row[k] for k in row.keys()}
            dados['dn'] = converter_data_para_web(dados.get('dn', ''))
            return dados
        else:
            return {"erro": "nulo"}

    except Exception as e:
        print(f"ERRO CRITICO NA BUSCA: {e}")
        return {"erro": "banco_travado"}


@eel.expose
def salvar(dados):
    """
    Salva o paciente e o atendimento no banco.
    
    O frontend chama quando a recepcionista aperta F2.
    Recebe um dict com TODOS os campos do formulário.
    
    Fluxo:
    1. Converte a data de nascimento pra ISO
    2. INSERT OR REPLACE na tabela pacientes (se já existe, atualiza)
    3. INSERT na tabela atendimentos (novo atendimento)
    4. COMMIT
    
    Retorna {"status": "sucesso"} ou {"status": "erro"}.
    """
    conn = conectar_banco()
    cursor = conn.cursor()

    try:
        # Data de nascimento no formato do banco
        data_nascimento_db = converter_data_para_db(dados.get('dn', ''))

        # --- INSERT OU UPDATE DO PACIENTE ---
        # INSERT OR REPLACE: se o CPF já existe, substitui tudo
        cursor.execute('''
            INSERT OR REPLACE INTO pacientes
            (cpf, sus, nome, nomeSocial, naturalidade,
             dn, idade, sexo, civil, raca, ocupacao,
             mae, responsavel, tel, endereco, numero,
             bairro, cidade, estado)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            apenas_numeros(dados.get('cpf', '')),
            apenas_numeros(dados.get('sus', '')),
            dados.get('nome', ''),
            dados.get('nomeSocial', ''),
            dados.get('naturalidade', ''),
            data_nascimento_db,
            dados.get('idade', ''),
            dados.get('sexo', ''),
            dados.get('civil', ''),
            dados.get('raca', ''),
            dados.get('ocupacao', ''),
            dados.get('mae', ''),
            dados.get('responsavel', ''),
            dados.get('tel', ''),
            dados.get('endereco', ''),
            dados.get('numero', ''),
            dados.get('bairro', ''),
            dados.get('cidade', ''),
            dados.get('estado', '')
        ))

        # --- INSERT DO ATENDIMENTO ---
        # Cada vez que a recepcionista salva, é um novo atendimento
        cursor.execute('''
            INSERT INTO atendimentos
            (cpf, sus, data_atendimento, hora_atendimento,
             registro, procedencia)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            apenas_numeros(dados.get('cpf')),
            apenas_numeros(dados.get('sus')),
            dados.get('data_atendimento'),
            dados.get('hora_atendimento'),
            dados.get('registro'),
            dados.get('procedencia')
        ))

        conn.commit()
        return {"status": "sucesso", "registro_gerado": dados.get('registro')}

    except Exception as e:
        print(f"ERRO AO SALVAR: {e}")
        return {"status": "erro", "mensagem": str(e)}

    finally:
        conn.close()


# --- GARI DA NUVEM (THREAD PROTEGIDA) ---
def rodar_gari():
    """
    Roda o Gari da Nuvem em uma thread separada.
    Se ele quebrar por algum motivo, o servidor continua de pé.
    """
    try:
        gari_da_nuvem()
    except Exception:
        pass


# =====================================================================
# PONTO DE ENTRADA
# =====================================================================
if __name__ == '__main__':
    init_db()  # Cria as tabelas se não existirem

    # Inicio o Gari da Nuvem em background (daemon=True)
    threading.Thread(target=rodar_gari, daemon=True).start()

    print("App Recepcao HMPCF Iniciado...")
    # Abre no Microsoft Edge (modo app, sem barras)
    # Tamanho 1250x850, porta 8000
    eel.start('index.html', mode='msedge', size=(1250, 850), port=8000)
