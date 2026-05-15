"""
SINCRONIZAR_FIREBIRD.PY — Sincronizador SQLite → Firebird
===================================================================
Esse script integra os pacientes do hospital.db (SQLite) com o banco
oficial do BPA (BPAMAG.GDB / Firebird).

Fluxo:
1. Lê pacientes do SQLite
2. Pra cada paciente, busca no Firebird por NOME + DATA DE NASCIMENTO
3. Se existe → UPDATE (atualiza endereço, telefone, CPF, SUS)
4. Se não existe → INSERT (cadastra novo paciente no GDB)

Por que NOME + DATA? Porque o GDB não tem CPF confiável em muitos
registros antigos. Nome + data de nascimento é a chave mais segura.
"""

import sqlite3
import firebirdsql
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import apenas_numeros, remove_accents
from config import FIREBIRD_USER, FIREBIRD_PASSWORD


def sincronizar_sqlite_para_gdb(mes_ano: str = "", caminho_gdb: str = "") -> str:
    """
    Sincroniza pacientes do SQLite pro Firebird.
    
    Parâmetros:
        mes_ano: "03/2026" — filtra por mês (vazio = todos)
        caminho_gdb: caminho do arquivo .GDB do Firebird
    
    Retorna relatório com: atualizados, novos cadastros, erros.
    """
    # Localiza o hospital.db
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    caminho_sqlite = os.path.join(pasta_script, '..', 'hospital.db')

    if not os.path.exists(caminho_sqlite):
        return "Erro: hospital.db nao encontrado na raiz do projeto."

    if not caminho_gdb:
        return "Erro: Nenhum arquivo .gdb informado."

    try:
        # --- CONEXÃO SQLITE ---
        conn_sq = sqlite3.connect(caminho_sqlite)
        conn_sq.row_factory = sqlite3.Row
        cursor_sq = conn_sq.cursor()

        # Consulta: com ou sem filtro de mês
        query = "SELECT DISTINCT p.* FROM pacientes p"
        params = []
        if mes_ano:
            query += """
                JOIN atendimentos a ON p.sus = a.sus
                WHERE a.data_atendimento LIKE ?
                   OR a.data_atendimento LIKE ?
            """
            parts = mes_ano.split('/')
            if len(parts) == 2:
                mm, yyyy = parts
                params.extend([f"%{mm}/{yyyy}%", f"%{yyyy}-{mm}%"])
            else:
                params.extend([f"%{mes_ano}%", f"%{mes_ano}%"])

        cursor_sq.execute(query, params)
        pacientes_db = cursor_sq.fetchall()
        conn_sq.close()

        if not pacientes_db:
            return "Nenhum paciente encontrado para este filtro no hospital.db."

        # --- CONEXÃO FIREBIRD ---
        conexao_fb = firebirdsql.connect(
            host='localhost',
            database=caminho_gdb,
            user=FIREBIRD_USER,
            password=FIREBIRD_PASSWORD,
            charset='WIN1252'
        )
        cursor_fb = conexao_fb.cursor()

    except Exception as e:
        return f"Erro de conexao: {e}"

    sucessos_upd = 0  # Pacientes atualizados
    sucessos_ins = 0  # Novos cadastros
    erros = 0
    lista_erros = []

    # --- PROCESSAMENTO PACIENTE POR PACIENTE ---
    for p in pacientes_db:
        try:
            nome = remove_accents(p['nome'])[:30].strip()
            if not nome or nome == 'NAN':
                continue

            cpf = apenas_numeros(p['cpf'])[:11] \
                if 'cpf' in p.keys() and p['cpf'] else ""
            sus = apenas_numeros(p['sus'])[:15] \
                if 'sus' in p.keys() and p['sus'] else ""

            # Data de nascimento: converte pra YYYYMMDD
            dn_raw = str(p['dn']).strip() \
                if 'dn' in p.keys() and p['dn'] else ""
            dt_nasc = '19900101'
            if '-' in dn_raw:
                parts = dn_raw.split('-')
                if len(parts) >= 3:
                    dt_nasc = (
                        f"{parts[0][:4].zfill(4)}"
                        f"{parts[1][:2].zfill(2)}"
                        f"{parts[2][:2].zfill(2)}"
                    )
            elif '/' in dn_raw:
                parts = dn_raw.split('/')
                if len(parts) >= 3:
                    dt_nasc = (
                        f"{parts[2][:4].zfill(4)}"
                        f"{parts[1][:2].zfill(2)}"
                        f"{parts[0][:2].zfill(2)}"
                    )
            if len(dt_nasc) != 8:
                dt_nasc = '19900101'

            sexo_raw = str(p['sexo']).strip().upper() \
                if 'sexo' in p.keys() and p['sexo'] else ""
            sexo = sexo_raw[:1] if sexo_raw in ['M', 'F'] else 'I'

            rua = remove_accents(p['endereco'])[:25] \
                if 'endereco' in p.keys() and p['endereco'] else ""
            numero = remove_accents(p['numero'])[:5] \
                if 'numero' in p.keys() and p['numero'] else "S/N"
            bairro = remove_accents(p['bairro'])[:15] \
                if 'bairro' in p.keys() and p['bairro'] else ""

            # Telefone: separa DDD + número
            tel_full = apenas_numeros(p['tel']) \
                if 'tel' in p.keys() and p['tel'] else ""
            if len(tel_full) <= 9 and tel_full:
                tel_full = "84" + tel_full
            ddd = tel_full[:2] if len(tel_full) >= 10 else ''
            tel = tel_full[-8:] if len(tel_full) >= 8 else tel_full

            co_lograd = "081"  # Código de logradouro padrão

            # --- BUSCA NO FIREBIRD POR NOME + DATA ---
            cursor_fb.execute(
                "SELECT NOME FROM CADCNS WHERE NOME = ? AND DTNASC = ?",
                (nome, dt_nasc)
            )
            reg = cursor_fb.fetchone()

            if reg:
                # --- JÁ EXISTE: UPDATE ---
                sql_up = """
                    UPDATE CADCNS SET
                        NUM_CPF = ?, LOGPCN = ?, NUMPCN = ?,
                        BAIRRO_PCNTE = ?, DDTEL_PCNTE = ?,
                        TEL_PCNTE = ?, CNS = ?, CO_LOGRAD = ?
                    WHERE NOME = ? AND DTNASC = ?
                """
                cursor_fb.execute(sql_up, (
                    cpf, rua, numero, bairro, ddd, tel, sus,
                    co_lograd, nome, dt_nasc
                ))
                sucessos_upd += 1
            else:
                # --- NÃO EXISTE: INSERT ---
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
                cursor_fb.execute(sql_in, (
                    sus, nome, cpf, dt_nasc, sexo,
                    rua, numero, bairro, ddd, tel, co_lograd
                ))
                sucessos_ins += 1

        except Exception as e_linha:
            erros += 1
            lista_erros.append(
                f"Erro no paciente {p['nome']}: {str(e_linha)}"
            )

    # --- FINALIZAÇÃO ---
    conexao_fb.commit()
    conexao_fb.close()

    msg = (
        f"Sincronizacao Concluida!\n"
        f"Pacientes Atualizados: {sucessos_upd}\n"
        f"Novos Cadastros: {sucessos_ins}\n"
        f"Erros: {erros}"
    )
    if erros > 0:
        with open(
            "log_erros_sqlite_para_gdb.txt", "w", encoding="utf-8"
        ) as f:
            f.write("ERROS ENCONTRADOS DURANTE A INTEGRACAO:\n\n")
            f.write("\n".join(lista_erros))
        msg += "\nLog de erros salvo em 'log_erros_sqlite_para_gdb.txt'."

    return msg


if __name__ == "__main__":
    mes = input("Mes (ex: 03/2026) ou Enter para todos: ").strip()
    gdb = input("Caminho do .gdb: ").strip()
    logger.info(sincronizar_sqlite_para_gdb(mes, gdb))
