"""
APP_PAINEL.PY — Servidor Web do Painel de Gestão (Eel | Porta 8001)
=====================================================================
Esse é o cérebro do sistema — o "Painel de Controle" que a gestão
do hospital usa pra:
- Digitar lotes manuais no BPA
- Fazer triagem de pacientes (extrair CPF/SUS de dados sujos)
- Executar o Robô RPA (digitação automática)
- Integrar com o Firebird (sincronizar SQLite → GDB)
- Exportar arquivos TXT pro Datasus
- Limpar duplicatas e NULLs no banco oficial

Ele funciona como um "hub" que importa todos os módulos
(automacao/, integracao/) e expõe as funções via Eel pro frontend.

No final, carrega a base inteira do Firebird pra RAM
pra fazer buscas ultrarrápidas (sem consultar o banco toda hora).
"""

import os
import glob
from datetime import datetime
import eel
import firebirdsql
import sys
from logging_setup import logger
from config import FIREBIRD_PATH, FIREBIRD_USER, FIREBIRD_PASSWORD
from auditoria_log import registrar as log_auditoria
from integracao.backup_utils import fazer_backup, listar_backups

# =====================================================================
# CONFIGURAÇÃO DE DIRETÓRIOS
# =====================================================================
# Pego o diretório atual pra construir caminhos absolutos
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_AUTOMACAO = os.path.join(PASTA_ATUAL, "automacao")
PASTA_INTEGRACAO = os.path.join(PASTA_ATUAL, "integracao")

# Inicializo o Eel apontando pra pasta web_painel/
eel.init('web_painel')

# =====================================================================
# IMPORTAÇÕES DOS MÓDULOS
# =====================================================================
# Trago os "trabalhadores" de cada módulo
from automacao import executor_rpa
from automacao import cpf_sus
from automacao import digitacao

# Adiciono a pasta integracao ao sys.path pra importar os scripts
sys.path.insert(0, PASTA_INTEGRACAO)
from integracao import exportar_bpa
from integracao import converter_csv
from integracao import importador_recepcao
from integracao import sincronizar_firebird
from integracao import sincronizar_contingencia
from integracao import corrigir_nulls
from integracao import duplicatas_gdb

# =====================================================================
# 5. MÓDULO ANÁLISE (BI)
# =====================================================================
from analise import dashboard_visual
from analise import planilha_producao
from analise import auditoria_periodica
from analise import analise_anual_csv
from analise import historico_paciente

# =====================================================================
# CARGA DA BASE DO FIREBIRD NA RAM
# =====================================================================
# Lista global que vai segurar todos os pacientes do BPAMAG.GDB
BASE_PACIENTES = []


def carregar_base() -> None:
    """
    Carrega TODO o banco do Firebird pra memória RAM.
    
    Por que? Porque pesquisar no Firebird toda vez que o usuário
    digita um nome é MUITO lento (o banco tá em rede).
    Colocando na RAM, a busca fica instantânea.
    
    Cada paciente vira um dicionário com: sus, nome, dtnasc, cpf
    """
    global BASE_PACIENTES
    caminho_gdb = FIREBIRD_PATH

    try:
        logger.info("Carregando pacientes para a memoria...")

        con = firebirdsql.connect(
            host='localhost',
            database=caminho_gdb,
            user=FIREBIRD_USER,
            password=FIREBIRD_PASSWORD,
            charset='WIN1252'
        )
        cur = con.cursor()

        # Pego TODOS os pacientes da tabela CADCNS
        cur.execute("SELECT CNS, NOME, DTNASC, NUM_CPF FROM CADCNS")

        for r in cur.fetchall():
            sus = str(r[0] or "").strip()
            nome = str(r[1] or "").strip().upper()
            dn_raw = str(r[2] or "").strip()
            cpf = str(r[3] or "").strip()

            # Data de nascimento: formato YYYYMMDD → DD/MM/YYYY
            if len(dn_raw) == 8:
                dtnasc = f"{dn_raw[6:8]}/{dn_raw[4:6]}/{dn_raw[0:4]}"
            else:
                dtnasc = "  /  /    "

            BASE_PACIENTES.append({
                'sus': sus,
                'nome': nome,
                'dtnasc': dtnasc,
                'cpf': cpf
            })

        con.close()
        logger.info(
            f"SUCESSO! {len(BASE_PACIENTES)} pacientes na RAM. "
            f"Busca ultrarrápida ativada!"
        )

    except Exception as e:
        logger.error(f"Erro Critico ao carregar base: {e}")


# =====================================================================
# 1. MÓDULO DIGITADOR MANUAL
# =====================================================================

@eel.expose
def buscar_pacientes_fb(termo: str) -> list[dict]:
    """Busca pacientes na RAM (não no banco)."""
    return digitacao.buscar_pacientes_memoria(termo, BASE_PACIENTES)


@eel.expose
def registrar_cabecalho_digitacao(arquivo: str, medico: str, data: str) -> bool:
    """Cria cabeçalho de produção (médico + data) no arquivo TXT."""
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    return digitacao.criar_cabecalho_producao(caminho, medico, data)


@eel.expose
def adicionar_paciente_txt(arquivo: str, documento: str) -> bool:
    """Adiciona uma ficha de paciente no arquivo TXT de produção."""
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    return digitacao.adicionar_ficha_producao(caminho, documento)


# =====================================================================
# 2. MÓDULO TRIAGEM E LIMPEZA
# =====================================================================

@eel.expose
def rodar_limpador(data_lote: str, enfermeiros_str: str) -> str:
    """Processa CPF/SUS sujos e organiza lotes por enfermeiro."""
    log_auditoria("rodar_limpador", f"data={data_lote}")
    caminho_sujo = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")

    # Extrai CPF/SUS dos dados bagunçados
    docs = cpf_sus.processar_lista(caminho_sujo)
    if not docs:
        return "Erro: Nenhum paciente valido encontrado."

    # Lista de enfermeiros (separados por vírgula)
    profs = [p.strip().upper() for p in enfermeiros_str.split(',') if p.strip()]
    if not profs:
        profs = ["PROFISSIONAL SEM NOME"]

    resultado_final = []
    chunk_size = 99  # Limite do BPA
    idx_p = 0

    # Divido os pacientes em chunks de 99
    for i in range(0, len(docs), chunk_size):
        chunk = docs[i:i + chunk_size]
        # Cada chunk vai pra um enfermeiro (rotativo)
        prof_atual = profs[idx_p % len(profs)]
        idx_p += 1

        resultado_final.append(f"PROFISSIONAL: {prof_atual} | DATA: {data_lote}")
        resultado_final.extend(chunk)
        resultado_final.append("")

    conteudo_str = "\n".join(resultado_final)
    caminho_prod = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")

    with open(caminho_prod, 'w', encoding='utf-8') as f:
        f.write(conteudo_str)

    return conteudo_str


@eel.expose
def salvar_texto_sujo(conteudo: str) -> None:
    """Salva o conteúdo bruto (dados sujos) no arquivo cpf_sus.txt."""
    caminho = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)


# =====================================================================
# 3. MÓDULO ROBÔ RPA
# =====================================================================

@eel.expose
def preparar_rpa(nome_arquivo: str) -> dict:
    """
    Prepara os lotes pra digitação automática.
    Lê o arquivo de produção e monta lotes de 99 pacientes
    com os dados completos (incluindo busca na RAM por nome).
    """
    caminho_completo = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    if os.path.exists(caminho_completo):
        lotes, erro = executor_rpa.preparar_lotes(
            caminho_completo, BASE_PACIENTES
        )
        return {"lotes": lotes, "erro": erro}
    return {"lotes": [], "erro": "Ficheiro nao encontrado."}


@eel.expose
def digitar_lote_rpa(medico: str, data: str, cargo: str, pacientes: list) -> str:
    """Executa a digitação automática via PyAutoGUI."""
    log_auditoria("digitar_lote_rpa", f"medico={medico} data={data} pacientes={len(pacientes)}")
    def callback(msg):
        eel.atualizar_progresso_web(msg)()

    executor_rpa.executar_pyautogui(
        medico, data, cargo, pacientes, callback
    )
    return "OK"


@eel.expose
def listar_producoes() -> list[str]:
    """Lista todos os arquivos .txt da pasta automacao/."""
    arquivos = glob.glob(os.path.join(PASTA_AUTOMACAO, "*.txt"))
    nomes = [os.path.basename(a) for a in arquivos]
    nomes.sort(reverse=True)  # Mais recentes primeiro
    return nomes


@eel.expose
def ler_producao(nome_arquivo: str) -> str:
    """Lê o conteúdo de um arquivo .txt da pasta automacao/."""
    caminho = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    if not os.path.exists(caminho):
        return ""
    with open(caminho, 'r', encoding='utf-8') as f:
        return f.read()


@eel.expose
def ler_txt_pacientes() -> str:
    """Atalho pra ler o arquivo prod_enfermeiros.txt."""
    return ler_producao("prod_enfermeiros.txt")


@eel.expose
def salvar_txt_pacientes(conteudo: str) -> str:
    """Salva conteúdo no arquivo prod_enfermeiros.txt."""
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    return "Salvo!"


# =====================================================================
# 4. MÓDULO INTEGRAÇÃO
# =====================================================================
# Cada função aqui expõe um script do integracao/ via Eel.
# Os parâmetros são opcionais — se vazios, os scripts usam
# valores padrão ou perguntam via terminal.

@eel.expose
def integracao_exportar_bpa(mes_ano: str = "", caminho_salvar: str = "") -> str:
    """Exporta SQLite → TXT BPA (Datasus)."""
    try:
        return exportar_bpa.exportar_dados(mes_ano, caminho_salvar)
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def integracao_converter_csv(caminho_csv: str = "", caminho_salvar: str = "") -> str:
    """Converte CSVs antigos → TXT BPA."""
    try:
        return converter_csv.processar_csv_antigo(caminho_csv, caminho_salvar)
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def integracao_importar_lote(separador: str = ";") -> str:
    """Importa CSVs da recepção pro SQLite (Smart Update)."""
    try:
        return importador_recepcao.executar_importacao_lote(separador)
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def integracao_sincronizar_firebird(mes_ano: str = "", caminho_gdb: str = "") -> str:
    """Sincroniza SQLite → Firebird (com backup automático)."""
    gdb = caminho_gdb or FIREBIRD_PATH
    fazer_backup(gdb, "pre_sincronizar")
    log_auditoria("sincronizar_firebird", f"mes={mes_ano} gdb={gdb}")
    try:
        return sincronizar_firebird.sincronizar_sqlite_para_gdb(
            mes_ano, caminho_gdb
        )
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def integracao_sincronizar_contingencia(caminho_csv: str = "") -> str:
    """Importa planilhas offline (contingência)."""
    try:
        return sincronizar_contingencia.sincronizar_contingencia(caminho_csv)
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def integracao_aniquilar_nulls(caminho_gdb: str = "") -> str:
    """Remove NULLs do Firebird (com backup automático)."""
    gdb = caminho_gdb or FIREBIRD_PATH
    fazer_backup(gdb, "pre_aniquilar_nulls")
    log_auditoria("aniquilar_nulls", f"gdb={gdb}")
    try:
        return corrigir_nulls.aniquilar_nulls_bpa(caminho_gdb)
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def integracao_limpar_duplicatas(caminho_gdb: str = "") -> str:
    """Remove duplicatas do Firebird (com backup automático)."""
    gdb = caminho_gdb or FIREBIRD_PATH
    fazer_backup(gdb, "pre_limpar_duplicatas")
    log_auditoria("limpar_duplicatas", f"gdb={gdb}")
    try:
        return duplicatas_gdb.limpar_duplicados_gdb(caminho_gdb)
    except Exception as e:
        return f"Erro: {e}"


# =====================================================================
# 5. MÓDULO ANÁLISE / BI
# =====================================================================

@eel.expose
def analise_gerar_dashboard() -> str:
    """Gera dashboard PNG + relatório Top 20."""
    log_auditoria("gerar_dashboard")
    try:
        return dashboard_visual.gerar_dashboard()
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def analise_gerar_relatorio_mes(mes_ref: str) -> str:
    """Gera planilha Excel de produção para um mês."""
    log_auditoria("gerar_relatorio_mes", mes_ref)
    try:
        return planilha_producao.gerar_relatorio_mes(mes_ref)
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def analise_gerar_auditoria_periodo(opcao: str) -> str:
    """Gera PDF de auditoria: '1', '3' ou '6' meses."""
    log_auditoria("gerar_auditoria_periodo", f"{opcao} mes(es)")
    try:
        return auditoria_periodica.gerar_auditoria_periodo(opcao)
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def analise_analisar_csvs_para_pdf() -> str:
    """Analisa CSVs antigos e gera PDF com Top 20."""
    log_auditoria("analisar_csvs_para_pdf")
    try:
        return analise_anual_csv.analisar_csvs_para_pdf()
    except Exception as e:
        return f"Erro: {e}"


@eel.expose
def analise_buscar_historico(termo: str) -> str:
    """Busca histórico de paciente por nome, CPF ou SUS."""
    log_auditoria("buscar_historico", termo[:80])
    try:
        return historico_paciente.buscar_por_termo(termo)
    except Exception as e:
        return f"Erro: {e}"


# =====================================================================
# 6. CONSULTA ATENDIMENTOS (RECEPÇÃO) — Tudo na RAM
# =====================================================================
from analise.consulta_recepcao import (
    carregar,
    status as consulta_status,
    consultar_atendimentos,
    resumo_atendimentos,
    atendimentos_por_dia,
)


@eel.expose
def consulta_listar_atendimentos(data_inicio: str, data_fim: str) -> list[dict]:
    return consultar_atendimentos(data_inicio, data_fim) or []


@eel.expose
def consulta_resumo_atendimentos(data_inicio: str, data_fim: str) -> dict:
    return resumo_atendimentos(data_inicio, data_fim)


@eel.expose
def consulta_atendimentos_por_dia(data_inicio: str, data_fim: str) -> list[dict]:
    return atendimentos_por_dia(data_inicio, data_fim) or []


@eel.expose
def consulta_recarregar() -> str:
    """Recarrega hospital.db na RAM (usado pelo botão de refresh)."""
    return carregar()


@eel.expose
def consulta_status_cache() -> str:
    """Status do cache sem recarregar."""
    return consulta_status()


# =====================================================================
# 7. BACKUP E LOG DE AUDITORIA
# =====================================================================

@eel.expose
def backup_executar(caminho: str, prefixo: str = "manual") -> str:
    """Faz backup manual de um arquivo."""
    destino = fazer_backup(caminho, prefixo)
    if destino:
        log_auditoria("backup_manual", f"{caminho} → {destino}")
        return f"Backup criado: {destino}"
    return f"Erro: arquivo {caminho} nao encontrado."


@eel.expose
def backup_listar(arquivo_original: str = "") -> list[dict]:
    """Lista backups disponíveis."""
    return listar_backups(arquivo_original)


@eel.expose
def auditoria_listar(limite: int = 100) -> list[dict]:
    """Retorna as últimas entradas do log de auditoria."""
    return listar(limite)


# =====================================================================
# 8. EXPORTAÇÃO CONSOLIDADA
# =====================================================================
from analise.exportacao_consolidada import exportar_tudo


@eel.expose
def exportacao_consolidada() -> str:
    """Gera todos os relatórios e empacota em ZIP."""
    log_auditoria("exportacao_consolidada", "iniciada")
    resultado = exportar_tudo()
    log_auditoria("exportacao_consolidada", resultado)
    return resultado


# =====================================================================
# 9. INDICADORES DO PAINEL (HOME)
# =====================================================================
from analise.consulta_recepcao import status as consulta_status


@eel.expose
def dashboard_indicadores() -> dict:
    """Retorna métricas resumidas pra home do painel."""
    qtd_fb = len(BASE_PACIENTES)

    status_db = consulta_status()
    qtd_atendimentos = 0
    if "OK" in status_db:
        try:
            qtd_atendimentos = int(
                status_db.split("atendimentos")[1].split("na")[0].strip()
            )
        except (ValueError, IndexError):
            qtd_atendimentos = 0

    backups = listar_backups()
    total_backups = len(backups)
    ultimo_backup = backups[0]["data"] if backups else "Nunca"

    return {
        "pacientes_firebird_ram": qtd_fb,
        "atendimentos_recepcao_ram": qtd_atendimentos,
        "cache_hospital_db": status_db,
        "total_backups": total_backups,
        "ultimo_backup": ultimo_backup,
    }


# =====================================================================
# INICIAR (usado pelo main.py)
# =====================================================================
def iniciar() -> None:
    logger.info("Servidor HMPCF Iniciado e Persistente na porta 8001")
    carregar_base()
    carregar()
    log_auditoria("painel_iniciado", f"{len(BASE_PACIENTES)} pacientes FB na RAM")

    def manter_vivo(rota, websockets):
        pass

    eel.start(
        'index.html',
        mode='msedge',
        size=(1250, 850),
        host='localhost',
        port=8001,
        block=False,
        close_callback=manter_vivo
    )

    while True:
        eel.sleep(1.0)

# =====================================================================
# PONTO DE ENTRADA (direto)
# =====================================================================
if __name__ == '__main__':
    iniciar()
