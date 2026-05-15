"""
SINC_NOME.PY — Sincronizador Alternativo SQLite → Firebird (por NOME + DATA)
============================================================================
Esse script faz a mesma coisa que o integracao/sincronizar_firebird.py da
pasta integracao/, mas é uma versão MAIS ANTIGA e independente.

Diferenças:
- Pede mês/ano manualmente (não aceita parâmetros)
- Busca por NOME + DATA DE NASCIMENTO no Firebird
- Se achar → UPDATE, se não → INSERT
- Gera log de produção

Por que existe? Porque antes de refatorar o módulo de integração,
esse era o sincronizador principal. Agora é mantido como backup.

Uso: python scripts/sinc_nome.py
"""

import sqlite3
import firebirdsql
from datetime import datetime
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros
from config import DB_SQLITE, FIREBIRD_PATH, FIREBIRD_USER, FIREBIRD_PASSWORD

DB_FIREBIRD = FIREBIRD_PATH


def sincronizar():
    """
    Sincroniza pacientes do SQLite pro Firebird.
    Pede mês e ano pro usuário.
    """
    print("\n" + "=" * 45)
    print("   HMPCF - SINCRONIZADOR BPA (PRODUCAO)")
    print("=" * 45)

    mes = input("Digite o MES (ex: 05): ").strip().zfill(2)
    ano = input("Digite o ANO (ex: 2026): ").strip()

    sucessos = 0
    falhas = 0
    lista_novos = []
    lista_erros = []

    try:
        # --- CONEXÃO SQLITE ---
        con_sqlite = sqlite3.connect(DB_SQLITE)
        con_sqlite.row_factory = sqlite3.Row
        cur_sqlite = con_sqlite.cursor()

        # Busca pacientes que tiveram atendimento no mês/ano
        query_sqlite = """
            SELECT DISTINCT pacientes.* FROM pacientes
            INNER JOIN atendimentos ON pacientes.cpf = atendimentos.cpf
            WHERE atendimentos.data_atendimento LIKE ?
               OR atendimentos.data_atendimento LIKE ?
        """

        cur_sqlite.execute(query_sqlite, (
            f'%-%{mes}-%',
            f'%/%{mes}/%'
        ))
        pacientes = cur_sqlite.fetchall()

        if not pacientes:
            print(f"\nNenhum atendimento encontrado para {mes}/{ano}.")
            return

        # --- CONEXÃO FIREBIRD ---
        con_fb = firebirdsql.connect(
            host='localhost',
            database=DB_FIREBIRD,
            user=FIREBIRD_USER,
            password=FIREBIRD_PASSWORD,
            charset='WIN1252'
        )
        cur_fb = con_fb.cursor()

        for p in pacientes:
            try:
                # --- PREPARA OS DADOS ---
                nome_bpa = str(p['nome']).upper().strip()[:30]
                cpf_limpo = apenas_numeros(p['cpf'])[:11]
                sus_limpo = apenas_numeros(p['sus'])[:15]

                # Data de nascimento no formato YYYYMMDD
                dt_nasc_orig = str(p['dn']).strip()
                try:
                    if '/' in dt_nasc_orig:
                        dt_nasc = datetime.strptime(
                            dt_nasc_orig, '%d/%m/%Y'
                        ).strftime('%Y%m%d')
                    else:
                        dt_nasc = datetime.strptime(
                            dt_nasc_orig, '%Y-%m-%d'
                        ).strftime('%Y%m%d')
                except Exception:
                    dt_nasc = '19900101'

                # --- BUSCA POR NOME + DATA ---
                cur_fb.execute(
                    "SELECT NOME FROM CADCNS "
                    "WHERE NOME = ? AND DTNASC = ?",
                    (nome_bpa, dt_nasc)
                )
                reg = cur_fb.fetchone()

                # Endereço e contato
                end = str(p['endereco'] or '').upper().strip()[:25]
                num = str(p['numero'] or '').strip()[:5]
                bairro = str(p['bairro'] or '').upper().strip()[:15]
                tel_full = apenas_numeros(p['tel'])
                ddd = tel_full[:2] if len(tel_full) >= 10 else ''
                tel = tel_full[-8:] if len(tel_full) >= 8 else tel_full
                sexo = str(p['sexo'] or 'M').upper()[:1]
                co_lograd = "081"

                if reg:
                    # --- UPDATE ---
                    nome_alvo = reg[0]
                    sql_up = """
                        UPDATE CADCNS SET
                            NUM_CPF = ?, LOGPCN = ?, NUMPCN = ?,
                            BAIRRO_PCNTE = ?, DDTEL_PCNTE = ?,
                            TEL_PCNTE = ?, CNS = ?, CO_LOGRAD = ?
                        WHERE NOME = ? AND DTNASC = ?
                    """
                    cur_fb.execute(sql_up, (
                        cpf_limpo, end, num, bairro, ddd, tel,
                        sus_limpo, co_lograd, nome_alvo, dt_nasc
                    ))
                    con_fb.commit()
                    sucessos += 1
                else:
                    # --- INSERT ---
                    sql_in = """
                        INSERT INTO CADCNS (
                            CNS, NOME, NUM_CPF, DTNASC, SEXO, RACA,
                            LOGPCN, NUMPCN, BAIRRO_PCNTE, CEPPCN,
                            IBGE, DDTEL_PCNTE, TEL_PCNTE, CO_LOGRAD
                        ) VALUES (
                            ?, ?, ?, ?, ?, '03', ?, ?, ?,
                            '59575000', '240360', ?, ?, ?
                        )
                    """
                    cur_fb.execute(sql_in, (
                        sus_limpo, nome_bpa, cpf_limpo, dt_nasc,
                        sexo, end, num, bairro, ddd, tel, co_lograd
                    ))
                    con_fb.commit()
                    sucessos += 1
                    lista_novos.append(
                        f"[NOVO] {nome_bpa} ({dt_nasc}) "
                        f"| Logradouro: {co_lograd}"
                    )

            except Exception as e:
                con_fb.rollback()
                falhas += 1
                lista_erros.append(f"Erro em {p['nome']}: {e}")

    except Exception as e_fatal:
        print(f"\nErro Critico: {e_fatal}")

    finally:
        if 'con_fb' in locals():
            con_fb.close()
        if 'con_sqlite' in locals():
            con_sqlite.close()

        # Gera relatório
        nome_log = f"log_sincronia_{mes}_{ano}.txt"
        with open(nome_log, "w", encoding="utf-8") as f:
            f.write(
                f"--- RELATORIO DE PRODUCAO HMPCF: "
                f"{mes}/{ano} ---\n"
            )
            f.write(
                f"Sincronizados: {sucessos} | Falhas: {falhas}\n"
            )
            f.write("-" * 50 + "\n\n")
            if lista_novos:
                f.write("--- CADASTRADOS/ATUALIZADOS ---\n")
                for n in lista_novos:
                    f.write(n + "\n")
            if lista_erros:
                f.write("\n--- ERROS ENCONTRADOS ---\n")
                for e in lista_erros:
                    f.write(e + "\n")

        print(
            f"\nSincronizacao finalizada! "
            f"Relatorio salvo em: {nome_log}"
        )


if __name__ == "__main__":
    sincronizar()
