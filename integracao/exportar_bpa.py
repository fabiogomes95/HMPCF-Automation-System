"""
EXPORTAR_BPA.PY — Exporta SQLite → TXT posicional Datasus
=================================================================
Esse script gera o arquivo TXT que o sistema BPA do governo importa.

O formato é posicional: cada campo TEM que estar numa posição exata
da linha, senão o sistema do governo rejeita.

Exemplo de linha gerada:
  898765432109876MARIA JOSE SILVA        19900101M24036001003    59575000081

Pra usar:
  - Direto no terminal: python integracao/exportar_bpa.py
  - Via web: Painel de Gestão → Integração → Exportar SQLite → TXT BPA
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import apenas_numeros, remove_accents
from config import CNS_PROFISSIONAL, CBO_CODIGO, FOLHA_CODIGO, SEQ_PROFISSIONAL

E_CBO = CBO_CODIGO
F_FOLHA = FOLHA_CODIGO
G_SEQ = SEQ_PROFISSIONAL
H_CNS_PROF = CNS_PROFISSIONAL


def exportar_dados(mes_ano="", caminho_salvar=""):
    """
    Função principal que exporta pacientes do SQLite pro TXT BPA.
    
    Parâmetros:
        mes_ano: "03/2026" — filtra por mês (vazio = todos)
        caminho_salvar: onde salvar o .txt (vazio = BPA_EXPORTADO_SQLITE.txt)
    
    Retorna mensagem com: total exportado, barrados, log de erros.
    """
    # Localiza o hospital.db na raiz do projeto
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(pasta_script, '..', 'hospital.db')

    if not os.path.exists(caminho_banco):
        return f"Erro: Banco de dados nao encontrado em {caminho_banco}"

    try:
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()

        # --- CONSULTA PRINCIPAL ---
        # Pego DISTINCT pra não repetir paciente
        query = """
            SELECT DISTINCT p.sus, p.nome, p.dn, p.sexo,
                   p.endereco, p.numero, p.bairro, p.tel
            FROM pacientes p
        """
        params = []

        # Se filtrou por mês, faço JOIN com atendimentos
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

        cursor.execute(query, params)
        pacientes_db = cursor.fetchall()
        conn.close()

        if not pacientes_db:
            return "Nenhum paciente encontrado para este filtro."

        lines, erros = [], []

        for row in pacientes_db:
            # --- TRATAMENTO DO SUS ---
            # Pego só a parte antes do ponto (se tiver)
            raw_sus = str(row[0]).split('.')[0] if row[0] else ""
            cns = apenas_numeros(raw_sus)

            # Nome: removo acentos e limito a 30 caracteres
            nome = remove_accents(
                str(row[1]) if row[1] else "NOME DESCONHECIDO"
            ).strip()

            # --- TRATAMENTO DA DATA ---
            # Aceito formato ISO (AAAA-MM-DD) ou BR (DD/MM/AAAA)
            dn_raw = str(row[2]).strip() if row[2] else ""
            data_f = None
            if '-' in dn_raw:
                parts = dn_raw.split('-')
                if len(parts) >= 3:
                    data_f = f"{parts[0][:4]}{parts[1][:2]}{parts[2][:2]}"
            elif '/' in dn_raw:
                parts = dn_raw.split('/')
                if len(parts) >= 3:
                    data_f = f"{parts[2][:4]}{parts[1][:2]}{parts[0][:2]}"
            if not data_f or len(data_f) != 8:
                data_f = "19900101"  # Data padrão segura

            # Sexo: M, F ou I (Indefinido)
            sexo_raw = str(row[3]).strip().upper() if row[3] else ""
            sexo = sexo_raw[:1] if sexo_raw[:1] in ['M', 'F'] else 'I'

            # Endereço com padding e truncamento
            rua_f = remove_accents(
                str(row[4] if row[4] else "")
            ).strip().ljust(30)[:30]
            num_f = remove_accents(
                str(row[5] if row[5] else "")
            ).strip().ljust(5)[:5]
            if not num_f.strip():
                num_f = "S/N".ljust(5)
            bairro_f = remove_accents(
                str(row[6] if row[6] else "")
            ).strip().ljust(30)[:30]

            # Telefone com DDD (11 dígitos)
            tel_digits = apenas_numeros(str(row[7]) if row[7] else "")
            telefone_f = "".ljust(11)
            if 8 <= len(tel_digits) <= 11:
                if len(tel_digits) <= 9:
                    tel_digits = "84" + tel_digits  # DDD padrão
                telefone_f = tel_digits.ljust(11)[:11]

            # --- VALIDAÇÃO DO SUS ---
            # Se não tem 15 dígitos, barro o paciente
            if len(cns) != 15:
                erros.append(
                    f"PACIENTE: {nome[:30]} | "
                    f"MOTIVO: SUS Invalido ou Ausente ({cns})"
                )
                continue

            # --- MONTAGEM DA LINHA POSICIONAL ---
            nome_f = nome.ljust(30)[:30]
            line = (
                f"{cns}{nome_f}{data_f}{sexo}"
                f"{E_CBO}{F_FOLHA}{G_SEQ}    "
                f"{H_CNS_PROF}{rua_f}          "
                f"{num_f}{bairro_f}{telefone_f}"
            )
            lines.append(line)

        # --- SALVA O ARQUIVO TXT ---
        if not caminho_salvar:
            caminho_salvar = "BPA_EXPORTADO_SQLITE.txt"

        with open(caminho_salvar, 'w', encoding='cp1252', errors='replace') as out_f:
            for line in lines:
                out_f.write(line + '\r\n')

        # --- RELATÓRIO ---
        relatorio = (
            f"Exportacao concluida!\n"
            f"Pacientes salvos: {len(lines)}\n"
            f"Barrados (Sem SUS): {len(erros)}"
        )
        if erros:
            log_path = caminho_salvar.replace('.txt', '_ERROS.txt')
            with open(log_path, 'w', encoding='utf-8') as log_f:
                log_f.write("--- RELATORIO DE EXPORTACAO ---\n")
                log_f.write(f"Sucessos gerados: {len(lines)}\n")
                log_f.write(f"Erros barrados: {len(erros)}\n")
                log_f.write("-------------------------------\n\n")
                for e in erros:
                    log_f.write(e + '\n')
            relatorio += f"\nLog de erros: {log_path}"

        return relatorio

    except Exception as e:
        return f"Erro durante a execucao: {e}"


if __name__ == "__main__":
    mes = input("Digite o mes (ex: 03/2026) ou Enter para todos: ").strip()
    logger.info(exportar_dados(mes))
