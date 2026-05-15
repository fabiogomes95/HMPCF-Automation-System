"""
VALIDAR_CNS.PY — Faxina Cirúrgica de SUS Inválido
=========================================================
Essa ferramenta varre o SQLite e aplica duas regras:

REGRA 1 (PENA DE MORTE): Se o SUS for INVÁLIDO (não passa no algoritmo)
   → Deleta o paciente E todas as fichas de atendimento dele

REGRA 2 (PENA LEVE): Se a data de nascimento for muito curta (< 4 chars)
   → Só apaga a data, mantém o paciente

Tudo é LOGADO num arquivo .txt de relatório.

Por que isso existe? Porque o sistema BPA do governo REJEITA
qualquer paciente com SUS inválido. Melhor deletar do que
ter o lote inteiro rejeitado.

Uso: python scripts/validar_cns.py
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, valida_cns

PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("Iniciando a FAXINA CIRURGICA (Focada APENAS em SUS Invalido)...")

try:
    conn = sqlite3.connect(os.path.join(PASTA_RAIZ, 'hospital.db'))
    cursor = conn.cursor()

    # Carrega todos os pacientes
    cursor.execute(
        "SELECT rowid, cpf, sus, dn, nome FROM pacientes"
    )
    todos_pacientes = cursor.fetchall()

    pacientes_apagados = 0
    fichas_apagadas = 0
    datas_limpas = 0

    # Abre o relatório de log
    with open(
        os.path.join(PASTA_RAIZ, 'relatorio_faxina.txt'),
        'w', encoding='utf-8'
    ) as f:
        f.write(
            "=== RELATORIO DE FAXINA DE BANCO DE DADOS"
            " - HOSPITAL CAFE FILHO ===\n"
        )
        f.write("-" * 80 + "\n\n")

        # --- AUDITORIA PACIENTE POR PACIENTE ---
        for paciente in todos_pacientes:
            rowid, cpf_cru, sus_cru, dn_cru, nome_paciente = paciente
            sus_limpo = apenas_numeros(sus_cru)

            # REGRA 1: SUS inválido → PENA DE MORTE
            erro_sus = False
            if sus_limpo:
                erro_sus = not valida_cns(sus_cru)

            # REGRA 2: Data muito curta → SÓ APAGA A DATA
            # Se a data tem menos de 4 caracteres, é lixo
            erro_data = False
            if dn_cru and len(str(dn_cru).strip()) > 0 \
                    and len(str(dn_cru).strip()) < 4:
                erro_data = True

            # Formatação pro log
            nome_fmt = nome_paciente if nome_paciente else "NOME EM BRANCO"
            cpf_fmt = cpf_cru if cpf_cru else "SEM CPF"
            sus_fmt = sus_cru if sus_cru else "SEM SUS"
            dn_fmt = dn_cru if dn_cru else "SEM DATA"

            if erro_sus:
                # DELETA TUDO: paciente + fichas de atendimento
                f.write(
                    f"EXCLUIDO  : {nome_fmt.ljust(40)} "
                    f"| SUS: {sus_fmt.ljust(15)} "
                    f"| MOTIVO: SUS Matematicamente Invalido\n"
                )

                cursor.execute(
                    "DELETE FROM atendimentos WHERE cpf = ?",
                    (cpf_cru,)
                )
                fichas_apagadas += cursor.rowcount

                cursor.execute(
                    "DELETE FROM pacientes WHERE rowid = ?",
                    (rowid,)
                )
                pacientes_apagados += 1

            elif erro_data:
                # SÓ APAGA A DATA, mantém o paciente
                f.write(
                    f"DATA LIMPA: {nome_fmt.ljust(40)} "
                    f"| DN ANTIGA: {dn_fmt.ljust(10)} "
                    f"| MOTIVO: Apenas Data Removida\n"
                )
                cursor.execute(
                    "UPDATE pacientes SET dn = '' WHERE rowid = ?",
                    (rowid,)
                )
                datas_limpas += 1

        # --- RESUMO ---
        f.write("\n" + "=" * 80 + "\n")
        f.write("RESUMO FINAL:\n")
        f.write(f"- {pacientes_apagados} pacientes EXCLUIDOS (SUS Invalido).\n")
        f.write(f"- {fichas_apagadas} fichas de atendimento EXCLUIDAS.\n")
        f.write(f"- {datas_limpas} Datas de Nascimento APAGADAS.\n")

    conn.commit()
    print("FAXINA CIRURGICA CONCLUIDA COM SUCESSO!")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
finally:
    conn.close()
