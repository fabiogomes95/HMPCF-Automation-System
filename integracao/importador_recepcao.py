"""
IMPORTADOR_RECEPCAO.PY — Importa CSVs da Recepção pro SQLite (Smart Update)
=============================================================================
Esse script varre a pasta atual em busca de arquivos .csv da recepção
e importa os pacientes pro banco SQLite.

O DIFERENCIAL é o "Smart Update":
- Se o paciente JÁ EXISTE no banco (pelo SUS), eu só preencho
  os campos que estão VAZIOS — NUNCA sobrescrevo dados preenchidos.
- Se o paciente NÃO EXISTE, eu insiro um novo registro.

Isso é crucial porque a recepção às vezes exporta CSVs com dados
parciais, e eu não quero perder informações já cadastradas.
"""

import sqlite3
import csv
import os
import sys
import glob
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging_setup import logger
from utils import apenas_numeros, valida_cns


def pega_coluna_segura(linha: list[str], indice: int) -> str:
    """
    Pega uma coluna da linha sem estourar IndexError.
    Se o índice não existe na linha, devolve string vazia.
    """
    if len(linha) > indice:
        return linha[indice].strip()
    return ""


def executar_importacao_lote(separador: str = ";") -> str:
    """
    Importa TODOS os CSVs da pasta pro SQLite.
    
    Parâmetros:
        separador: ";" ou "," — o delimitador do CSV
    
    Regras:
        - Ignora pacientes com SUS inválido
        - Se o SUS já existe no banco: preenche só campos vazios
        - Se o SUS não existe: insere novo
        - Ignora o arquivo "pacientes.csv" (que é de exportação)
    
    Retorna relatório com números de: novos, atualizados, intactos, ignorados.
    """
    # Localiza o hospital.db (na pasta atual ou na raiz)
    caminho_db = os.path.join(os.path.dirname(__file__), 'hospital.db')
    if not os.path.exists(caminho_db):
        caminho_db = os.path.join(os.path.dirname(__file__), '..', 'hospital.db')

    # Lista CSVs (excluindo pacientes.csv)
    arquivos_csv = glob.glob("*.csv")
    arquivos_csv = [
        arq for arq in arquivos_csv if arq.lower() != "pacientes.csv"
    ]

    if not arquivos_csv:
        return "Nenhum arquivo CSV da recepcao encontrado na pasta."

    inseridos_novos = 0
    atualizados_parciais = 0
    intactos_perfeitos = 0
    ignorados_erro = 0
    detalhes_novos = []

    try:
        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor()

        for arquivo in arquivos_csv:
            with open(arquivo, mode='r', encoding='utf-8', errors='ignore') as f:
                leitor = csv.reader(f, delimiter=separador)
                next(leitor, None)  # Pula o cabeçalho

                for linha in leitor:
                    if len(linha) < 10:
                        continue

                    # Extraio campos do CSV
                    nome_csv = pega_coluna_segura(linha, 1).upper()
                    dn_csv = pega_coluna_segura(linha, 2)
                    sexo_csv = pega_coluna_segura(linha, 4).upper()
                    cpf_csv = apenas_numeros(pega_coluna_segura(linha, 8))
                    sus_csv = apenas_numeros(pega_coluna_segura(linha, 9))

                    # --- VALIDAÇÃO DO SUS ---
                    # Só aceito pacientes com SUS válido (15 dígitos)
                    if not sus_csv or not valida_cns(sus_csv):
                        ignorados_erro += 1
                        continue

                    # --- VERIFICO SE JÁ EXISTE NO BANCO ---
                    cursor.execute(
                        "SELECT NUM_CPF, NOME, DTNASC, SEXO FROM pacientes WHERE CNS = ?",
                        (sus_csv,)
                    )
                    paciente_banco = cursor.fetchone()

                    if paciente_banco:
                        # --- SMART UPDATE ---
                        # Só atualizo campos que estão VAZIOS no banco
                        db_cpf, db_nome, db_dn, db_sexo = paciente_banco
                        campos_para_atualizar = []
                        valores_para_atualizar = []

                        # CPF: só atualiza se o banco estiver vazio
                        if (not db_cpf or db_cpf.strip() == "") and cpf_csv:
                            campos_para_atualizar.append("NUM_CPF = ?")
                            valores_para_atualizar.append(cpf_csv)

                        # Nome: só atualiza se o banco estiver vazio
                        if (not db_nome or db_nome.strip() == "") and nome_csv:
                            campos_para_atualizar.append("NOME = ?")
                            valores_para_atualizar.append(nome_csv)

                        # Data de nascimento: só se vazio
                        if (not db_dn or db_dn.strip() == "") and dn_csv:
                            campos_para_atualizar.append("DTNASC = ?")
                            valores_para_atualizar.append(dn_csv)

                        # Sexo: só se vazio E for M/F/I
                        if (not db_sexo or db_sexo.strip() == "") \
                                and sexo_csv in ['M', 'F', 'I']:
                            campos_para_atualizar.append("SEXO = ?")
                            valores_para_atualizar.append(sexo_csv)

                        if campos_para_atualizar:
                            sql_update = (
                                f"UPDATE pacientes SET "
                                f"{', '.join(campos_para_atualizar)} "
                                f"WHERE CNS = ?"
                            )
                            valores_para_atualizar.append(sus_csv)
                            try:
                                cursor.execute(sql_update, valores_para_atualizar)
                                atualizados_parciais += 1
                            except sqlite3.IntegrityError:
                                ignorados_erro += 1
                        else:
                            # Todos os campos já preenchidos — paciente intacto
                            intactos_perfeitos += 1
                    else:
                        # --- NOVO PACIENTE ---
                        try:
                            cursor.execute('''
                                INSERT INTO pacientes (CNS, NUM_CPF, NOME, DTNASC, SEXO)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (sus_csv, cpf_csv, nome_csv, dn_csv, sexo_csv))
                            inseridos_novos += 1
                            detalhes_novos.append(
                                f"NOME: {nome_csv} | SUS: {sus_csv}"
                            )
                        except sqlite3.IntegrityError:
                            ignorados_erro += 1

        conn.commit()
        conn.close()

        # --- GERA RELATÓRIO DE NOVOS CADASTROS ---
        if detalhes_novos:
            nome_relatorio = "relatorio_importacao.txt"
            with open(nome_relatorio, "w", encoding="utf-8") as f_txt:
                f_txt.write(
                    "RELATORIO DE NOVOS PACIENTES CADASTRADOS\n"
                )
                f_txt.write(
                    f"DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                )
                f_txt.write("-" * 60 + "\n")
                for registro in detalhes_novos:
                    f_txt.write(registro + "\n")

        return (
            f"Processamento concluido!\n"
            f"Arquivos lidos: {len(arquivos_csv)}\n"
            f"Novos pacientes: {inseridos_novos}\n"
            f"Atualizados: {atualizados_parciais}\n"
            f"Intactos: {intactos_perfeitos}\n"
            f"Ignorados: {ignorados_erro}"
        )

    except Exception as e:
        return f"Erro durante a importacao: {e}"


if __name__ == "__main__":
    sep = input("Separador (, ou ;): ").strip() or ";"
    logger.info(executar_importacao_lote(sep))
