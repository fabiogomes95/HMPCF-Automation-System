import os
import glob
import eel
import firebirdsql

# ==============================================================================
# 📂 CONFIGURAÇÃO DE DIRETÓRIOS E AMBIENTE
# ==============================================================================
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_AUTOMACAO = os.path.join(PASTA_ATUAL, "automacao")

eel.init('web_painel')

# 💡 AS IMPORTAÇÕES: Trazendo nossos "trabalhadores" isolados
from automacao import executor_rpa
from automacao import cpf_sus 
from automacao import digitacao 

# ==============================================================================
# 🧠 MOTOR DE RAM: CARREGAMENTO DE BASE DO HOSPITAL
# ==============================================================================
BASE_PACIENTES = []

def carregar_base():
    """Carrega TODOS os pacientes para a memória RAM assim que o sistema abre."""
    global BASE_PACIENTES
    caminho_gdb = r'C:/BPA/BPAMAG.GDB'
    try:
        print("⏳ Carregando pacientes para a memória...")
        con = firebirdsql.connect(host='localhost', database=caminho_gdb, user='SYSDBA', password='masterkey', charset='WIN1252')
        cur = con.cursor()
        cur.execute("SELECT CNS, NOME, DTNASC, NUM_CPF FROM CADCNS")
        for r in cur.fetchall():
            sus = str(r[0] or "").strip()
            nome = str(r[1] or "").strip().upper()
            dn_raw = str(r[2] or "").strip()
            cpf = str(r[3] or "").strip()
            
            dtnasc = f"{dn_raw[6:8]}/{dn_raw[4:6]}/{dn_raw[0:4]}" if len(dn_raw) == 8 else "  /  /    "
            
            BASE_PACIENTES.append({
                'sus': sus, 'nome': nome, 'dtnasc': dtnasc, 'cpf': cpf
            })
        con.close()
        print(f"⚡ SUCESSO! {len(BASE_PACIENTES)} pacientes na RAM. Busca ultrarrápida ativada!")
    except Exception as e:
        print(f"❌ Erro Crítico ao carregar base: {e}")

# ==============================================================================
# 🔍 1. MÓDULO DIGITADOR MANUAL (Delega para o digitacao.py)
# ==============================================================================

@eel.expose
def buscar_pacientes_fb(termo):
    # Envia a pesquisa e a base de dados em RAM para o arquivo resolver
    return digitacao.buscar_pacientes_memoria(termo, BASE_PACIENTES)

@eel.expose
def registrar_cabecalho_digitacao(arquivo, medico, data):
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    return digitacao.criar_cabecalho_producao(caminho, medico, data)

@eel.expose
def adicionar_paciente_txt(arquivo, documento):
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    return digitacao.adicionar_ficha_producao(caminho, documento)

# ==============================================================================
# 🧹 2. MÓDULO TRIAGEM E LIMPEZA (Delega para o cpf_sus.py)
# ==============================================================================

@eel.expose
def rodar_limpador(data_lote, enfermeiros_str):
    caminho_sujo = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    
    docs = cpf_sus.processar_lista(caminho_sujo)
    if not docs: return "Erro: Nenhum paciente válido encontrado."
        
    profs = [p.strip().upper() for p in enfermeiros_str.split(',') if p.strip()]
    if not profs: profs = ["PROFISSIONAL SEM NOME"]
    
    resultado_final = []
    chunk_size = 99
    idx_p = 0
    
    for i in range(0, len(docs), chunk_size):
        chunk = docs[i:i+chunk_size]
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
def salvar_texto_sujo(conteudo):
    caminho = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    with open(caminho, 'w', encoding='utf-8') as f: 
        f.write(conteudo)

# ==============================================================================
# 🤖 3. MÓDULO ROBÔ RPA E ARQUIVOS (Delega para o executor_rpa.py)
# ==============================================================================

@eel.expose
def preparar_rpa(nome_arquivo):
    caminho_completo = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    if os.path.exists(caminho_completo):
        # ⚠️ AQUI ESTÁ A CORREÇÃO: Enviamos a memória RAM inteira pro Robô não travar!
        lotes, erro = executor_rpa.preparar_lotes(caminho_completo, BASE_PACIENTES)
        return {"lotes": lotes, "erro": erro}
    return {"lotes": [], "erro": "Ficheiro não encontrado."}

@eel.expose
def digitar_lote_rpa(medico, data, cargo, pacientes):
    def callback(msg): eel.atualizar_progresso_web(msg)()
    executor_rpa.executar_pyautogui(medico, data, cargo, pacientes, callback)
    return "OK"

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
    return ler_producao("prod_enfermeiros.txt")

@eel.expose
def salvar_txt_pacientes(conteudo):
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    with open(caminho, 'w', encoding='utf-8') as f: f.write(conteudo)
    return "✅ Salvo!"

# ==============================================================================
# 🚀 LIGAÇÃO DO APLICATIVO
# ==============================================================================
# No final do seu app_painel.py
# ==============================================================================
# 🚀 LIGAÇÃO DO APLICATIVO
# ==============================================================================
if __name__ == '__main__':
    print("🚀 Servidor HMPCF Iniciado e Persistente na porta 8001")
    carregar_base()
    
    # 1. Crie esta função minúscula para anular a "autodestruição" do Eel
    def manter_vivo(rota, websockets):
        pass 

    # 2. Adicione o 'close_callback=manter_vivo' no seu eel.start
    eel.start('index.html', mode=None, host='localhost', port=8001, block=False, close_callback=manter_vivo)

    while True:
        eel.sleep(1.0)