# =========================================================================
# SISTEMA DE BOLETIM DE ATENDIMENTO - HOSPITAL CAFÉ FILHO
# Arquivo Servidor (Backend) - Versão Final Otimizada e Formatada
# =========================================================================

# --- IMPORTAÇÃO DE BIBLIOTECAS (As ferramentas que o Python vai usar) ---
import os           # Para lidar com caminhos de arquivos e pastas no sistema operacional
import sqlite3      # O banco de dados local, leve e embutido no Python
import gspread      # A biblioteca mágica que conecta o Python ao Google Sheets
import threading    # Permite rodar tarefas em segundo plano (como o nosso "Gari da Nuvem")
import time         # Usado para criar pausas (ex: esperar 2 segundos antes de tentar de novo)
from datetime import datetime # Para pegar a data e hora exatas do sistema
from google.oauth2.service_account import Credentials # Para fazer o login seguro na API do Google
from flask import Flask, render_template, request, jsonify # Flask é o motor do nosso servidor web local

# --- Importando suas ferramentas personalizadas do arquivo utils.py ---
# Isso evita que o código fique gigante e repetitivo.
from utils import apenas_numeros, remove_accents

# Força o Python a rodar o script sempre na mesma pasta onde este arquivo (app.py) está salvo.
# Isso evita erros de "arquivo não encontrado" quando o sistema tenta achar o banco de dados.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Cria o aplicativo web (nosso servidor local)
app = Flask(__name__)
# Define o nome do arquivo do banco de dados local
DB_NAME = 'hospital.db'

# =========================================================================
# ☁️ CONFIGURAÇÕES DO GOOGLE SHEETS
# =========================================================================
# Define que nosso programa tem permissão para ler/editar planilhas e acessar o Google Drive
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Seu ID fixo da planilha do Google. Usar o ID impede que o sistema quebre 
# caso alguém renomeie o arquivo "DADOS BPA" lá no Google Drive.
ID_PLANILHA = "1xw_x-bYlHCHzMe39g1mJKPFAD_IcXA8BB0uRfmmuR90"


# =========================================================================
# ⚙️ FUNÇÃO 1: O PREPARADOR DO BANCO DE DADOS LOCAL
# =========================================================================
def init_db():
    # Abre a conexão com o banco de dados (se o arquivo não existir, ele cria na hora)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Cria a tabela 'pacientes' caso ela ainda não exista. 
    # O 'cpf' é a chave primária, ou seja, não podem existir dois pacientes com o mesmo CPF.
    cursor.execute('''CREATE TABLE IF NOT EXISTS pacientes (cpf TEXT PRIMARY KEY, sus TEXT, nome TEXT, nomeSocial TEXT, naturalidade TEXT, dn TEXT, idade TEXT, sexo TEXT, civil TEXT, raca TEXT, ocupacao TEXT, mae TEXT, responsavel TEXT, tel TEXT, endereco TEXT, numero TEXT, bairro TEXT, cidade TEXT, estado TEXT)''')
    
    # Cria a tabela 'atendimentos' caso não exista.
    # O 'enviado_nuvem' é o controle do Gari: 0 significa que ainda não foi pro Google, 1 significa que já foi.
    cursor.execute('''CREATE TABLE IF NOT EXISTS atendimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, cpf TEXT, sus TEXT, data_atendimento TEXT, hora_atendimento TEXT, registro TEXT, procedencia TEXT, enviado_nuvem INTEGER DEFAULT 0)''')
    
    # Este bloco 'try' é uma medida de segurança (migração). 
    # Se você já tinha um banco antigo sem a coluna 'enviado_nuvem', ele tenta adicionar.
    # Se a coluna já existir, ele vai dar erro (OperationalError), mas o 'pass' manda ele ignorar e seguir a vida.
    try:
        cursor.execute("ALTER TABLE atendimentos ADD COLUMN enviado_nuvem INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass 
        
    # Salva as mudanças e fecha a porta do banco de dados
    conn.commit()
    conn.close()

# =========================================================================
# 🚀 FUNÇÃO 2: O MOTOR DO GOOGLE (COM FORMATO A:M E CENTRALIZAÇÃO)
# =========================================================================
def enviar_para_planilha(dados):
    # O 'try' tenta executar tudo isso. Se a internet cair no meio, ele pula pro 'except' lá no final.
    try:
        # 1. Autenticação e Acesso via ID
        # Pega as chaves de acesso no arquivo credentials.json e faz o login
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPE)
        client = gspread.authorize(creds)
        # Abre a planilha específica usando o código de identificação único dela
        spreadsheet = client.open_by_key(ID_PLANILHA)

        # Pega a data de hoje para saber em qual mês estamos
        agora = datetime.now()
        # Dicionário traduzindo o número do mês para o nome em português (sempre em maiúsculo)
        meses_pt = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO',
                    7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}
        # Cria o nome da aba (Ex: "ABRIL 2026")
        nome_aba = f"{meses_pt[agora.month]} {agora.year}"

        # 2. Gestão de Abas: Tenta abrir a aba do mês
        try:
            sheet = spreadsheet.worksheet(nome_aba)
        except gspread.exceptions.WorksheetNotFound:
            # Se a aba do mês não existir (ex: virou o mês pra MAIO), ele cria uma aba nova
            sheet = spreadsheet.add_worksheet(title=nome_aba, rows="1000", cols="15")

        # --- 🚀 O GATILHO QUE VOCÊ PEDIU: LINHA DE PLANTÃO (A ao M) ---
        # Pega o número do registro e tira os zeros da frente (ex: "001" vira "1")
        reg_limpo = str(dados.get('registro', '')).lstrip('0')
        
        # Se o registro digitado for exatamente o número 1, ele inicia a rotina de criar a divisória
        if reg_limpo == '1':
            # Pega só a hora do atendimento (ex: de "08:30" ele pega o "08" e transforma em número)
            hora_atend = int(dados.get('hora_atendimento', '07:00').split(':')[0])
            # Pega a data crua do atendimento
            data_raw = dados.get('data_atendimento', '')
            # Formata a data para o padrão Brasileiro (DD/MM/AAAA)
            data_fmt = datetime.strptime(data_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if data_raw else agora.strftime('%d/%m/%Y')
            
            # Define se é Plantão Diurno (entre 07h e 18h59) ou Noturno (fora desse horário)
            turno = 'DIURNO' if 7 <= hora_atend < 19 else 'NOTURNO'
            # Monta o texto que vai aparecer na planilha
            texto_plantao = f"PLANTÃO {turno} - {data_fmt}"
            
            try:
                # Adiciona uma nova linha onde a primeira célula tem o texto e as outras 12 estão vazias
                sheet.append_row([texto_plantao] + [""] * 12)
                # Conta quantas linhas tem na planilha para saber qual foi a linha que acabamos de adicionar
                num_linha = len(sheet.get_all_values()) 
                
                # A MÁGICA VISUAL: Define o espaço de A até M na linha atual (Ex: A2:M2)
                range_celulas = f'A{num_linha}:M{num_linha}'
                # Mescla (junta) todas as células dessa linha num blocão só
                sheet.merge_cells(range_celulas)
                # Formata a célula mesclada: Centraliza o texto, coloca em Negrito, tamanho 11 e fonte Inter
                sheet.format(range_celulas, {
                    "horizontalAlignment": "CENTER", 
                    "textFormat": {"bold": True, "fontSize": 11, "fontFamily": "Inter"}
                })
            except Exception as e_visual:
                # Se der erro só na hora de deixar bonito, ele avisa no painel mas não trava o envio
                print(f"⚠️ Erro ao formatar faixa de plantão: {e_visual}")

        # 3. Tratamento de Dados (Usando as funções do seu arquivo utils.py)
        
        # Tira acentos do nome e deixa tudo em MAIÚSCULO
        nome_limpo = remove_accents(dados.get('nome', '')).upper()
        # Tira acentos da rua e remove espaços sobrando no começo e fim (.strip)
        rua = remove_accents(dados.get('endereco', '')).strip()
        # Garante que o número seja só número. Se vier vazio, preenche com "S/N" (Sem Número)
        num = apenas_numeros(dados.get('numero', '')).strip() or "S/N"
        # Tira acentos do bairro
        bairro = remove_accents(dados.get('bairro', '')).strip()
        
        # Monta a primeira parte: "NOME DA RUA, NUMERO"
        rua_num = f"{rua}, {num}" if rua and num else (rua or num)
        # Monta a parte final: "NOME DA RUA, NUMERO - BAIRRO" (E joga tudo pra Maiúsculo)
        endereco_formatado = f"{rua_num} - {bairro}".upper()

        # Limpa o CPF (deixa só os números usando o utils)
        cpf_limpo = apenas_numeros(dados.get('cpf', ''))
        # Se o CPF tiver exatamente 11 números, ele coloca a máscara bonita (000.000.000-00)
        cpf_com_mask = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_limpo

        # Pega a Data de Nascimento crua (AAAA-MM-DD)
        dn_raw = dados.get('dn', '')
        # Converte a data de nascimento para o padrão BR (DD/MM/AAAA)
        dn_br = datetime.strptime(dn_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if (dn_raw and '-' in dn_raw) else dn_raw

        # Pega a procedência (de onde o paciente veio) e coloca em maiúsculo
        procedencia = str(dados.get('procedencia', '')).upper()
        # Se a procedência for "NORMAL", ele deixa a observação vazia. Se for SAMU/POLICIA, ele escreve na observação.
        obs = "" if procedencia == "NORMAL" else procedencia

        # 4. Montagem da Linha do Paciente (Aqui colocamos tudo na ordem exata das colunas)
        linha = [
            dados.get('registro'),             # Coluna A
            nome_limpo,                        # Coluna B
            dn_br,                             # Coluna C
            dados.get('idade'),                # Coluna D
            dados.get('sexo'),                 # Coluna E
            dados.get('raca'),                 # Coluna F
            dados.get('cidade'),               # Coluna G
            dados.get('hora_atendimento'),     # Coluna H
            cpf_com_mask,                      # Coluna I
            str(apenas_numeros(dados.get('sus', ''))), # Coluna J (SUS só com números, convertido pra texto)
            obs,                               # Coluna K
            endereco_formatado,                # Coluna L
            dados.get('tel')                   # Coluna M
        ]
        
        # Envia de fato a lista montada acima para a próxima linha vazia da planilha
        sheet.append_row(linha)
        
        # --- CORREÇÃO DO FORMATO (TIRA A CÓPIA AUTOMÁTICA DO GOOGLE) ---
        # Se for o registro 1, a linha do paciente não pode herdar o negrito/centro do plantão.
        if reg_limpo == '1':
            try:
                linha_paciente = len(sheet.get_all_values())
                sheet.format(f'A{linha_paciente}:M{linha_paciente}', {
                    "horizontalAlignment": "LEFT", 
                    "textFormat": {
                        "bold": False, 
                        "fontSize": 10, 
                        "fontFamily": "Inter"  
                    }
                })
            except Exception:
                pass # Ignora erros visuais para não travar o envio

        # Retorna "Verdadeiro" para avisar o Gari que deu tudo certo
        return True
        
    except Exception as e:
        # Se cair a internet ou der erro na API, ele imprime no painel e retorna "Falso"
        # Assim o Gari sabe que falhou e vai tentar de novo mais tarde.
        print(f"❌ Erro na Sincronização Google: {e}")
        return False

# =========================================================================
# 🧹 FUNÇÃO 3: O GARI DA NUVEM (FILA DE SINCRONIZAÇÃO EM SEGUNDO PLANO)
# =========================================================================
def gari_da_nuvem():
    # while True faz essa função rodar para sempre num loop infinito
    while True:
        # O try/except aqui garante que se o Gari tropeçar em algum erro, o programa não desliga.
        try:
            # Conecta no banco de dados local
            conn = sqlite3.connect(DB_NAME); 
            conn.row_factory = sqlite3.Row; # Faz as linhas retornarem como dicionários, facilitando a leitura
            cursor = conn.cursor()
            
            # Pede ao banco: "Me traga todos os atendimentos (junto com os dados do paciente) onde 'enviado_nuvem' é igual a 0, em ordem de chegada"
            cursor.execute('''SELECT a.id as id_atend, a.registro, a.data_atendimento, a.hora_atendimento, a.procedencia, p.* FROM atendimentos a JOIN pacientes p ON a.cpf = p.cpf WHERE a.enviado_nuvem = 0 ORDER BY a.id ASC''')
            # Guarda todos os resultados encontrados na variável 'pendentes'
            pendentes = cursor.fetchall()
            
            # Para cada paciente pendente encontrado...
            for p in pendentes:
                # Chama a Função 2 (enviar_para_planilha). 
                # Se ela retornar True (sucesso)...
                if enviar_para_planilha(dict(p)):
                    # Atualiza o status desse atendimento no banco local para 1 (Já enviado).
                    cursor.execute("UPDATE atendimentos SET enviado_nuvem = 1 WHERE id = ?", (p['id_atend'],))
                    # Salva a atualização no banco
                    conn.commit()
            # Fecha a conexão com o banco para não sobrecarregar
            conn.close()
        except: 
            # Se der qualquer erro no processo do Gari, ele simplesmente ignora (pass) e tenta no próximo ciclo
            pass
            
        # O Gari dorme por 2 segundos antes de recomeçar o loop infinito. 
        # Isso impede que o computador use 100% do processador à toa.
        time.sleep(2)


# =========================================================================
# 🌐 ROTAS FLASK (A COMUNICAÇÃO ENTRE O SITE E O PYTHON)
# =========================================================================

# Rota principal (Quando você acessa o IP local no navegador)
@app.route('/')
def index(): 
    # Ele carrega o arquivo HTML (a tela visual do sistema)
    return render_template('index.html')

# Rota para buscar paciente existente pelo CPF ou SUS (Ao digitar e dar Enter/Tab no front-end)
@app.route('/buscar/<id>', methods=['GET'])
def buscar_paciente(id):
    # Limpa o que foi digitado, deixando só números
    id_limpo = apenas_numeros(id)
    # Abre o banco de dados
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    # Procura um paciente onde o CPF ou o SUS seja exatamente igual aos números digitados
    cursor.execute("SELECT * FROM pacientes WHERE cpf=? OR sus=?", (id_limpo, id_limpo))
    # Pega o primeiro resultado (se houver)
    row = cursor.fetchone(); conn.close()
    
    # Se achou, devolve os dados em formato JSON para preencher a tela. Se não achou, devolve um erro 404.
    return jsonify(dict(row)) if row else (jsonify({"erro": "nulo"}), 404)

# Rota para salvar um novo atendimento (Quando clica no botão Salvar no sistema)
@app.route('/salvar', methods=['POST'])
def salvar():
    # Pega os dados que vieram lá da tela do navegador
    dados = request.json
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    try:
        # 1. Tenta inserir o Paciente. Se o CPF já existir, ele SUBSTITUI (REPLACE) os dados, mantendo tudo atualizado.
        cursor.execute('''INSERT OR REPLACE INTO pacientes (cpf, sus, nome, nomeSocial, naturalidade, dn, idade, sexo, civil, raca, ocupacao, mae, responsavel, tel, endereco, numero, bairro, cidade, estado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
        (apenas_numeros(dados.get('cpf','')), apenas_numeros(dados.get('sus','')), dados.get('nome',''), dados.get('nomeSocial',''), dados.get('naturalidade',''), dados.get('dn',''), dados.get('idade',''), dados.get('sexo',''), dados.get('civil',''), dados.get('raca',''), dados.get('ocupacao',''), dados.get('mae',''), dados.get('responsavel',''), dados.get('tel',''), dados.get('endereco',''), dados.get('numero',''), dados.get('bairro',''), dados.get('cidade',''), dados.get('estado','')))
        
        # 2. Insere a ficha de atendimento na tabela 'atendimentos'. 
        # Lembrando que o 'enviado_nuvem' entra como 0 automaticamente (graças ao DEFAULT 0 criado na Função 1).
        cursor.execute('''INSERT INTO atendimentos (cpf, sus, data_atendimento, hora_atendimento, registro, procedencia) VALUES (?, ?, ?, ?, ?, ?)''', 
        (apenas_numeros(dados.get('cpf')), apenas_numeros(dados.get('sus')), dados.get('data_atendimento'), dados.get('hora_atendimento'), dados.get('registro'), dados.get('procedencia')))
        
        # Salva tudo no banco
        conn.commit()
        # Retorna mensagem de sucesso E DEVOLVE O NÚMERO DO REGISTRO pro site!
        return jsonify({"status": "sucesso", "registro_gerado": dados.get('registro')})
        
    except Exception as e: 
        # Se der erro no banco (ex: disco cheio), avisa o site (Erro 500)
        return jsonify({"status": "erro", "msg": str(e)}), 500
    finally: 
        # Garante que a porta do banco sempre vai ser fechada, mesmo se der erro
        conn.close()

# =========================================================================
# 🎬 LIGANDO OS MOTORES (INÍCIO DO PROGRAMA)
# =========================================================================
# O Python só entra neste IF quando você roda o arquivo app.py diretamente no terminal
if __name__ == '__main__':
    # 1. Prepara o banco de dados (cria as tabelas se for a primeira vez)
    init_db()
    
    # 2. Inicia o "Gari da Nuvem" numa Thread separada. 
    # O 'daemon=True' faz com que o Gari morra automaticamente quando você desligar o servidor Flask.
    threading.Thread(target=gari_da_nuvem, daemon=True).start()
    
    # 3. Liga o Servidor Web (Flask) na porta 5000, permitindo acesso pela rede local (0.0.0.0).
    # use_reloader=False é vital aqui, senão o Flask reinicia sozinho e cria 2 "Garis" rodando ao mesmo tempo.
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)