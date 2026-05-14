import os
import glob
import eel

# ==============================================================================
# 📂 CONFIGURAÇÃO DE DIRETÓRIOS E AMBIENTE (FOCO EM WINDOWS)
# ==============================================================================
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_AUTOMACAO = os.path.join(PASTA_ATUAL, "automacao")

eel.init('web_painel')

# 💡 AS IMPORTAÇÕES: Trazemos o robô e o limpador direto pra memória!
from automacao import executor_rpa
from automacao import cpf_sus 

# ==============================================================================
# 🩺 MÓDULO TRIAGEM E FATIAMENTO (ENFERMEIROS)
# ==============================================================================

@eel.expose
def rodar_limpador(data_lote, enfermeiros_str):
    """
    Função chamada pelo botão "Reordenar e Dividir Lotes" no painel web.
    1. Executa a limpeza bruta puxando a função do cpf_sus.py.
    2. Lê os dados filtrados diretamente da memória.
    3. Quebra os pacientes em lotes de 99.
    4. Adiciona cabeçalhos e cria apenas o prod_enfermeiros.txt.
    """
    
    # Define onde está o rascunho sujo colado pelas meninas
    caminho_sujo = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    
    # 1. Manda o cpf_sus limpar e pegar os dados direto na memória (Adeus pacientes.txt!)
    docs = cpf_sus.processar_lista(caminho_sujo)
    
    if not docs: 
        return "Erro: Nenhum paciente válido encontrado. Verifique se os dados estão corretos."
        
    # Prepara a lista de enfermeiros
    profs = [p.strip().upper() for p in enfermeiros_str.split(',') if p.strip()]
    if not profs: profs = ["PROFISSIONAL SEM NOME"]
    
    resultado_final = []
    chunk_size = 99
    idx_p = 0
    
    # 2. Fatiamento em blocos de 99 e criação dos cabeçalhos pro Robô
    for i in range(0, len(docs), chunk_size):
        chunk = docs[i:i+chunk_size]
        prof_atual = profs[idx_p % len(profs)] # Roda o plantão dos enfermeiros
        idx_p += 1
        
        # O cabeçalho sagrado que o seu robô exige:
        resultado_final.append(f"PROFISSIONAL: {prof_atual} | DATA: {data_lote}")
        resultado_final.extend(chunk)
        resultado_final.append("") # Linha vazia entre lotes
        
    # 3. Salva TUDO direto no prod_enfermeiros.txt
    conteudo_str = "\n".join(resultado_final)
    caminho_prod = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    
    with open(caminho_prod, 'w', encoding='utf-8') as f:
        f.write(conteudo_str)
    
    # Retorna o texto formatado para mostrar na tela do painel
    return conteudo_str

# ==============================================================================
# 🤖 FUNÇÕES GERAIS DE COMUNICAÇÃO WEB <-> PYTHON
# ==============================================================================

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
    with open(caminho, 'r', encoding='utf-8') as f: 
        return f.read()

@eel.expose
def preparar_rpa(nome_arquivo):
    caminho_completo = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    if os.path.exists(caminho_completo):
        lotes, erro = executor_rpa.preparar_lotes(caminho_completo)
        return {"lotes": lotes, "erro": erro}
    return {"lotes": [], "erro": "Ficheiro não encontrado."}

@eel.expose
def digitar_lote_rpa(medico, data, cargo, pacientes):
    def callback(msg): 
        eel.atualizar_progresso_web(msg)()
    executor_rpa.executar_pyautogui(medico, data, cargo, pacientes, callback)
    return "OK"

@eel.expose
def ler_txt_pacientes():
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    if not os.path.exists(caminho): return ""
    with open(caminho, 'r', encoding='utf-8') as f: 
        return f.read()

@eel.expose
def salvar_txt_pacientes(conteudo):
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    with open(caminho, 'w', encoding='utf-8') as f: 
        f.write(conteudo)
    return "✅ Salvo!"

@eel.expose
def salvar_texto_sujo(conteudo):
    caminho = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    with open(caminho, 'w', encoding='utf-8') as f: 
        f.write(conteudo)

@eel.expose
def registrar_cabecalho_digitacao(arquivo, medico, data):
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    with open(caminho, 'a', encoding='utf-8') as f:
        f.write(f"PROFISSIONAL: {medico.upper()} | DATA: {data}\n")
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
        sql = "SELECT CNS, NOME, DTNASC, NUM_CPF FROM CADCNS WHERE NOME LIKE ? OR NUM_CPF LIKE ? OR CNS LIKE ?"
        cur.execute(sql, (f"%{termo}%", f"%{termo}%", f"%{termo}%"))
        res = []
        for r in cur.fetchall():
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
        print(f"Erro na busca do banco: {e}")
        return []

# ==============================================================================
# 🚀 INICIALIZAÇÃO DO APLICATIVO
# ==============================================================================
if __name__ == '__main__':
    print("🚀 Sistema HMPCF - Painel de Automação Iniciado (Sem arquivos lixo!)")
    eel.start('index.html', mode='msedge', size=(), port=8001)