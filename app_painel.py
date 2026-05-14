import os
import sys
import subprocess
import glob
import eel

# ==============================================================================
# 📂 CONFIGURAÇÃO DE DIRETÓRIOS E AMBIENTE (FOCO EM WINDOWS)
# ==============================================================================
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_AUTOMACAO = os.path.join(PASTA_ATUAL, "automacao")

# Inicializa o motor Eel apontando para a pasta 'web_painel'
eel.init('web_painel')

# 💡 A NOVA IMPORTAÇÃO: O VS Code entende isso perfeitamente!
from automacao import executor_rpa

# ==============================================================================
# 🩺 MÓDULO TRIAGEM E FATIAMENTO (ENFERMEIROS)
# ==============================================================================

@eel.expose
def rodar_limpador(data_lote, enfermeiros_str):
    """
    Função chamada pelo botão "Reordenar e Dividir Lotes" no painel web.
    1. Executa a limpeza bruta (via cpf_sus.py).
    2. Lê os dados filtrados.
    3. Quebra os pacientes em lotes de 99.
    4. Adiciona cabeçalhos (PROFISSIONAL: | DATA:) num formato de rodízio.
    """
    # 1. Corre a limpeza executando o script cpf_sus.py (que gera o pacientes.txt)
    subprocess.run([sys.executable, "cpf_sus.py"], cwd=PASTA_AUTOMACAO)
    
    # Prepara para ler o resultado gerado
    caminho_pacientes = os.path.join(PASTA_AUTOMACAO, "pacientes.txt")
    if not os.path.exists(caminho_pacientes): 
        return "Erro: pacientes.txt não encontrado. Verifique se colou os dados."
    
    # Lê os pacientes limpos e exclui linhas em branco
    with open(caminho_pacientes, 'r', encoding='utf-8') as f:
        docs = [l.strip() for l in f if l.strip()]
        
    # Prepara a lista de enfermeiros, convertendo para maiúsculo
    profs = [p.strip().upper() for p in enfermeiros_str.split(',') if p.strip()]
    if not profs: profs = ["PROFISSIONAL SEM NOME"]
    
    resultado_final = []
    chunk_size = 99
    idx_p = 0
    
    # 2. Fatiamento em blocos de 99 e criação dos cabeçalhos
    for i in range(0, len(docs), chunk_size):
        chunk = docs[i:i+chunk_size]
        prof_atual = profs[idx_p % len(profs)] # Alterna entre os enfermeiros da lista
        idx_p += 1
        
        # Formato exato que o método split("|") espera ler no robô (executor_rpa.py)
        resultado_final.append(f"PROFISSIONAL: {prof_atual} | DATA: {data_lote}")
        resultado_final.extend(chunk)
        resultado_final.append("") # Adiciona uma linha vazia entre lotes para organização visual
        
    # Salva o resultado final fatiado no arquivo padrão da automação
    conteudo_str = "\n".join(resultado_final)
    with open(os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt"), 'w', encoding='utf-8') as f:
        f.write(conteudo_str)
    
    return conteudo_str

# ==============================================================================
# 🤖 FUNÇÕES GERAIS DE COMUNICAÇÃO WEB <-> PYTHON
# ==============================================================================

@eel.expose
def listar_producoes():
    """Lista todos os arquivos .txt na pasta de automação e retorna para o menu drop-down web"""
    arquivos = glob.glob(os.path.join(PASTA_AUTOMACAO, "*.txt"))
    nomes = [os.path.basename(a) for a in arquivos]
    nomes.sort(reverse=True)
    return nomes

@eel.expose
def ler_producao(nome_arquivo):
    """Retorna o texto de um arquivo selecionado para a interface web ler (área de texto do robô)"""
    caminho = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    if not os.path.exists(caminho): return ""
    with open(caminho, 'r', encoding='utf-8') as f: 
        return f.read()

@eel.expose
def preparar_rpa(nome_arquivo):
    """Pede ao executor_rpa para carregar os lotes e validar o TXT selecionado contra o GDB"""
    caminho_completo = os.path.join(PASTA_AUTOMACAO, nome_arquivo)
    if os.path.exists(caminho_completo):
        lotes, erro = executor_rpa.preparar_lotes(caminho_completo)
        return {"lotes": lotes, "erro": erro}
    return {"lotes": [], "erro": "Ficheiro não encontrado."}

@eel.expose
def digitar_lote_rpa(medico, data, cargo, pacientes):
    """Aciona a função de digitação física (PyAutoGUI) do robô e gerencia o status via callback"""
    def callback(msg): 
        eel.atualizar_progresso_web(msg)() # Envia a mensagem de progresso de volta para o JavaScript
    executor_rpa.executar_pyautogui(medico, data, cargo, pacientes, callback)
    return "OK"

@eel.expose
def ler_txt_pacientes():
    """Lê o arquivo final gerado pela triagem dos enfermeiros e o joga na tela"""
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    if not os.path.exists(caminho): return ""
    with open(caminho, 'r', encoding='utf-8') as f: 
        return f.read()

@eel.expose
def salvar_txt_pacientes(conteudo):
    """Salva uma edição manual que o usuário tenha feito na área de texto final da Triagem"""
    caminho = os.path.join(PASTA_AUTOMACAO, "prod_enfermeiros.txt")
    with open(caminho, 'w', encoding='utf-8') as f: 
        f.write(conteudo)
    return "✅ Salvo!"

@eel.expose
def salvar_texto_sujo(conteudo):
    """Salva o texto copiado (rascunho cru) pelo usuário no arquivo cpf_sus.txt para ser limpo"""
    caminho = os.path.join(PASTA_AUTOMACAO, "cpf_sus.txt")
    with open(caminho, 'w', encoding='utf-8') as f: 
        f.write(conteudo)

@eel.expose
def registrar_cabecalho_digitacao(arquivo, medico, data):
    """Grava o nome e a data formatados (cabeçalho) durante a digitação de novos pacientes manuais"""
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    with open(caminho, 'a', encoding='utf-8') as f:
        f.write(f"PROFISSIONAL: {medico.upper()} | DATA: {data}\n")
    return True

@eel.expose
def adicionar_paciente_txt(arquivo, documento):
    """Adiciona um documento pesquisado e clicado no módulo web de digitação ao arquivo do dia"""
    caminho = os.path.join(PASTA_AUTOMACAO, arquivo)
    try:
        with open(caminho, 'a', encoding='utf-8') as f: 
            f.write(f"{documento}\n")
        return True
    except: 
        return False

@eel.expose
def buscar_pacientes_fb(termo):
    """Faz a busca em tempo real de pacientes pelo nome, CPF ou SUS via Eel conectado ao Firebird"""
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
            # Formatações para a interface web ficar bonita (datas e espaços)
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
    print("🚀 Sistema HMPCF - Painel de Automação Iniciado (100% Eel)")
    # Inicia a janela do navegador chamando a página inicial index.html no formato de aplicativo
    eel.start('index.html', mode='msedge', size=(), port=8001)