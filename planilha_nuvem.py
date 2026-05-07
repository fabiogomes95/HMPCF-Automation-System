# =========================================================================
# ☁️ MOTOR DE SINCRONIZAÇÃO: GOOGLE SHEETS & GARI DA NUVEM
# =========================================================================
# Desenvolvido para: Hospital Municipal Presidente Café Filho
# Objetivo: Enviar atendimentos do SQLite para a nuvem de forma organizada,
# respeitando o horário de troca de plantão (07:00h) e evitando erros de 
# formatação que "somem" com os dados do paciente.
# =========================================================================

import sqlite3
import time
import gspread
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from utils import apenas_numeros, remove_accents

# Configurações globais de acesso
DB_NAME = 'hospital.db'
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
ID_PLANILHA = "1xw_x-bYlHCHzMe39g1mJKPFAD_IcXA8BB0uRfmmuR90"

def enviar_para_planilha(dados):
    """
    Função principal que conecta na API e organiza as abas por mês.
    """
    try:
        # 1. AUTENTICAÇÃO: Abre as portas do Google usando nossa chave JSON
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPE)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(ID_PLANILHA)

        # 2. LÓGICA DA VIRADA DO MÊS (MUITO IMPORTANTE):
        # No hospital, o mês só vira quando o pessoal da manhã chega (07:00).
        # Subtraímos 7 horas da hora atual. Assim, se for 01/05 às 06:00, 
        # o sistema ainda considera que estamos no "plantão noturno" de 30/04.
        agora = datetime.now()
        data_referencia = agora - timedelta(hours=7) 
        
        meses_pt = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO',
                    7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}
        
        # Define o nome da aba (Ex: "MAIO 2026")
        nome_aba = f"{meses_pt[data_referencia.month]} {data_referencia.year}"

        # 3. GERENCIAMENTO DA ABA:
        # Tenta abrir a aba do mês. Se não existir (primeiro dia do mês), ele cria uma nova.
        try:
            sheet = spreadsheet.worksheet(nome_aba)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=nome_aba, rows="1000", cols="15")
            # Se a aba é nova, já joga o cabeçalho oficial de uma vez
            sheet.append_row(['REG','NOME','DN','IDADE','SEXO','RAÇA','CIDADE','HORA','CPF','SUS','OBS','ENDEREÇO','TEL'])

        # 4. PREPARAÇÃO E LIMPEZA DOS DADOS:
        # Aqui a gente garante que nada vai com acento ou lixo para a nuvem.
        nome_limpo = remove_accents(dados.get('nome', '')).upper()
        rua = remove_accents(dados.get('endereco', '')).strip()
        num = apenas_numeros(dados.get('numero', '')).strip() or "S/N"
        bairro = remove_accents(dados.get('bairro', '')).strip()
        endereco_formatado = f"{rua}, {num} - {bairro}".upper()
        
        # Máscara de CPF para ficar bonito na planilha (000.000.000-00)
        cpf_limpo = apenas_numeros(dados.get('cpf', ''))
        cpf_mask = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_limpo

        # Converte a data do banco (YYYY-MM-DD) para o padrão Brasil (DD/MM/YYYY)
        dn_raw = dados.get('dn', '')
        dn_br = datetime.strptime(dn_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if (dn_raw and '-' in dn_raw) else dn_raw

        # Se for um atendimento "NORMAL", não precisa poluir a coluna OBS
        procedencia = str(dados.get('procedencia', '')).upper()
        obs = "" if procedencia == "NORMAL" else procedencia

        # Monta a lista final que será uma linha na planilha
        linha_paciente = [
            dados.get('registro'), nome_limpo, dn_br, dados.get('idade'), dados.get('sexo'),
            dados.get('raca'), dados.get('cidade'), dados.get('hora_atendimento'),
            cpf_mask, str(apenas_numeros(dados.get('sus', ''))), obs,
            endereco_formatado, dados.get('tel')
        ]

        # 5. ENVIO SEGURO (PROTEÇÃO CONTRA MESCLAGEM):
        # IMPORTANTE: Primeiro salvamos o paciente. O Google Sheets nos retorna 
        # exatamente em qual número de linha ele foi salvo.
        resultado = sheet.append_row(linha_paciente)
        
        # 6. TRATAMENTO DO TÍTULO DO PLANTÃO:
        # Se for o registro número 1, significa que um novo plantão começou.
        reg_limpo = str(dados.get('registro', '')).lstrip('0')
        
        if reg_limpo == '1':
            # Descobrimos a linha do paciente através da resposta da API (ex: 'A50')
            match = re.search(r'[A-Z]+(\d+)', resultado['updates']['updatedRange'])
            if match:
                num_linha_paciente = int(match.group(1))
                
                # Define se é Diurno ou Noturno baseado na hora do sistema
                hora_atend = int(dados.get('hora_atendimento', '07:00').split(':')[0])
                turno = 'DIURNO' if 7 <= hora_atend < 19 else 'NOTURNO'
                
                # Formata o texto que vai ficar no cabeçalho azul
                data_plantao = datetime.strptime(dados.get('data_atendimento'), '%Y-%m-%d').strftime('%d/%m/%Y') if dados.get('data_atendimento') else agora.strftime('%d/%m/%Y')
                texto_plantao = f"PLANTÃO {turno} - {data_plantao}"

                # PULO DO GATO: Insere uma linha NOVA acima do paciente e mescla.
                # Isso evita que o Google Sheets mescle a linha do paciente por erro.
                sheet.insert_row([texto_plantao] + [""] * 12, index=num_linha_paciente)
                
                # Aplica o estilo visual (Centralizado, Negrito, Azul Marinho)
                range_mesclagem = f'A{num_linha_paciente}:M{num_linha_paciente}'
                sheet.merge_cells(range_mesclagem)
                sheet.format(range_mesclagem, {
                    "horizontalAlignment": "CENTER", 
                    "textFormat": {
                        "bold": True, 
                        "fontSize": 12, 
                        "fontFamily": "Inter", 
                        "foregroundColor": {"red": 0.0, "green": 0.2, "blue": 0.6}
                    }
                })

        return True
    except Exception as e:
        print(f"❌ Erro na Sincronização Google: {e}")
        return False

# =========================================================================
# 🧹 O GARI DA NUVEM (ROBÔ DE SEGUNDO PLANO)
# =========================================================================
def gari_da_nuvem():
    """
    Fica rodando eternamente procurando o que ainda não foi enviado.
    """
    while True:
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Busca IDs que estão com enviado_nuvem = 0 (Pendente)
            cursor.execute("SELECT id FROM atendimentos WHERE enviado_nuvem = 0 ORDER BY id ASC")
            pendentes = cursor.fetchall()
            
            for p_id in pendentes:
                id_atend = p_id['id']
                
                # TRAVA DE SEGURANÇA: Muda para 2 (Processando) para outro gari não pegar o mesmo
                cursor.execute("UPDATE atendimentos SET enviado_nuvem = 2 WHERE id = ? AND enviado_nuvem = 0", (id_atend,))
                conn.commit()
                
                # Se conseguimos travar o registro, fazemos o JOIN para pegar todos os dados do paciente
                if cursor.rowcount == 1:
                    cursor.execute('''
                        SELECT a.registro, a.data_atendimento, a.hora_atendimento, a.procedencia, p.* FROM atendimentos a 
                        JOIN pacientes p ON a.cpf = p.cpf 
                        WHERE a.id = ?''', (id_atend,))
                    dados_completos = cursor.fetchone()
                    
                    # Tenta enviar para o Google Sheets
                    if dados_completos and enviar_para_planilha(dict(dados_completos)):
                        # Sucesso total!
                        cursor.execute("UPDATE atendimentos SET enviado_nuvem = 1 WHERE id = ?", (id_atend,))
                    else:
                        # Se falhou (internet caiu, etc), volta para 0 para tentar de novo depois
                        cursor.execute("UPDATE atendimentos SET enviado_nuvem = 0 WHERE id = ?", (id_atend,))
                    conn.commit()
            conn.close()
        except: 
            pass # Silencia erros de conexão de banco para não travar o loop
            
        time.sleep(2) # Espera 2 segundos para não sobrecarregar o processador