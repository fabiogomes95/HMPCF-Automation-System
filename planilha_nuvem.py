# =========================================================================
# ☁️ MOTOR DO GOOGLE SHEETS E GARI DA NUVEM (planilha_nuvem.py)
# =========================================================================
# OBJETIVO: Cuidar exclusivamente do envio de dados para o Google Sheets em 
# segundo plano, mantendo a trava anti-duplicação (Gari da Nuvem) intacta.
# =========================================================================

import sqlite3
import time
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from utils import apenas_numeros, remove_accents

# Nome do banco de dados referenciado localmente
DB_NAME = 'hospital.db'

# Configurações de permissão do Google
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
ID_PLANILHA = "1xw_x-bYlHCHzMe39g1mJKPFAD_IcXA8BB0uRfmmuR90"

# =========================================================================
# 🚀 FUNÇÃO DE ENVIO E FORMATAÇÃO (Sua lógica exata)
# =========================================================================
def enviar_para_planilha(dados):
    try:
        # 1. Autenticação e Abertura da Planilha
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPE)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(ID_PLANILHA)

        agora = datetime.now()
        meses_pt = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO',
                    7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}
        nome_aba = f"{meses_pt[agora.month]} {agora.year}"

        # 2. Gestão de Abas
        try:
            sheet = spreadsheet.worksheet(nome_aba)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=nome_aba, rows="1000", cols="15")

        # --- GATILHO DA LINHA DE PLANTÃO ---
        reg_limpo = str(dados.get('registro', '')).lstrip('0')
        if reg_limpo == '1':
            hora_atend = int(dados.get('hora_atendimento', '07:00').split(':')[0])
            data_raw = dados.get('data_atendimento', '')
            data_fmt = datetime.strptime(data_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if data_raw else agora.strftime('%d/%m/%Y')
            
            turno = 'DIURNO' if 7 <= hora_atend < 19 else 'NOTURNO'
            texto_plantao = f"PLANTÃO {turno} - {data_fmt}"
            
            try:
                sheet.append_row([texto_plantao] + [""] * 12)
                num_linha = len(sheet.get_all_values()) 
                range_celulas = f'A{num_linha}:M{num_linha}'
                sheet.merge_cells(range_celulas)
                sheet.format(range_celulas, {
                    "horizontalAlignment": "CENTER", 
                    "textFormat": {"bold": True, "fontSize": 11, "fontFamily": "Inter"}
                })
            except Exception as e_visual:
                print(f"⚠️ Erro ao formatar faixa de plantão: {e_visual}")

        # 3. Tratamento de Dados (Limpeza)
        nome_limpo = remove_accents(dados.get('nome', '')).upper()
        rua = remove_accents(dados.get('endereco', '')).strip()
        num = apenas_numeros(dados.get('numero', '')).strip() or "S/N"
        bairro = remove_accents(dados.get('bairro', '')).strip()
        rua_num = f"{rua}, {num}" if rua and num else (rua or num)
        endereco_formatado = f"{rua_num} - {bairro}".upper()

        cpf_limpo = apenas_numeros(dados.get('cpf', ''))
        cpf_com_mask = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_limpo

        dn_raw = dados.get('dn', '')
        dn_br = datetime.strptime(dn_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if (dn_raw and '-' in dn_raw) else dn_raw

        procedencia = str(dados.get('procedencia', '')).upper()
        obs = "" if procedencia == "NORMAL" else procedencia

        # 4. Montagem e Envio da Linha
        linha = [
            dados.get('registro'), nome_limpo, dn_br, dados.get('idade'), dados.get('sexo'),
            dados.get('raca'), dados.get('cidade'), dados.get('hora_atendimento'),
            cpf_com_mask, str(apenas_numeros(dados.get('sus', ''))), obs,
            endereco_formatado, dados.get('tel')
        ]
        
        sheet.append_row(linha)
        
        # Correção de herança de formatação do Google
        if reg_limpo == '1':
            try:
                linha_paciente = len(sheet.get_all_values())
                sheet.format(f'A{linha_paciente}:M{linha_paciente}', {
                    "horizontalAlignment": "LEFT", 
                    "textFormat": {"bold": False, "fontSize": 10, "fontFamily": "Inter"}
                })
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"❌ Erro na Sincronização Google: {e}")
        return False

# =========================================================================
# 🧹 O GARI DA NUVEM (Loop e Trava Atômica originais)
# =========================================================================
def gari_da_nuvem():
    while True:
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Pega apenas os IDs pendentes
            cursor.execute("SELECT id FROM atendimentos WHERE enviado_nuvem = 0 ORDER BY id ASC")
            pendentes_ids = cursor.fetchall()
            
            for pid in pendentes_ids:
                id_atend = pid['id']
                
                # 2. 🛡️ A TRAVA ATÔMICA: Tranca mudando para 2 antes de pegar os dados
                cursor.execute("UPDATE atendimentos SET enviado_nuvem = 2 WHERE id = ? AND enviado_nuvem = 0", (id_atend,))
                conn.commit()
                
                # 3. Se este Gari trancou com sucesso, puxa os dados e envia
                if cursor.rowcount == 1:
                    # Seu JOIN perfeito que puxa o paciente e o atendimento juntos
                    cursor.execute('''SELECT a.id as id_atend, a.registro, a.data_atendimento, 
                                      a.hora_atendimento, a.procedencia, p.* FROM atendimentos a JOIN pacientes p ON a.cpf = p.cpf 
                                      WHERE a.id = ?''', (id_atend,))
                    p = cursor.fetchone()
                    
                    if p and enviar_para_planilha(dict(p)):
                        # Sucesso: Muda para 1 (Concluído)
                        cursor.execute("UPDATE atendimentos SET enviado_nuvem = 1 WHERE id = ?", (id_atend,))
                    else:
                        # Falha: Devolve para 0
                        cursor.execute("UPDATE atendimentos SET enviado_nuvem = 0 WHERE id = ?", (id_atend,))
                        
                    conn.commit()
            conn.close()
        except Exception as e:
            pass # Erros de banco são ignorados até o próximo ciclo
            
        time.sleep(2)