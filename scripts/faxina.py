"""
FAXINA.PY — Faxina Geral do SQLite | Auditoria + Mesclagem + Reestruturação
=============================================================================
Esse script faz uma faxina COMPLETA no banco hospital.db:

1. AUDITORIA: Valida CPF e SUS de cada paciente
   - CPF falso → vira "" (string vazia)
   - SUS falso → vira ""
2. GUILHOTINA: Se não tem nem CPF nem SUS válido → DELETA
3. MESCLAGEM: Se dois pacientes tem o mesmo documento → funde os dados
4. REESTRUTURAÇÃO: Recria a tabela com PRIMARY KEY (cpf, sus)
5. LIMPEZA DOS ATENDIMENTOS: Valida CPF/SUS dos históricos

Uso: python scripts/faxina.py
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import apenas_numeros, valida_cns, valida_cpf

# Garante que vai achar o banco na raiz do projeto
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(DIRETORIO_ATUAL, '..'))
DB_NAME = 'hospital.db'


def fazer_faxina():
    """
    Executa a faxina completa no banco.
    
    Etapas:
    1. Carrega todos os pacientes
    2. Valida CPF e SUS de cada um
    3. Exclui fichas sem documento válido
    4. Mescla pacientes duplicados (mesmo documento)
    5. Recria a tabela com nova estrutura
    6. Audita também a tabela de atendimentos
    """
    logger.info("Iniciando a Grande Faxina e Auditoria no Banco de Dados...")
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # --- PASSO 1: CARREGAR TODOS OS PACIENTES ---
    cursor.execute("SELECT * FROM pacientes")
    pacientes_sujos = cursor.fetchall()

    pacientes_limpos = {}
    fichas_excluidas = 0

    for p in pacientes_sujos:
        dados = dict(p)
        cpf_bruto = apenas_numeros(dados.get('cpf', ''))
        sus_bruto = apenas_numeros(dados.get('sus', ''))

        # --- PASSO 2: AUDITORIA ---
        # Se o CPF não passar no algoritmo, vira vazio
        cpf_puro = cpf_bruto if valida_cpf(cpf_bruto) else ""
        # Se o SUS não passar no algoritmo, vira vazio
        sus_puro = sus_bruto if valida_cns(sus_bruto) else ""

        # --- PASSO 3: GUILHOTINA ---
        # Sem CPF E sem SUS válido? A ficha é deletada
        if not cpf_puro and not sus_puro:
            fichas_excluidas += 1
            continue

        # Atualiza os dados com os documentos validados
        dados['cpf'] = cpf_puro
        dados['sus'] = sus_puro

        # --- PASSO 4: MESCLAGEM ---
        # Uso o documento VÁLIDO como chave de agrupamento
        # CPF tem prioridade sobre SUS
        chave_unica = cpf_puro if cpf_puro else sus_puro

        if chave_unica in pacientes_limpos:
            # Se já existe, funde os dados: preenche campos vazios
            paciente_guardado = pacientes_limpos[chave_unica]
            for coluna, valor in dados.items():
                if not paciente_guardado.get(coluna) and valor:
                    paciente_guardado[coluna] = valor
        else:
            pacientes_limpos[chave_unica] = dados

    logger.info(f"Encontrados {len(pacientes_sujos)} registros totais.")
    logger.info(f"Foram APAGADAS {fichas_excluidas} fichas sem CPF ou SUS validos.")
    logger.info(f"Apos auditoria e mesclagem, restaram {len(pacientes_limpos)} pacientes UNICOS.")

    # --- PASSO 5: REESTRUTURAÇÃO ---
    logger.info("Recriando a tabela com nova arquitetura...")
    cursor.execute("DROP TABLE pacientes")

    # Nova tabela com PRIMARY KEY composta (cpf + sus)
    cursor.execute('''
        CREATE TABLE pacientes (
            cpf TEXT, sus TEXT, nome TEXT, nomeSocial TEXT,
            naturalidade TEXT, dn TEXT, idade TEXT, sexo TEXT,
            civil TEXT, raca TEXT, ocupacao TEXT, mae TEXT,
            responsavel TEXT, tel TEXT, endereco TEXT, numero TEXT,
            bairro TEXT, cidade TEXT, estado TEXT,
            PRIMARY KEY (cpf, sus)
        )
    ''')

    logger.info("Salvando pacientes sobreviventes...")
    for chave, dados in pacientes_limpos.items():
        colunas = ', '.join(dados.keys())
        placeholders = ', '.join(['?'] * len(dados))
        valores = tuple(dados.values())
        cursor.execute(
            f"INSERT INTO pacientes ({colunas}) "
            f"VALUES ({placeholders})",
            valores
        )

    # --- PASSO 6: AUDITAR OS ATENDIMENTOS ---
    logger.info("Auditando tabela de atendimentos...")
    cursor.execute("SELECT id, cpf, sus FROM atendimentos")
    for a in cursor.fetchall():
        id_atend = a['id']
        a_cpf = apenas_numeros(a['cpf'])
        a_sus = apenas_numeros(a['sus'])

        a_cpf_ok = a_cpf if valida_cpf(a_cpf) else ""
        a_sus_ok = a_sus if valida_cns(a_sus) else ""

        cursor.execute(
            "UPDATE atendimentos SET cpf=?, sus=? WHERE id=?",
            (a_cpf_ok, a_sus_ok, id_atend)
        )

    conn.commit()
    conn.close()
    logger.info("Faxina e Auditoria Concluidas!")


if __name__ == '__main__':
    fazer_faxina()
