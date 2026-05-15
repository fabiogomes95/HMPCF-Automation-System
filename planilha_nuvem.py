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
        agora = datetime.now()
        data_referencia = agora - timedelta(hours=7) 
        
        meses_pt = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO',
                    7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}
        
        nome_aba = f"{meses_pt[data_referencia.month]} {data_referencia.year}"

        # 3. GERENCIAMENTO DA ABA:
        try:
            sheet = spreadsheet.worksheet(nome_aba)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=nome_aba, rows=1000, cols=15)
            sheet.append_row(['REG','NOME','DN','IDADE','SEXO','RAÇA','CIDADE','HORA','CPF','SUS','OBS','ENDEREÇO','TEL'])

        # 4. PREPARAÇÃO E LIMPEZA DOS DADOS:
        nome_limpo = remove_accents(dados.get('nome', '')).upper()
        rua = remove_accents(dados.get('endereco', '')).strip()
        num = apenas_numeros(dados.get('numero', '')).strip() or "S/N"
        bairro = remove_accents(dados.get('bairro', '')).strip()
        endereco_formatado = f"{rua}, {num} - {bairro}".upper()
        
        cpf_limpo = apenas_numeros(dados.get('cpf', ''))
        cpf_mask = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_limpo

        # 🛡️ BLINDAGEM DA DATA DE NASCIMENTO (Fim do erro 20007)
        dn_raw = str(dados.get('dn', ''))
        dn_br = dn_raw # Valor padrão caso a conversão falhe
        try:
            if dn_raw and '-' in dn_raw:
                # Tenta converter
                dn_br = datetime.strptime(dn_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            # Se a data for absurda (ex: 20007-02-09), ignora a conversão e envia como veio
            pass 

        procedencia = str(dados.get('procedencia', '')).upper()
        obs = "" if procedencia == "NORMAL" else procedencia

        linha_paciente = [
            dados.get('registro'), nome_limpo, dn_br, dados.get('idade'), dados.get('sexo'),
            dados.get('raca'), dados.get('cidade'), dados.get('hora_atendimento'),
            cpf_mask, str(apenas_numeros(dados.get('sus', ''))), obs,
            endereco_formatado, dados.get('tel')
        ]

        # 5. ENVIO SEGURO
        resultado = sheet.append_row(linha_paciente)
        
        # 6. TRATAMENTO DO TÍTULO DO PLANTÃO:
        reg_limpo = str(dados.get('registro', '')).lstrip('0')
        
        if reg_limpo == '1':
            match = re.search(r'[A-Z]+(\d+)', resultado['updates']['updatedRange'])
            if match:
                num_linha_paciente = int(match.group(1))
                
                hora_atend = int(dados.get('hora_atendimento', '07:00').split(':')[0])
                turno = 'DIURNO' if 7 <= hora_atend < 19 else 'NOTURNO'
                
                # 🛡️ BLINDAGEM DA DATA DE ATENDIMENTO
                data_atend_raw = dados.get('data_atendimento')
                data_plantao = agora.strftime('%d/%m/%Y') # Valor seguro padrão
                try:
                    if data_atend_raw:
                        data_plantao = datetime.strptime(data_atend_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    pass

                texto_plantao = f"PLANTÃO {turno} - {data_plantao}"

                sheet.insert_row([texto_plantao] + [""] * 12, index=num_linha_paciente)
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
            
            cursor.execute("SELECT id FROM atendimentos WHERE enviado_nuvem = 0 ORDER BY id ASC")
            pendentes = cursor.fetchall()
            
            for p_id in pendentes:
                id_atend = p_id['id']
                
                cursor.execute("UPDATE atendimentos SET enviado_nuvem = 2 WHERE id = ? AND enviado_nuvem = 0", (id_atend,))
                conn.commit()
                
                if cursor.rowcount == 1:
                    cursor.execute('''
                        SELECT a.registro, a.data_atendimento, a.hora_atendimento, a.procedencia, p.* FROM atendimentos a 
                        JOIN pacientes p ON a.cpf = p.cpf 
                        WHERE a.id = ?''', (id_atend,))
                    dados_completos = cursor.fetchone()
                    
                    if dados_completos and enviar_para_planilha(dict(dados_completos)):
                        cursor.execute("UPDATE atendimentos SET enviado_nuvem = 1 WHERE id = ?", (id_atend,))
                    else:
                        cursor.execute("UPDATE atendimentos SET enviado_nuvem = 0 WHERE id = ?", (id_atend,))
                    conn.commit()
            conn.close()
        except Exception: 
            pass 
            
        time.sleep(10)