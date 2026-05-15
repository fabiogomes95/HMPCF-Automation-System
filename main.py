"""
MAIN.PY — Launcher Unificado HMPCF + Auto-Update
==================================================
Gerencia a inicialização de todos os servidores, verifica
atualizações no GitHub e permite build com PyInstaller.

Uso:
    python main.py              # Inicia normalmente
    python main.py --no-update  # Pula verificação de update
    python main.py --build      # Apenas verifica se PyInstaller está pronto

Para gerar .exe:
    pip install pyinstaller
    python -m PyInstaller main.spec
"""

import os
import sys
import json
import time
import threading
import webbrowser
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from logging_setup import logger

# ──────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ──────────────────────────────────────────────────────────────────────
PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
VERSAO_LOCAL = "1.1.0"
REPO = "fabiogomes95/HMPCF-Automation-System"
BRANCH = "main"
URL_VERSION = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/version.json"
URL_DOWNLOAD_ZIP = f"https://github.com/{REPO}/archive/refs/heads/{BRANCH}.zip"

# ──────────────────────────────────────────────────────────────────────
# CORES NO TERMINAL
# ──────────────────────────────────────────────────────────────────────
class Cores:
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    AZUL = '\033[94m'
    RESET = '\033[0m'
    NEGRITO = '\033[1m'

def info(msg):    logger.info(f"{Cores.AZUL}[INFO]{Cores.RESET} {msg}")
def sucesso(msg): logger.info(f"{Cores.VERDE}[OK]{Cores.RESET} {msg}")
def aviso(msg):   logger.warning(f"{Cores.AMARELO}[!]{Cores.RESET} {msg}")
def erro(msg):    logger.error(f"{Cores.VERMELHO}[ERRO]{Cores.RESET} {msg}")

# ──────────────────────────────────────────────────────────────────────
# 1. VERIFICADOR DE VERSÃO (Auto-Update)
# ──────────────────────────────────────────────────────────────────────
def get_versao_local():
    """Lê a versão do version.json local."""
    caminho = os.path.join(PASTA_RAIZ, 'version.json')
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f).get('version', VERSAO_LOCAL)
    except Exception:
        return VERSAO_LOCAL

def get_versao_remota():
    """Busca version.json no GitHub e retorna a versão remota."""
    try:
        req = urllib.request.Request(URL_VERSION, headers={
            'User-Agent': 'HMPCF-Automation-System'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            dados = json.loads(resp.read().decode('utf-8'))
            return dados.get('version', None)
    except Exception as e:
        return None

def tem_git_instalado():
    """Verifica se o Git está disponível no PATH."""
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        return True
    except Exception:
        return False

def fazer_update_git_pull():
    """Executa git pull para atualizar o repositório."""
    info("Atualizando via git pull...")
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd=PASTA_RAIZ,
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            sucesso(f"Atualização concluída!\n{result.stdout}")
            return True
        else:
            erro(f"Falha no git pull:\n{result.stderr}")
            return False
    except Exception as e:
        erro(f"Erro ao executar git pull: {e}")
        return False

def fazer_update_zip():
    """Download do ZIP e extração manual (fallback sem Git)."""
    import zipfile
    import io
    import shutil

    aviso("Git não encontrado. Baixando ZIP do repositório...")
    try:
        req = urllib.request.Request(URL_DOWNLOAD_ZIP, headers={
            'User-Agent': 'HMPCF-Automation-System'
        })
        with urllib.request.urlopen(req, timeout=120) as resp:
            dados_zip = resp.read()

        with zipfile.ZipFile(io.BytesIO(dados_zip)) as zf:
            # A pasta dentro do ZIP tem formato: HMPCF-Automation-System-main/
            prefixo = f"HMPCF-Automation-System-{BRANCH}/"
            temp_dir = os.path.join(PASTA_RAIZ, '.update_temp')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            for member in zf.namelist():
                if member.startswith(prefixo):
                    rel_path = member[len(prefixo):]
                    if not rel_path:
                        continue
                    dest = os.path.join(temp_dir, rel_path)
                    if member.endswith('/'):
                        os.makedirs(dest, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with open(dest, 'wb') as f:
                            f.write(zf.read(member))

            # Substitui arquivos (exceto hospital.db que é local)
            excluir = {'hospital.db', 'credentials.json', '.update_temp'}
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file in excluir:
                        continue
                    src = os.path.join(root, file)
                    rel = os.path.relpath(src, temp_dir)
                    dst = os.path.join(PASTA_RAIZ, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

            shutil.rmtree(temp_dir)

        sucesso("Atualização via ZIP concluída!")
        return True

    except Exception as e:
        erro(f"Falha na atualização via ZIP: {e}")
        return False

def verificar_atualizacao():
    """
    Verifica se há versão nova no GitHub.
    Retorna True se atualizou, False se já está atualizado.
    """
    logger.info(f"\n{Cores.NEGRITO}═" * 50)
    logger.info(f"  HMPCF — VERIFICADOR DE ATUALIZAÇÕES")
    logger.info(f"═" * 50 + f"{Cores.RESET}")

    local = get_versao_local()
    remota = get_versao_remota()

    info(f"Versão local:  {Cores.NEGRITO}{local}{Cores.RESET}")

    if remota is None:
        aviso("Não foi possível verificar atualizações (sem internet?).")
        aviso("Continuando com a versão local.")
        return False

    info(f"Versão remota: {Cores.NEGRITO}{remota}{Cores.RESET}")

    try:
        partes_local = [int(x) for x in local.split('.')]
        partes_remota = [int(x) for x in remota.split('.')]

        # Normaliza tamanhos (ex: 1.0 vs 1.0.0)
        while len(partes_local) < 3: partes_local.append(0)
        while len(partes_remota) < 3: partes_remota.append(0)

        if tuple(partes_remota) > tuple(partes_local):
            aviso(f"Nova versão disponível: {remota}")

            resposta = input(f"{Cores.AMARELO}Deseja atualizar? (S/N): {Cores.RESET}").strip().upper()

            if resposta != 'S':
                aviso("Atualização cancelada pelo usuário.")
                return False

            if tem_git_instalado():
                ok = fazer_update_git_pull()
            else:
                ok = fazer_update_zip()

            if ok:
                sucesso("Reinicie o programa para usar a nova versão!")
                input(f"\n{Cores.VERDE}Pressione ENTER para sair...{Cores.RESET}")
                sys.exit(0)
            else:
                erro("Falha na atualização. Continuando com versão local.")
                return False
        else:
            sucesso("Sistema já está atualizado!")
            return False
    except (ValueError, TypeError):
        aviso(f"Formato de versão incomparável. Local={local}, Remota={remota}")
        return False

# ──────────────────────────────────────────────────────────────────────
# 2. LANÇADOR DOS SERVIDORES
# ──────────────────────────────────────────────────────────────────────
def servidor_recepcao():
    """Inicia o servidor da Recepção (porta 8000)."""
    try:
        sys.path.insert(0, PASTA_RAIZ)
        import app_recepcao
        app_recepcao.iniciar()
    except Exception as e:
        erro(f"Falha ao iniciar Recepção: {e}")

def servidor_painel():
    """Inicia o servidor do Painel de Gestão (porta 8001)."""
    try:
        sys.path.insert(0, PASTA_RAIZ)
        import app_painel
        app_painel.iniciar()
    except Exception as e:
        erro(f"Falha ao iniciar Painel: {e}")

# ──────────────────────────────────────────────────────────────────────
# 3. MODO SERVIÇO (Threads)
# ──────────────────────────────────────────────────────────────────────
def modo_servico():
    """
    Modo produção: sobe ambos os servidores em threads separadas.
    Como o Eel usa block=False no app_painel, conseguimos rodar ambos.
    """
    logger.info(f"\n{Cores.NEGRITO}═" * 50)
    logger.info(f"  HMPCF — INICIANDO SERVIDORES")
    logger.info(f"═" * 50 + f"{Cores.RESET}")

    # Pré-configura o app_painel (block=False) e importa antecipadamente
    os.chdir(PASTA_RAIZ)

    # Thread da Recepção
    t_recepcao = threading.Thread(target=servidor_recepcao, daemon=True)
    t_recepcao.start()
    info("Servidor da Recepção iniciado (porta 8000)")

    # Pequena pausa para a recepção subir
    time.sleep(0.5)

    # Thread do Painel
    t_painel = threading.Thread(target=servidor_painel, daemon=True)
    t_painel.start()
    info("Servidor do Painel iniciado (porta 8001)")

    # Abre o navegador
    time.sleep(2)
    webbrowser.open('http://localhost:8000')

    logger.info(f"{Cores.VERDE}{Cores.NEGRITO}✓ Sistema HMPCF operacional!{Cores.RESET}")
    logger.info(f"  Recepção: http://localhost:8000")
    logger.info(f"  Painel:   http://localhost:8001")
    logger.warning(f"Pressione CTRL+C para parar todos os servidores.{Cores.RESET}")

    # Mantém o main vivo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.warning(f"Servidores encerrados pelo usuário.{Cores.RESET}")
        sys.exit(0)

# ──────────────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logger.info(f"""{Cores.AZUL}{Cores.NEGRITO}
    ╔══════════════════════════════════════════╗
    ║   HMPCF - AUTOMAÇÃO HOSPITALAR v{VERSAO_LOCAL.ljust(6)}║
    ║   Hospital Municipal Pres. Café Filho   ║
    ╚══════════════════════════════════════════╝{Cores.RESET}
    """)

    args = sys.argv[1:]

    # Flag --no-update pula a verificação
    if '--no-update' not in args:
        verificar_atualizacao()
    else:
        info("Modo --no-update: pulando verificação de atualização.")

    # Flag --build apenas testa ambiente
    if '--build' in args:
        logger.info(f"Verificando ambiente para build...{Cores.RESET}")
        try:
            import PyInstaller
            sucesso(f"PyInstaller disponível ({PyInstaller.__version__})")
        except ImportError:
            erro("PyInstaller não instalado. Execute: pip install pyinstaller")
        sys.exit(0)

    # Inicia o sistema
    modo_servico()
