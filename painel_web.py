import os
import sys
import subprocess
import threading
import glob

# ==============================================================================
# HACK DE COMPATIBILIDADE PARA LINUX (CORRIGE O NameError: _root_path)
# ==============================================================================
import eel
import eel.__init__ as eel_mod

# Forçamos a definição das variáveis que o Eel está perdendo no escopo no Linux
BASE_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
setattr(eel_mod, '_root_path', BASE_WEB)
setattr(eel_mod, 'root_path', BASE_WEB)
# ==============================================================================

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_AUTOMACAO = os.path.join(PASTA_ATUAL, "automacao")
sys.path.append(PASTA_AUTOMACAO)

# Tenta importar o robô protegendo contra o erro de Display do Linux (Wayland)
try:
    import executor_rpa
    import tkinter as tk
    from tkinter import filedialog
    robo_disponivel = True
    print("✅ Motor de automação carregado com sucesso.")
except Exception as e:
    executor_rpa = None
    robo_disponivel = False
    print(f"⚠️ Modo Casa: Automação desativada (Sem tela X11/BPA). Erro: {e}")

# Garante que o eel use a pasta correta
eel.init('web')

# ==============================================================================
# FUNÇÕES EXPOSTAS AO NAVEGADOR (LIMPEZA, TRIAGEM E ROBÔ)
# ==============================================================================

@eel.expose
def escolher_arquivo():
    if not robo_disponivel: return ""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    caminho = filedialog.askopenfilename(initialdir=PASTA_AUTOMACAO, filetypes=[("TXT", "*.txt")])
    root.destroy()
    return os.path.basename(caminho)

@eel.expose
def listar_producoes():
    arquivos = glob.glob(os.path.join(PASTA_AUTOMACAO, "*.txt"))
    nomes = [os.path.basename(a) for a in arquivos]
    nomes.sort(reverse=True)
    return nomes

@eel.expose
def ler_producao(nome_arquivo):
    caminho = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    if not os.path.exists(caminho): return ""
    with open(caminho, 'r', encoding='utf-8') as f: return f.read()

@eel.expose
def ler_txt_pacientes():
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    if not os.path.exists(caminho): return ""
    with open(caminho, 'r', encoding='utf-8') as f: return f.read()

@eel.expose
def salvar_txt_pacientes(conteudo):
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    with open(caminho, 'w', encoding='utf-8') as f: f.write(conteudo)
    return "✅ Salvo!"

@eel.expose
def salvar_texto_sujo(conteudo):
    caminho = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    with open(caminho, 'w', encoding='utf-8') as f: f.write(conteudo)

@eel.expose
def rodar_limpador(data_lote, enfermeiros_str):
    """Roda o cpf_sus.py, fatiando de 99 em 99 e distribuindo entre os enfermeiros."""
    # 1. Roda o script de limpeza base
    subprocess.run([sys.executable, "cpf_sus.py"], cwd=PASTA_AUTOMACAO)
    
    # 2. Lê os documentos limpos (gerados no pacientes.txt pelo cpf_sus.py)
    caminho_pacientes = os.path.join(PASTA_AUTOMACAO, "pacientes.txt")
    if not os.path.exists(caminho_pacientes):
        return "Erro: Nenhum paciente processado."
        
    with open(caminho_pacientes, 'r', encoding='utf-8') as f:
        docs = [linha.strip() for linha in f if linha.strip()]
        
    # 3. Organiza a lista de enfermeiros
    lista_enfs = [e.strip().upper() for e in enfermeiros_str.split(',') if e.strip()]
    if not lista_enfs:
        lista_enfs = ["ENFERMEIRO PADRAO"]
        
    resultado_final = []
    chunk_size = 99
    enf_index = 0
    
    # 4. Fatiamento por 99 pacientes
    for i in range(0, len(docs), chunk_size):
        chunk = docs[i:i+chunk_size]
        enf_atual = lista_enfs[enf_index % len(lista_enfs)] # Pega o enfermeiro em rodízio
        enf_index += 1
        
        resultado_final.append(f"\nMEDICO: {enf_atual}")
        resultado_final.append(f"DATA: {data_lote}")
        resultado_final.extend(chunk)
        
    # 5. Salva o arquivo prod_enfermeiros.txt padronizado
    conteudo_final = "\n".join(resultado_final) + "\n"
    caminho_prod = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    with open(caminho_prod, 'w', encoding='utf-8') as f:
        f.write(conteudo_final)
        
    return conteudo_final

@eel.expose
def preparar_rpa(nome_arquivo):
    if not robo_disponivel:
        print(f"🏠 Simulando abertura do lote: {nome_arquivo}")
        return {"lotes": [], "erro": "", "modo_casa": True}
    caminho_completo = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    lotes, erro = executor_rpa.preparar_lotes(caminho_completo)
    return {"lotes": lotes, "erro": erro}

@eel.expose
def digitar_lote_rpa(medico, data, cargo, pacientes):
    if robo_disponivel:
        def callback(mensagem): eel.atualizar_progresso_web(mensagem)()
        executor_rpa.executar_pyautogui(medico, data, cargo, pacientes, callback)
        return "OK"
    else:
        print(f"🤖 SIMULAÇÃO RPA: Digitando {len(pacientes)} pacientes de {medico}...")
        return "OK"

# ==============================================================================
# FUNÇÕES DO ASSISTENTE DE DIGITAÇÃO DIRETA (FIREBIRD)
# ==============================================================================

@eel.expose
def registrar_cabecalho_digitacao(arquivo, medico, data):
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    with open(caminho, 'a', encoding='utf-8') as f:
        f.write(f"\nMEDICO: {medico.upper()}\n")
        f.write(f"DATA: {data}\n")
    return True

@eel.expose
def adicionar_paciente_txt(arquivo, documento):
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    try:
        with open(caminho, 'a', encoding='utf-8') as f:
            f.write(f"{documento}\n")
        return True
    except:
        return False

@eel.expose
def buscar_pacientes_fb(termo):
    if not termo: return []
    termo = termo.upper().strip()
    caminho_gdb = r'C:/BPA/BPAMAG.GDB'
    try:
        import firebirdsql
        con = firebirdsql.connect(host='localhost', database=caminho_gdb, user='SYSDBA', password='masterkey', charset='WIN1252')
        cur = con.cursor()
        query = "SELECT CNS, NOME, DTNASC, NUM_CPF FROM CADCNS WHERE NOME LIKE ? OR NUM_CPF LIKE ? OR CNS LIKE ?"
        param = f"%{termo}%"
        cur.execute(query, (param, param, param))
        rows = cur.fetchall()
        res = []
        for r in rows:
            dn_raw = str(r[2] or "").strip()
            res.append({
                'sus': str(r[0] or "").strip(),
                'nome': str(r[1] or "").strip().upper(),
                'dtnasc': f"{dn_raw[6:8]}/{dn_raw[4:6]}/{dn_raw[0:4]}" if len(dn_raw) == 8 else "  /  /    ",
                'cpf': str(r[3] or "").strip()
            })
        con.close()
        return sorted(res, key=lambda x: x['nome'])[:50]
    except Exception as e:
        print(f"Fallback banco (MOCK DATA). Erro real: {e}")
        return [
            {'nome': 'FÁBIO GOMES DA SILVA', 'sus': '707802947623117', 'cpf': '13797250460', 'dtnasc': '10/05/1995'},
            {'nome': 'MARIA JOSE DA CONCEICAO', 'sus': '708702106402299', 'cpf': '07307009412', 'dtnasc': '01/01/1990'},
            {'nome': f'PACIENTE TESTE BPA ({termo})', 'sus': '706702534700518', 'cpf': '', 'dtnasc': '12/12/1980'}
        ]

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    print("🚀 Iniciando HMPCF Gestão Digital 3.0...")
    eel.start('index.html')