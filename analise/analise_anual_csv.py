import os
import re
import csv
from io import StringIO
import pandas as pd
from datetime import datetime
from weasyprint import HTML

print("==================================================")
print("🔍 ANALISADOR DE FREQUÊNCIA DE PACIENTES (.CSV)")
print("==================================================\n")

pasta_atual = os.path.dirname(os.path.abspath(__file__))

print("📡 Procurando arquivos .csv na pasta...")
arquivos_csv = [os.path.join(pasta_atual, f) for f in os.listdir(pasta_atual) if f.lower().endswith('.csv')]

if not arquivos_csv:
    print("🛑 ERRO: Nenhum arquivo .csv encontrado na pasta.")
    exit()

# 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
def limpar_numeros(texto):
    return re.sub(r'\D', '', str(texto))

def formatar_cpf(cpf):
    c = limpar_numeros(cpf)
    if len(c) == 11:
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
    return "NÃO INFORMADO"

def formatar_sus(sus):
    s = limpar_numeros(sus)
    if len(s) == 15:
        return f"{s[:3]} {s[3:7]} {s[7:11]} {s[11:]}"
    return "NÃO INFORMADO"

def gerar_id_unico(row):
    cpf = limpar_numeros(row.get('cpf', ''))
    if len(cpf) == 11: return f"CPF_{cpf}"
    
    sus = limpar_numeros(row.get('sus', ''))
    if len(sus) == 15: return f"SUS_{sus}"
    
    nome_cru = str(row.get('nome', '')).upper().strip()
    nome = re.sub(r'[^A-Z0-9]', '', nome_cru)
    dn = limpar_numeros(row.get('dn', ''))
    
    if not nome or nome == 'NAN' or 'PLANTAO' in nome_cru or nome == 'NOME':
        return "IGNORAR"
        
    return f"NOME_{nome}_DN_{dn}"

# 3. LEITURA "TRATOR" BLINDADA
dfs = []
colunas_oficiais = ['registro','nome','dn','idade','sexo','raca','cidade','hora','cpf','sus','obs','endereco','tel']

print("\n⚙️ INICIANDO LEITURA DOS CSVS...")
for f in arquivos_csv:
    try:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                texto_csv = file.read()
        except UnicodeDecodeError:
            with open(f, 'r', encoding='latin1') as file:
                texto_csv = file.read()
                
        delimitador = ';' if texto_csv.count(';') > texto_csv.count(',') else ','
        leitor = csv.reader(StringIO(texto_csv), delimiter=delimitador)
        
        dados_limpos = []
        for linha in leitor:
            if not linha: continue 
            while len(linha) < 13:
                linha.append("")
            linha = linha[:13]
            dados_limpos.append(linha)
            
        df = pd.DataFrame(dados_limpos, columns=colunas_oficiais)
        
        if not df.empty and str(df.iloc[0]['nome']).strip().lower() == 'nome':
            df = df.iloc[1:].reset_index(drop=True)
            
        dfs.append(df)
        print(f"✔️ Arquivo processado: {os.path.basename(f)} ({len(df)} registros)")

    except Exception as e:
        print(f"⚠️ Erro ao ler {os.path.basename(f)}: {e}")

if not dfs:
    print("🛑 Nenhum dado válido pôde ser extraído dos CSVs.")
    exit()

df_geral = pd.concat(dfs, ignore_index=True)

# 4. APLICAÇÃO DA INTELIGÊNCIA DE IDENTIFICAÇÃO E LIMPEZA
print("\n🧠 Cruzando os dados e limpando ruídos...")
df_geral['ID_UNICO'] = df_geral.apply(gerar_id_unico, axis=1)
df_geral = df_geral[df_geral['ID_UNICO'] != "IGNORAR"]

top_ids = df_geral['ID_UNICO'].value_counts().head(20).index
df_top = df_geral[df_geral['ID_UNICO'].isin(top_ids)]

print("🏗️ Gerando o PDF Limpo...")

pacientes_html = ""

# 5. MONTAGEM DOS BLOCOS DO PDF (TOP 20 COM DATA DE NASCIMENTO)
for i, id_paciente in enumerate(top_ids, start=1):
    dados_p = df_top[df_top['ID_UNICO'] == id_paciente]
    
    nomes_validos = dados_p.get('nome', pd.Series(dtype=str)).dropna()
    nome_exibicao = str(nomes_validos.iloc[0]).strip().upper() if not nomes_validos.empty else "NOME NÃO INFORMADO"
    
    cpf_raw = dados_p.get('cpf', pd.Series(dtype=str)).dropna()
    cpf_exibicao = formatar_cpf(cpf_raw.iloc[0]) if not cpf_raw.empty else "NÃO INFORMADO"
    
    sus_raw = dados_p.get('sus', pd.Series(dtype=str)).dropna()
    sus_exibicao = formatar_sus(sus_raw.iloc[0]) if not sus_raw.empty else "NÃO INFORMADO"

    # Extração da Data de Nascimento (DN)
    dn_raw = dados_p.get('dn', pd.Series(dtype=str)).dropna()
    dn_exibicao = str(dn_raw.iloc[0]).strip() if not dn_raw.empty else "NÃO INFORMADA"
    
    total_entradas = len(dados_p)
    
    pacientes_html += f"""
    <div class="patient-card">
        <div class="patient-name">👤 {i}º - {nome_exibicao}</div>
        <div class="patient-info">📅 <b>NASCIMENTO:</b> {dn_exibicao}</div>
        <div class="patient-info">💳 <b>CPF:</b> {cpf_exibicao}</div>
        <div class="patient-info">🏥 <b>SUS:</b> {sus_exibicao}</div>
        <div class="patient-info">🔄 <b>TOTAL DE ENTRADAS:</b> {total_entradas} vez(es)</div>
    </div>
    """

# 6. GERAÇÃO DO PDF
html_template = f"""
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ 
            size: A4; 
            margin: 1.5cm; 
            background-color: #ffffff;
        }}
        body {{ font-family: 'Segoe UI', sans-serif; color: #000; background: #ffffff; margin: 0; }}
        .header {{ text-align: center; background-color: #ffffff; color: #000; padding: 10px 0; border-bottom: 2px solid #000; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 16pt; letter-spacing: 1px; font-weight: bold; }}
        .header p {{ margin: 5px 0 0 0; font-size: 10pt; color: #555; }}
        .container {{ column-count: 2; column-gap: 1.5cm; width: 100%; }}
        .patient-card {{ break-inside: avoid; page-break-inside: avoid; background-color: #ffffff; border: 1px solid #ccc; border-left: 4px solid #333; border-radius: 4px; padding: 12px; margin-bottom: 15px; font-size: 9pt; }}
        .patient-name {{ font-weight: bold; font-size: 11pt; text-transform: uppercase; margin-bottom: 8px; color: #000; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
        .patient-info {{ margin-bottom: 3px; color: #333; font-size: 10pt; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 HMPCF - AUDITORIA DE FREQUÊNCIA (CSV)</h1>
        <p>Top 20 Pacientes | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    <div class="container">
        {pacientes_html}
    </div>
</body>
</html>
"""

arquivo_pdf = os.path.join(pasta_atual, "RELATORIO_FREQUENCIA_CSV.pdf")
HTML(string=html_template).write_pdf(arquivo_pdf)

print(f"\n✅ SUCESSO! Relatório em PDF gerado.")
print(f"📁 Salvo em: {arquivo_pdf}")