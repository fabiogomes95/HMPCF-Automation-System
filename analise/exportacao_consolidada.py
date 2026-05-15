"""
EXPORTACAO_CONSOLIDADA.PY — Gera todos os relatórios e empacota em ZIP
========================================================================
Executa: dashboard PNG, planilha Excel, auditoria PDF, análise CSV PDF.
Tudo num único arquivo .zip na pasta exports/.
"""

import os
import zipfile
from datetime import datetime
from logging_setup import logger

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS_DIR = os.path.join(SRC_DIR, "exports")


def exportar_tudo() -> str:
    if not os.path.exists(EXPORTS_DIR):
        os.makedirs(EXPORTS_DIR, exist_ok=True)

    from analise import dashboard_visual, planilha_producao, auditoria_periodica, analise_anual_csv

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_zip = f"relatorio_consolidado_{timestamp}.zip"
    caminho_zip = os.path.join(EXPORTS_DIR, nome_zip)

    arquivos_gerados: list[str] = []

    try:
        logger.info("Gerando dashboard...")
        res = dashboard_visual.gerar_dashboard()
        if "dashboard" in res.lower():
            for f in os.listdir(SRC_DIR):
                if f.startswith("dashboard") and f.endswith(".png"):
                    arquivos_gerados.append(os.path.join(SRC_DIR, f))

        logger.info("Gerando planilha de producao...")
        mes_atual = datetime.now().strftime("%m-%Y")
        res = planilha_producao.gerar_relatorio_mes(mes_atual)
        if "xlsx" in res.lower():
            for f in os.listdir(SRC_DIR):
                if f.startswith("producao") and f.endswith(".xlsx"):
                    arquivos_gerados.append(os.path.join(SRC_DIR, f))

        logger.info("Gerando auditoria periodica...")
        res = auditoria_periodica.gerar_auditoria_periodo("1")
        if ".pdf" in res.lower():
            for f in os.listdir(SRC_DIR):
                if f.startswith("auditoria") and f.endswith(".pdf"):
                    arquivos_gerados.append(os.path.join(SRC_DIR, f))

        logger.info("Gerando analise de CSVs...")
        res = analise_anual_csv.analisar_csvs_para_pdf()
        if ".pdf" in res.lower():
            for f in os.listdir(SRC_DIR):
                if f.startswith("analise_csv") and f.endswith(".pdf"):
                    arquivos_gerados.append(os.path.join(SRC_DIR, f))
    except Exception as e:
        logger.error(f"Erro ao gerar relatorios: {e}")

    if not arquivos_gerados:
        return "Nenhum relatorio foi gerado para consolidar."

    try:
        with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for caminho in arquivos_gerados:
                if os.path.exists(caminho):
                    zf.write(caminho, os.path.basename(caminho))
                    os.remove(caminho)

        tamanho_kb = os.path.getsize(caminho_zip) / 1024
        msg = f"SUCESSO! ZIP gerado: {nome_zip} ({tamanho_kb:.0f} KB, {len(arquivos_gerados)} arquivos)"
        logger.info(msg)
        return msg

    except Exception as e:
        msg = f"Erro ao criar ZIP: {e}"
        logger.error(msg)
        return msg
