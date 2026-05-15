"""
FUSAO.PY — Fusão Inteligente de Pacientes Duplicados
======================================================
Esse script é a FAXINA V3 — mais inteligente que a faxina.py
porque ele lida com casos complexos de duplicação.

O PROBLEMA REAL:
- Às vezes o MESMO CPF/SUS está associado a MUITOS nomes diferentes
  (CPF "coringa" usado por várias pessoas — tipo 000.000.000-00)
- Nesse caso, NÃO podemos fundir, porque são pessoas diferentes!

SOLUÇÃO:
1. Agrupa pacientes por CPF ou SUS válido
2. Se um documento tem MAIS DE 3 nomes diferentes → CPF CORINGA → ignora
3. Se tem até 3 nomes → funde: o MAIOR nome vira o "master"
4. Move os atendimentos dos clones pro master
5. Deleta os clones

Uso: python scripts/fusao.py
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import apenas_numeros, valida_cpf, valida_cns


def faxina_definitiva():
    """
    Executa a fusão inteligente de pacientes duplicados.
    
    Regras:
    1. Agrupa por CPF válido (prioridade) ou SUS válido
    2. Se o documento aparece em >3 nomes diferentes → CPF CORINGA → ignora
    3. Dentro do grupo, o MAIOR nome (mais completo) vira o master
    4. Move todos os atendimentos dos clones pro master
    5. Deleta os clones
    
    Precisa de CONFIRMAÇÃO manual antes de começar
    (pra garantir que o backup foi feito).
    """
    logger.info("==================================================")
    logger.info("FAXINA V3 - MAXIMA SEGURANCA E PREVENCAO DE ERROS")
    logger.info("==================================================")

    caminho_db = os.path.join(
        os.path.dirname(__file__), '..', 'hospital.db'
    )

    confirmar = input(
        "ATENCAO: Voce RESTAUROU O BACKUP original de novo? (S/N): "
    ).strip().upper()
    if confirmar != 'S':
        logger.info("Operacao cancelada. Restaure o backup primeiro.")
        return

    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT rowid, nome, cpf, sus FROM pacientes")
        todos_pacientes = cursor.fetchall()

        grupos = {}
        pacientes_sem_doc = 0

        # --- PASSO 1: AGRUPAR POR DOCUMENTO VÁLIDO ---
        for paciente in todos_pacientes:
            rowid, nome, cpf_bruto, sus_bruto = paciente

            chave_unica = None

            # CPF tem prioridade sobre SUS
            if cpf_bruto and valida_cpf(cpf_bruto):
                chave_unica = apenas_numeros(cpf_bruto)
            elif sus_bruto and valida_cns(sus_bruto):
                chave_unica = apenas_numeros(sus_bruto)

            if chave_unica:
                if chave_unica not in grupos:
                    grupos[chave_unica] = []
                grupos[chave_unica].append(paciente)
            else:
                pacientes_sem_doc += 1

        total_grupos_fundidos = 0
        total_clones_apagados = 0
        total_atend_movidos = 0
        cpf_generico_ignorado = 0

        # --- PASSO 2: PROCESSAR CADA GRUPO ---
        for chave, lista_pacientes in grupos.items():
            if len(lista_pacientes) > 1:

                # --- TRAVA 1: CPF CORINGA ---
                # Se o mesmo documento tem MAIS DE 3 nomes diferentes,
                # é um CPF genérico (tipo 000.000.000-00).
                # NÃO podemos fundir — são pessoas diferentes!
                nomes_unicos = set([
                    str(p[1]).strip().upper()
                    for p in lista_pacientes if p[1]
                ])
                if len(nomes_unicos) > 3:
                    cpf_generico_ignorado += len(lista_pacientes)
                    continue

                total_grupos_fundidos += 1

                # --- TRAVA 2: ESCOLHER O MASTER ---
                # O paciente com o MAIOR nome (mais completo) vira o master
                lista_pacientes.sort(
                    key=lambda x: len(str(x[1]).strip()),
                    reverse=True
                )

                master = lista_pacientes[0]
                master_id = master[0]
                master_nome = master[1]

                # --- TRAVA 3: GARIMPAR O MELHOR CPF/SUS ---
                # Pego o melhor CPF e SUS de TODOS os clones
                melhor_cpf = master[2]
                melhor_sus = master[3]

                for p in lista_pacientes:
                    if not melhor_cpf and p[2] and valida_cpf(p[2]):
                        melhor_cpf = p[2]
                    if not melhor_sus and p[3] and valida_cns(p[3]):
                        melhor_sus = p[3]

                # Atualiza o master com os melhores documentos
                cursor.execute(
                    "UPDATE pacientes SET cpf = ?, sus = ?, nome = ? "
                    "WHERE rowid = ?",
                    (melhor_cpf, melhor_sus, master_nome, master_id)
                )

                # --- DELETAR OS CLONES ---
                clones = lista_pacientes[1:]
                for clone in clones:
                    clone_id, clone_nome, clone_cpf, clone_sus = clone

                    # Move os atendimentos do clone pro master
                    if clone_sus and str(clone_sus).strip() != '':
                        cursor.execute(
                            "UPDATE atendimentos SET sus = ? "
                            "WHERE sus = ?",
                            (melhor_sus, clone_sus)
                        )
                        total_atend_movidos += cursor.rowcount

                    if clone_cpf and str(clone_cpf).strip() != '':
                        cursor.execute(
                            "UPDATE atendimentos SET cpf = ? "
                            "WHERE cpf = ?",
                            (melhor_cpf, clone_cpf)
                        )
                        total_atend_movidos += cursor.rowcount

                    # Deleta o clone
                    cursor.execute(
                        "DELETE FROM pacientes WHERE rowid = ?",
                        (clone_id,)
                    )
                    total_clones_apagados += 1

                    logger.info(f"  -> Clone '{clone_nome}' absorvido pelo Master '{master_nome}'")

        conn.commit()

        logger.info("=" * 50)
        logger.info("FAXINA DEFINITIVA CONCLUIDA!")
        logger.info("=" * 50)
        logger.info(f"Pacientes corrigidos    : {total_grupos_fundidos}")
        logger.info(f"Clones apagados         : {total_clones_apagados}")
        logger.info(f"Atendimentos realocados : {total_atend_movidos}")
        logger.info(f"Ignorados (Sem Doc)     : {pacientes_sem_doc}")
        logger.info(f"Ignorados (CPF Coringa) : {cpf_generico_ignorado}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"ERRO: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    faxina_definitiva()
