"""
APP_RECEPCAO.PY — Servidor Web da Recepção (Eel | Porta 8000)
===============================================================

Fluxo:
1. Recepcionista abre index.html no navegador
2. Digita CPF, SUS ou NOME → frontend chama buscar_paciente() ou buscar_por_nome()
3. Preenche o formulário → clica F2 → frontend chama salvar()
4. salvar() insere no SQLite
5. Gari da Nuvem (outra thread) pega do SQLite e manda pro Google Sheets
"""

import os
import sqlite3
import threading
import eel
from logging_setup import logger
from utils import apenas_numeros
from planilha_nuvem import gari_da_nuvem

os.chdir(os.path.dirname(os.path.abspath(__file__)))

eel.init('web_recepcao')

DB_NAME = 'hospital.db'


def conectar_banco() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)


def init_db() -> None:
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

    try:
        cursor.execute(
            "ALTER TABLE atendimentos "
            "ADD COLUMN enviado_nuvem INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def converter_data_para_db(data_br: str) -> str:
    try:
        if "/" in data_br:
            partes = data_br.split('/')
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        return data_br
    except Exception:
        return data_br


def converter_data_para_web(data_db: str) -> str:
    try:
        if "-" in data_db:
            partes = data_db.split('-')
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        return data_db
    except Exception:
        return data_db


# =====================================================================
# FUNÇÕES EXPORTADAS PRO JAVASCRIPT
# =====================================================================

@eel.expose
def buscar_paciente(id_procurado: str) -> dict:
    """
    Busca paciente por CPF ou SUS.
    Retorna dict com dados, ou {"erro": "nulo"} se não achar.
    """
    try:
        id_limpo = apenas_numeros(str(id_procurado))

        conn = conectar_banco()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM pacientes WHERE cpf=? OR sus=?",
            (id_limpo, id_limpo)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            dados = {k: row[k] for k in row.keys()}
            dados['dn'] = converter_data_para_web(dados.get('dn', ''))
            return dados
        else:
            return {"erro": "nulo"}

    except Exception as e:
        logger.error(f"ERRO CRITICO NA BUSCA: {e}")
        return {"erro": "banco_travado"}


@eel.expose
def buscar_por_nome(termo: str) -> list[dict]:
    """
    Busca pacientes por nome (parcial, case insensitive).
    Retorna lista de pacientes encontrados.
    """
    try:
        conn = conectar_banco()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT nome, cpf, sus, dn FROM pacientes WHERE nome LIKE ? LIMIT 20",
            (f"%{termo.upper()}%",)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        resultados = []
        for row in rows:
            resultados.append({
                'nome': row['nome'],
                'cpf': row['cpf'] or '',
                'sus': row['sus'] or '',
                'dn': converter_data_para_web(row['dn'] or '')
            })
        return resultados

    except Exception as e:
        logger.error(f"ERRO NA BUSCA POR NOME: {e}")
        return []


@eel.expose
def buscar_historico(cpf_ou_sus: str) -> list[dict]:
    """
    Busca os últimos 3 atendimentos de um paciente.
    """
    try:
        id_limpo = apenas_numeros(str(cpf_ou_sus))
        if not id_limpo:
            return []

        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT data_atendimento, hora_atendimento, procedencia
               FROM atendimentos
               WHERE cpf=? OR sus=?
               ORDER BY data_atendimento DESC, hora_atendimento DESC
               LIMIT 5""",
            (id_limpo, id_limpo)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'data': converter_data_para_web(r[0]) if r[0] else '',
                'hora': r[1] or '',
                'procedencia': r[2] or ''
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"ERRO NO HISTORICO: {e}")
        return []


@eel.expose
def verificar_duplicata(nome: str, dn: str) -> list[dict]:
    """
    Verifica se já existe paciente com mesmo nome + data de nascimento.
    Retorna lista de possíveis duplicatas.
    """
    try:
        if not nome or not dn:
            return []

        nome_upper = nome.strip().upper()
        dn_iso = converter_data_para_db(dn)

        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nome, cpf, sus, dn FROM pacientes WHERE nome=? AND dn=?",
            (nome_upper, dn_iso)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {'nome': r[0], 'cpf': r[1] or '', 'sus': r[2] or ''}
            for r in rows
        ]

    except Exception as e:
        logger.error(f"ERRO NA VERIFICACAO DE DUPLICATA: {e}")
        return []


@eel.expose
def salvar(dados: dict) -> dict:
    """
    Salva paciente + atendimento no banco.
    Retorna {"status": "sucesso"} ou {"status": "erro"}.
    """
    conn = conectar_banco()
    cursor = conn.cursor()

    try:
        data_nascimento_db = converter_data_para_db(dados.get('dn', ''))

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
        logger.error(f"ERRO AO SALVAR: {e}")
        return {"status": "erro", "mensagem": str(e)}

    finally:
        conn.close()


# --- GARI DA NUVEM (THREAD PROTEGIDA) ---
_status_gari = "desconhecido"

def rodar_gari() -> None:
    global _status_gari
    try:
        _status_gari = "rodando"
        gari_da_nuvem()
    except Exception:
        _status_gari = "erro"


@eel.expose
def status_gari() -> str:
    """Retorna o status atual do Gari da Nuvem."""
    return _status_gari


# =====================================================================
# INICIAR (usado pelo main.py)
# =====================================================================
def iniciar() -> None:
    init_db()
    threading.Thread(target=rodar_gari, daemon=True).start()
    logger.info("App Recepcao HMPCF Iniciado...")
    eel.start('index.html', mode='msedge', size=(1250, 850), port=8000)

# =====================================================================
# PONTO DE ENTRADA (direto)
# =====================================================================
if __name__ == '__main__':
    iniciar()
