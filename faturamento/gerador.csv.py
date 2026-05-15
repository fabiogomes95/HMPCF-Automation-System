# ==============================================================================
# 🚀 GERADOR DE BPA - VERSÃO "PLANILHA ANTIGA" (RUA, NUMERO. BAIRRO)
# ==============================================================================
# Feito para ler o CSV antigo com as colunas: 
# REGISTRO, NOME, DN, IDADE, SEXO, RAÇA, CIDADE, HORARIO, CPF, SUS, OBS, ENDERECO, TEL
#
# REGRA DE ENDEREÇO: "R. EXEMPLO, 123. CENTRO"
# - Corta na 1ª vírgula para pegar a RUA
# - Corta no ponto (após a vírgula) para separar NÚMERO e BAIRRO
#
# REGRA DE DADOS:
# - Data vazia ou com erro -> Vira '19900101'
# - Sexo diferente de M/F -> Vira 'I'
# - SUS sem 15 dígitos -> Barra o paciente e joga no log de erros
# ==============================================================================

import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents

# ------------------------------------------------------------------------------
# ⚙️ MOTOR PRINCIPAL
# ------------------------------------------------------------------------------
def processar_csv_antigo():
    root = tk.Tk()
    root.withdraw() # Esconde a janela preta de fundo

    # 1. ESCOLHER O ARQUIVO CSV
    caminho_csv = filedialog.askopenfilename(
        title="Selecione o CSV das planilhas antigas",
        filetypes=[("Arquivos CSV", "*.csv")]
    )
    if not caminho_csv: return

    # 2. LER OS DADOS
    try:
        # on_bad_lines='skip' ajuda caso tenha muitas vírgulas no final vazadas
        df = pd.read_csv(caminho_csv, dtype=str, encoding='utf-8', on_bad_lines='skip')
    except:
        try:
            df = pd.read_csv(caminho_csv, dtype=str, encoding='latin1', on_bad_lines='skip')
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Erro ao ler o CSV:\n{e}")
            return

    # 3. VARIÁVEIS FIXAS
    e_cbo = "240360"           
    f_folha = "010"            
    g_seq = "03"               
    h_cns_prof = "59575000081" 

    linhas_bpa = []
    lista_erros = []

    # 4. PROCESSAMENTO LINHA A LINHA
    for index, row in df.iterrows():
        try:
            # Pular se as colunas principais estiverem totalmente vazias
            if len(row) < 13: continue 

            # --- NOME (Posição 1) ---
            nome_bruto = str(row.iloc[1]).strip()
            if nome_bruto.upper() in ['NAN', '']: continue 
            nome = remove_accents(nome_bruto)
            
            # --- SUS (Posição 9) - O FILTRO RIGOROSO ---
            raw_sus = str(row.iloc[9]).split('.')[0] 
            cns = apenas_numeros(raw_sus)
            
            if len(cns) != 15:
                lista_erros.append(f"LINHA {index + 2} | {nome[:30]} | ERRO: SUS ({cns}) incompleto ou ausente.")
                continue
                
            # --- DATA DE NASCIMENTO (Posição 2) - INJEÇÃO DE 1990 ---
            dn_raw = str(row.iloc[2]).strip()
            data_f = None
            
            if '-' in dn_raw: 
                parts = dn_raw.split('-')
                if len(parts) >= 3:
                    data_f = f"{parts[0][:4].zfill(4)}{parts[1][:2].zfill(2)}{parts[2][:2].zfill(2)}"
            elif '/' in dn_raw: 
                parts = dn_raw.split('/')
                if len(parts) >= 3:
                    data_f = f"{parts[2][:4].zfill(4)}{parts[1][:2].zfill(2)}{parts[0][:2].zfill(2)}"

            # Se a data estiver ruim, aplica o 01/01/1990
            if not data_f or len(data_f) != 8:
                data_f = "19900101"

            # --- SEXO (Posição 4) - REGRA DO 'I' ---
            sexo_raw = str(row.iloc[4]).strip().upper()
            sexo_limpo = sexo_raw[:1] 
            sexo = sexo_limpo if sexo_limpo in ['M', 'F'] else 'I'

            # ------------------------------------------------------------------
            # ✂️ FATIANDO O ENDEREÇO (Posição 11) -> "RUA, NUMERO. BAIRRO"
            # ------------------------------------------------------------------
            endereco_raw = str(row.iloc[11]).strip()
            if endereco_raw.upper() == "NAN": endereco_raw = ""
            
            rua = ""
            numero = "S/N"
            bairro = str(row.iloc[6]).strip() # Cidade como backup (Posição 6)
            if bairro.upper() == "NAN": bairro = ""

            if endereco_raw:
                if ',' in endereco_raw:
                    # Corta na PRIMEIRA vírgula para separar a RUA do resto
                    partes_virgula = endereco_raw.split(',', 1) 
                    rua = partes_virgula[0].strip()
                    resto = partes_virgula[1].strip()
                    
                    # Agora verifica se tem PONTO no resto para separar NUMERO e BAIRRO
                    if '.' in resto:
                        partes_ponto = resto.split('.', 1)
                        numero = partes_ponto[0].strip()
                        bairro_extraido = partes_ponto[1].strip()
                        if bairro_extraido: # Só substitui se o bairro não estiver vazio
                            bairro = bairro_extraido
                    else:
                        numero = resto # Se não tem ponto, assume que sobrou só o número
                else:
                    rua = endereco_raw # Sem vírgula, tudo vira rua

            # Formatando para os espaços rígidos do BPA
            rua_f = remove_accents(rua).ljust(30)[:30]
            num_f = remove_accents(numero).ljust(5)[:5]
            if not num_f.strip(): num_f = "S/N".ljust(5)
            bairro_f = remove_accents(bairro).ljust(30)[:30]
            
            # --- TELEFONE (Posição 12) ---
            tel_digits = apenas_numeros(str(row.iloc[12]))
            telefone_f = "".ljust(11) 
            if 8 <= len(tel_digits) <= 11:
                if len(tel_digits) <= 9: 
                    tel_digits = "84" + tel_digits 
                telefone_f = tel_digits.ljust(11)[:11]

            # --------------------------------------------------------------------------
            # 🏗️ MONTANDO A LINHA
            # --------------------------------------------------------------------------
            nome_f = nome.ljust(30)[:30]
            line = f"{cns}{nome_f}{data_f}{sexo}{e_cbo}{f_folha}{g_seq}    {h_cns_prof}{rua_f}          {num_f}{bairro_f}{telefone_f}"
            
            linhas_bpa.append(line)
            
        except Exception as e_linha:
            lista_erros.append(f"LINHA {index + 2} | ERRO INESPERADO: {e_linha}")

    # 5. SALVAMENTO E RELATÓRIO
    save_path = filedialog.asksaveasfilename(
        defaultextension=".txt", 
        initialfile="BPA_PLANILHA_ANTIGA.txt",
        title="Salvar arquivo do BPA (Planilhas Antigas)"
    )
    
    if save_path:
        # Salva o arquivo de importação
        with open(save_path, 'w', encoding='cp1252', errors='replace') as out_f:
            for linha in linhas_bpa: 
                out_f.write(linha + '\n')
        
        # Gera o log de pacientes barrados (se houver)
        if lista_erros:
            arquivo_erros = save_path.replace('.txt', '_PACIENTES_SEM_CADASTRO.txt')
            with open(arquivo_erros, 'w', encoding='utf-8') as log_f:
                log_f.write(f"--- RELATÓRIO DE PACIENTES BARRADOS (PLANILHA ANTIGA) ---\n")
                log_f.write(f"Total Sucessos: {len(linhas_bpa)}\n")
                log_f.write(f"Total Barrados: {len(lista_erros)}\n")
                log_f.write(f"----------------------------------------------------------\n\n")
                for e in lista_erros: 
                    log_f.write(e + '\n')
    
        # Pop-up final
        mensagem_final = f"Conversão Finalizada! (Planilhas Antigas)\n\n"
        mensagem_final += f"✅ Pacientes no BPA: {len(linhas_bpa)}\n"
        mensagem_final += f"❌ Barrados (Sem SUS): {len(lista_erros)}\n\n"
        
        if len(lista_erros) > 0:
            mensagem_final += "Foi criado o arquivo '_PACIENTES_SEM_CADASTRO.txt' detalhando quem ficou de fora."

        messagebox.showinfo("Resumo da Geração", mensagem_final)

if __name__ == "__main__":
    processar_csv_antigo()