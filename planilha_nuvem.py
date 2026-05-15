"""
PLANILHA_NUVEM.PY — Gari da Nuvem | Sincronizador Google Sheets
=================================================================
Esse é o "Gari da Nuvem" — um robô de segundo plano que fica
varrendo o SQLite e jogando os atendimentos pro Google Sheets.

Por que "Gari"? Porque ele limpa a sujeira (dados novos) e
joga na nuvem sem ninguém precisar fazer nada.

Funciona assim:
1. O app_recepcao.py inicia uma thread com o gari_da_nuvem()
2. Ele fica num loop infinito, dormindo 10s entre ciclos
3. A cada ciclo, procura atendimentos com enviado_nuvem = 0
4. Envia pra planilha, marca como 1 (enviado) ou 0 (falhou)

Regra de ouro: o mês "vira" às 07:00h (troca de plantão).
Se é 03/05 às 06:00, ainda conta como ABRIL (porque o plantão
noturno ainda está vigente).
"""

import sqlite3
import time
import gspread
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from utils import apenas_numeros, remove_accents

# === CONFIGURAÇÕES ===
DB_NAME = 'hospital.db'  # SQLite local com os atendimentos

# Escopos de permissão da API Google:
# - sheets: ler/escrever na planilha
# - drive: gerenciar arquivos no Drive
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ID da planilha Google Sheets (vem da URL: /d/1xw_x-.../edit)
ID_PLANILHA = "1xw_x-bYlHCHzMe39g1mJKPFAD_IcXA8BB0uRfmmuR90"


def enviar_para_planilha(dados):
    """
    Envia UM atendimento para a planilha Google.
    
    Fluxo:
    1. Autentica na API com o arquivo credentials.json
    2. Descobre a aba certa (ex: "MAIO 2026")
    3. Formata os dados (remove acentos, mascara CPF)
    4. Envia a linha
    5. Se for o primeiro registro do plantão, insere um cabeçalho
    
    Retorna True se deu certo, False se deu erro.
    """
    try:
        # --- AUTENTICAÇÃO GOOGLE ---
        # Carrego as credenciais do arquivo JSON baixado do Google Cloud
        creds = Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPE
        )
        client = gspread.authorize(creds)
        # Abro a planilha pelo ID (mais seguro que pelo nome)
        spreadsheet = client.open_by_key(ID_PLANILHA)

        # --- LÓGICA DA VIRADA DO MÊS (REGRA DO PLANTÃO) ---
        # Se agora é 05/05 às 03:00, o plantão NOTURNO ainda é de MAIO
        # Mas na prática a madrugada pertence ao dia anterior...
        # Então eu SUBtraio 7h da hora atual pra decidir o mês
        # 05/05 03:00 - 7h = 04/05 20:00 → mês = MAIO (ok)
        # 05/05 06:00 - 7h = 04/05 23:00 → mês = MAIO (ok, plantão noturno de ontem)
        # 05/05 07:01 - 7h = 05/05 00:01 → mês = MAIO (novo plantão)
        # Basicamente: até 07:00 da manhã, o mês ainda é o anterior
        agora = datetime.now()
        data_referencia = agora - timedelta(hours=7)

        # Dicionário de meses em português (pro nome da aba)
        meses_pt = {
            1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARCO', 4: 'ABRIL',
            5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
            9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
        }
        nome_aba = f"{meses_pt[data_referencia.month]} {data_referencia.year}"

        # --- GERENCIAMENTO DA ABA ---
        # Tenta pegar a aba. Se não existir, cria uma nova.
        try:
            sheet = spreadsheet.worksheet(nome_aba)
        except gspread.exceptions.WorksheetNotFound:
            # Aba nova! Crio com 1000 linhas e 15 colunas
            sheet = spreadsheet.add_worksheet(
                title=nome_aba, rows=1000, cols=15
            )
            # Cabeçalho da planilha
            sheet.append_row([
                'REG', 'NOME', 'DN', 'IDADE', 'SEXO', 'RACA',
                'CIDADE', 'HORA', 'CPF', 'SUS', 'OBS',
                'ENDERECO', 'TEL'
            ])

        # --- FORMATAÇÃO DOS DADOS ---
        # Limpo e padronizo cada campo antes de enviar
        nome_limpo = remove_accents(dados.get('nome', '')).upper()
        rua = remove_accents(dados.get('endereco', '')).strip()
        num = apenas_numeros(dados.get('numero', '')).strip() or "S/N"
        bairro = remove_accents(dados.get('bairro', '')).strip()
        endereco_formatado = f"{rua}, {num} - {bairro}".upper()

        # CPF com máscara (000.000.000-00) — mais legível na planilha
        cpf_limpo = apenas_numeros(dados.get('cpf', ''))
        if len(cpf_limpo) == 11:
            cpf_mask = (
                f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}."
                f"{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
            )
        else:
            cpf_mask = cpf_limpo

        # --- BLINDAGEM DA DATA DE NASCIMENTO ---
        # Proteção contra o erro 20007 (data explosiva tipo 20007-02-09)
        # que fazia a planilha comer dados do paciente
        dn_raw = str(dados.get('dn', ''))
        dn_br = dn_raw  # valor padrão: se falhar, envia como veio
        try:
            if dn_raw and '-' in dn_raw:
                dn_br = datetime.strptime(dn_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            # Data inválida? Ignoro a conversão, envio o valor original
            pass

        # Se a procedência for "NORMAL", deixo OBS em branco
        # Caso contrário, uso a procedência como observação
        procedencia = str(dados.get('procedencia', '')).upper()
        obs = "" if procedencia == "NORMAL" else procedencia

        # Monto a linha completa do paciente
        linha_paciente = [
            dados.get('registro'),
            nome_limpo,
            dn_br,
            dados.get('idade'),
            dados.get('sexo'),
            dados.get('raca'),
            dados.get('cidade'),
            dados.get('hora_atendimento'),
            cpf_mask,
            str(apenas_numeros(dados.get('sus', ''))),
            obs,
            endereco_formatado,
            dados.get('tel')
        ]

        # --- ENVIO PARA A PLANILHA ---
        # append_row adiciona uma nova linha no final
        resultado = sheet.append_row(linha_paciente)

        # --- TRATAMENTO DO CABEÇALHO DO PLANTÃO ---
        # Se o REGISTRO for "1" (primeiro paciente do plantão),
        # insiro uma linha extra com o título do plantão em negrito
        reg_limpo = str(dados.get('registro', '')).lstrip('0')

        if reg_limpo == '1':
            # Extraio o número da linha onde o paciente foi inserido
            match = re.search(r'[A-Z]+(\d+)', resultado['updates']['updatedRange'])
            if match:
                num_linha_paciente = int(match.group(1))

                # Determino o turno pela hora do atendimento
                hora_atend = int(
                    dados.get('hora_atendimento', '07:00').split(':')[0]
                )
                turno = 'DIURNO' if 7 <= hora_atend < 19 else 'NOTURNO'

                # Formato a data do plantão
                data_atend_raw = dados.get('data_atendimento')
                data_plantao = agora.strftime('%d/%m/%Y')
                try:
                    if data_atend_raw:
                        data_plantao = datetime.strptime(
                            data_atend_raw, '%Y-%m-%d'
                        ).strftime('%d/%m/%Y')
                except ValueError:
                    pass

                # Insiro o título "PLANTÃO DIURNO - 01/01/2026"
                # na linha ACIMA do primeiro paciente
                texto_plantao = f"PLANTAO {turno} - {data_plantao}"
                sheet.insert_row(
                    [texto_plantao] + [""] * 12,
                    index=num_linha_paciente
                )

                # Mesclo as células e formata em negrito azul
                range_mesclagem = f'A{num_linha_paciente}:M{num_linha_paciente}'
                sheet.merge_cells(range_mesclagem)
                sheet.format(range_mesclagem, {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "bold": True,
                        "fontSize": 12,
                        "fontFamily": "Inter",
                        "foregroundColor": {
                            "red": 0.0, "green": 0.2, "blue": 0.6
                        }
                    }
                })

        return True

    except Exception as e:
        print(f"Erro na Sincronizacao Google: {e}")
        return False


def gari_da_nuvem():
    """
    Robô de SEGUNDO PLANO: fica rodando pra sempre.
    
    A cada 10 segundos:
    1. Abre o SQLite
    2. Pega todos os atendimentos com enviado_nuvem = 0
    3. Pra cada um: marca como 2 (processando), tenta enviar
    4. Se enviou: marca como 1 (enviado)
    5. Se falhou: marca como 0 (pendente) pra tentar de novo
    
    O "lock" com enviado_nuvem = 2 evita que duas threads
    peguem o mesmo atendimento ao mesmo tempo.
    """
    while True:
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Busco atendimentos que ainda não foram pra nuvem
            cursor.execute(
                "SELECT id FROM atendimentos "
                "WHERE enviado_nuvem = 0 ORDER BY id ASC"
            )
            pendentes = cursor.fetchall()

            for p_id in pendentes:
                id_atend = p_id['id']

                # --- LOCK OTIMISTA ---
                # Marco como 2 pra nenhuma outra thread pegar
                cursor.execute(
                    "UPDATE atendimentos SET enviado_nuvem = 2 "
                    "WHERE id = ? AND enviado_nuvem = 0",
                    (id_atend,)
                )
                conn.commit()

                # Só continuo se realmente consegui fazer o lock
                if cursor.rowcount == 1:
                    # JOIN entre atendimentos e pacientes pelo CPF
                    cursor.execute('''
                        SELECT a.registro, a.data_atendimento,
                               a.hora_atendimento, a.procedencia, p.*
                        FROM atendimentos a
                        JOIN pacientes p ON a.cpf = p.cpf
                        WHERE a.id = ?
                    ''', (id_atend,))
                    dados_completos = cursor.fetchone()

                    if dados_completos and enviar_para_planilha(dict(dados_completos)):
                        # Sucesso! Marco como enviado
                        cursor.execute(
                            "UPDATE atendimentos SET enviado_nuvem = 1 "
                            "WHERE id = ?",
                            (id_atend,)
                        )
                    else:
                        # Falhou! Volto pra 0 pra tentar de novo
                        cursor.execute(
                            "UPDATE atendimentos SET enviado_nuvem = 0 "
                            "WHERE id = ?",
                            (id_atend,)
                        )
                    conn.commit()

            conn.close()

        except Exception:
            # Se qualquer erro acontecer (ex: banco locked), ignoro
            # e tento de novo no próximo ciclo
            pass

        # Durmo 10 segundos antes do próximo ciclo
        time.sleep(10)
