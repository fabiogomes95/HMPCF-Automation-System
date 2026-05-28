# ==============================================================================
# PROJETO: Gerador de Arquivos BPA (SUS) com Validação de Dados
# OBJETIVO: Ler planilhas CSV despadronizadas, limpar os dados, validar o CNS
#           e exportar no layout posicional exato exigido pelo Ministério da Saúde.
# ==============================================================================

# --- 1. IMPORTAÇÃO DE BIBLIOTECAS (Nossa caixa de ferramentas) ---
import csv           # Ferramenta para ler e escrever arquivos separados por vírgula/ponto-e-vírgula
import re            # Regex (Expressões Regulares): Nosso "detetive" para achar padrões de texto
import unicodedata   # Ferramenta para lidar com acentos e cedilhas
import sys           # Para configurar o caminho de importação
import os
import tkinter as tk # Ferramenta para criar janelas (interfaces gráficas) no Windows
from tkinter import filedialog, messagebox # Módulos para abrir a janela de selecionar arquivo e alertas
from datetime import datetime # Ferramenta para manipular datas

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import CEP_RUA, CODIGO_UNIDADE, FOLHA_CODIGO, SEQ_PROFISSIONAL

# --- 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO (Nossos operários) ---

def remove_accents(input_str):
    """
    Função para arrancar acentos e caracteres invisíveis que travam o sistema.
    """
    if not input_str: return ""
    
    nfkd_form = unicodedata.normalize('NFKD', str(input_str))
    limpo = u"".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()
    limpo = limpo.encode('ascii', 'replace').decode('ascii')
    return limpo.replace('?', ' ')

def parse_endereco_fixed(endereco):
    """
    Função que recebe um endereço bagunçado e fatia ele em: Rua, Complemento, Número e Bairro.
    """
    endereco = re.sub(r'\d{4,5}-\d{4}$', '', str(endereco)).strip()
    endereco = remove_accents(endereco).strip()
    
    matches = list(re.finditer(r'\d+|\bS/N\b|\bSN\b', endereco))
    if not matches:
        matches = list(re.finditer(r'\d+|S/N|SN', endereco))
        
    if not matches:
        return endereco.ljust(30)[:30], "".ljust(10), "S/N".ljust(5)[:5], "".ljust(30)[:30]
    
    if len(matches) > 1:
        best_m = matches[-1]
        for m in matches:
            if m.start() < 15:
                prox_texto = endereco[m.end():m.end()+4]
                if prox_texto in [' DE ', ' DO ', ' DA ']: continue
                if m.start() >= 2 and endereco[m.start()-2:m.start()] == 'R.': continue
            best_m = m
            break
    else:
        best_m = matches[0]
        
    rua = endereco[:best_m.start()].strip('., -')
    numero = best_m.group().strip()
    
    if numero == "SN":
        numero = "S/N"
    if not numero:
        numero = "S/N"
        
    bairro = endereco[best_m.end():].strip('., -')
    
    return rua.ljust(30)[:30], "".ljust(10), numero.ljust(5)[:5], bairro.ljust(30)[:30]

def valida_cns(cns):
    """
    Função matemática que valida se o número do SUS existe (Módulo 11).
    """
    if len(cns) != 15 or cns[0] not in '12789':
        return False
    
    soma = sum(int(cns[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0


# --- 3. A FUNÇÃO PRINCIPAL (O Motor do Programa) ---

def process_file():
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Selecione a planilha CSV do BPA",
        filetypes=[("Arquivos CSV", "*.csv")]
    )
    if not file_path: return

    e_unidade = CODIGO_UNIDADE
    f_folha = FOLHA_CODIGO
    g_seq = SEQ_PROFISSIONAL
    h_cep_rua = CEP_RUA
    
    lines = []
    erros = []

    # O bloco TRY começa aqui! Tudo dentro dele precisa estar com espaços (indentado) para a direita
    try:
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            content = f.read()
        separador = ';' if content.count(';') > content.count(',') else ','
        
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            reader = csv.reader(f, delimiter=separador)
            
            for i, row in enumerate(reader):
                linha_num = i + 1
                if len(row) < 5: 
                    continue 
                
                nome_log = "NOME DESCONHECIDO"
                nome_raw = str(row[1]) if len(row) > 1 else ""
                
                if not nome_raw or re.search(r'\d', nome_raw) or len(nome_raw) < 4:
                    for col in row:
                        if len(str(col)) > 5 and not re.search(r'\d', str(col)):
                            nome_raw = str(col)
                            break
                if nome_raw:
                    nome_log = remove_accents(nome_raw).strip()

                cpf_log = "CPF NAO INFORMADO"
                for col in row:
                    c_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', str(col))
                    if c_match:
                        cpf_log = c_match.group(0)
                        break
                
                cns = None
                for col in row:
                    limpo = re.sub(r'\D', '', str(col))
                    if len(limpo) == 15 and limpo[0] in '12789':
                        cns = limpo
                        break
                
                if not cns:
                    erros.append(f"Linha {linha_num:04d} | PACIENTE: {nome_log.ljust(30)[:30]} | CPF: {cpf_log.ljust(14)} | MOTIVO: Faltou digitar o CNS")
                    continue
                
                if not valida_cns(cns):
                    erros.append(f"Linha {linha_num:04d} | PACIENTE: {nome_log.ljust(30)[:30]} | CPF: {cpf_log.ljust(14)} | MOTIVO: CNS Invalido (Erro de Digitacao: {cns})")
                    continue
                    
                date_str = None
                data_f = None
                for col in row:
                    match = re.search(r'(\d{2})[^\d]*(\d{2})[^\d]*(\d{4}|\d{2})', str(col))
                    if match and len(str(col)) < 15:
                        dia, mes, ano = match.groups()
                        if len(ano) == 2: 
                            ano = "20" + ano if int(ano) < 30 else "19" + ano
                        try:
                            parsed = datetime.strptime(f"{dia}/{mes}/{ano}", '%d/%m/%Y')
                            data_f = parsed.strftime('%Y%m%d')
                            break
                        except:
                            pass
                            
                if not data_f:
                    erros.append(f"Linha {linha_num:04d} | PACIENTE: {nome_log.ljust(30)[:30]} | CPF: {cpf_log.ljust(14)} | MOTIVO: Data de Nascimento Invalida")
                    continue
                    
                sexo = ' '
                for col in row:
                    s = str(col).strip().upper()
                    if s == 'M' or s == 'F':
                        sexo = s
                        break
                
                nome = nome_log.ljust(30)[:30]
                
                endereco_raw = ""
                if len(row) > 9:
                    for col in row[9:]:
                        val = str(col).strip()
                        if len(val) > 8 and re.search(r'[A-Za-z]{3,}', val):
                            endereco_raw = val
                            break
                if not endereco_raw and len(row) > 11:
                    endereco_raw = str(row[11])
                
                rua_f, compl_f, num_f, bairro_f = parse_endereco_fixed(endereco_raw)
                
                telefone_f = "".ljust(11) 
                for col in reversed(row):
                    val = str(col).strip()
                    if not val or val == '-': continue
                    tel_digits = re.sub(r'\D', '', val)
                    
                    if 8 <= len(tel_digits) <= 11 and not re.search(r'[A-Za-z]{3,}', val):
                        if len(tel_digits) == 8 or len(tel_digits) == 9:
                            tel_digits = "84" + tel_digits 
                        if len(tel_digits) == 10 or len(tel_digits) == 11:
                            telefone_f = tel_digits.ljust(11)[:11]
                            break 
                
                line = f"{cns}{nome}{data_f}{sexo}{e_unidade}{f_folha}{g_seq}    {h_cep_rua}{rua_f}{compl_f}{num_f}{bairro_f}{telefone_f}"
                lines.append(line) 
                
        output_path = file_path.replace('.csv', '_FORMATADO_BPA.txt')
        log_path = file_path.replace('.csv', '_LOG_DE_ERROS.txt')
        
        with open(output_path, 'w', encoding='cp1252', errors='replace') as out_f:
            for line in lines:
                out_f.write(line + '\r\n')
                
        with open(log_path, 'w', encoding='utf-8', errors='replace') as log_f:
            log_f.write(f"Total formatado com sucesso: {len(lines)}\n")
            log_f.write(f"Total ignorado por erros: {len(erros)}\n\n")
            log_f.write("--- PACIENTES NAO FATURADOS ---\n")
            for e in erros:
                log_f.write(e + '\n')
        
        if len(lines) == 0:
            messagebox.showwarning("Aviso", "Nenhum registo salvo! Abra o arquivo LOG_DE_ERROS.txt para ver o motivo.")
        else:
            messagebox.showinfo("Sucesso!", f"Processamento Concluido!\n\nSalvos: {len(lines)}\nErros: {len(erros)}\n\nO BPA agora valida a matematica do SUS automaticamente!")

    # O bloco EXCEPT obrigatoriamente alinhado na mesma reta vertical do TRY lá em cima!
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro no processamento:\n{str(e)}")

if __name__ == "__main__":
    process_file()