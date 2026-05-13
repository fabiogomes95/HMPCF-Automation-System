import eel
import os
import subprocess
import threading
import glob
import sys
import tkinter as tk
from tkinter import filedialog

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_AUTOMACAO = os.path.join(PASTA_ATUAL, "automacao")

sys.path.append(PASTA_AUTOMACAO)
import executor_rpa

eel.init('web')

# --- FUNÇÕES EXPOSTAS AO NAVEGADOR ---

@eel.expose
def escolher_arquivo():
    """Abre o seletor do Windows para o Fábio escolher a produção"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    caminho = filedialog.askopenfilename(initialdir=PASTA_AUTOMACAO, filetypes=[("TXT", "*.txt")])
    root.destroy()
    return caminho

@eel.expose
def listar_producoes():
    """Lista todos os arquivos .txt para o menu suspenso"""
    arquivos = glob.glob(os.path.join(PASTA_AUTOMACAO, "*.txt"))
    nomes = [os.path.basename(a) for a in arquivos]
    nomes.sort(reverse=True)
    return nomes

@eel.expose
def ler_producao(nome_arquivo):
    """Exibe o conteúdo no painel esquerdo"""
    caminho = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    with open(caminho, 'r', encoding='utf-8') as f: return f.read()

@eel.expose
def ler_csv():
    """Exibe o pacientes.csv no painel direito"""
    caminho = os.path.join(PASTA_AUTOMACAO, "pacientes.csv")
    if not os.path.exists(caminho): return ""
    with open(caminho, 'r', encoding='utf-8') as f: return f.read()

@eel.expose
def salvar_csv(conteudo):
    """Salva edições no pacientes.csv"""
    caminho = os.path.join(PASTA_AUTOMACAO, "pacientes.csv")
    with open(caminho, 'w', encoding='utf-8') as f: f.write(conteudo)
    return "✅ Salvo!"

@eel.expose
def salvar_texto_sujo(conteudo):
    """Salva rascunho no cpf_sus.txt"""
    caminho = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    with open(caminho, 'w', encoding='utf-8') as f: f.write(conteudo)

@eel.expose
def rodar_limpador():
    """Roda o cpf_sus.py para organizar os dados"""
    subprocess.run(["python", "cpf_sus.py"], cwd=PASTA_AUTOMACAO)
    return ler_csv()

@eel.expose
def preparar_rpa(caminho):
    """Pede ao robô para validar os dados - CORRIGIDO PARA 'preparar_lotes'"""
    lotes, erro = executor_rpa.preparar_lotes(caminho)
    return {"lotes": lotes, "erro": erro}

@eel.expose
def digitar_lote_rpa(medico, data, proc, pacs):
    """Inicia a digitação e envia progresso para o HTML"""
    def callback(mensagem):
        eel.atualizar_progresso_web(mensagem)()
    
    executor_rpa.executar_pyautogui(medico, data, proc, pacs, callback)
    return "OK"

if __name__ == '__main__':
    # Inicia no Edge modo App
    eel.start('index.html', size=(1250, 800), mode='msedge')