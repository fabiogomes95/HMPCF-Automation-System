# ==============================================================================
# PROJETO: SINCRONIZADOR BPA E CONTINGÊNCIA
# ==============================================================================
# OBJETIVO: 
# Quando a energia ou a internet cai, as recepcionistas anotam no Excel. 
# Esse script lê planilhas manuais super bagunçadas, "caça" os documentos no 
# meio dos textos e insere tudo no banco de dados de forma cirúrgica.
# ==============================================================================

import csv
import re
import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import sys

# Garante acesso ao utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents, parse_endereco_fixed, valida_cns

def sincronizar_contingencia():
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(title="Selecionar Planilha Manual", filetypes=[("CSV", "*.csv")])
    if not file_path: return
    
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(pasta_script, '..', 'hospital.db')
    
    try:
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()
        
        # Mapeamento prévio: Guarda quem já está no banco para evitar duplicações.
        cursor.execute("SELECT cpf, sus FROM pacientes")
        mapa_banco = {apenas_numeros(row): (row, apenas_numeros(row[1])) for row in cursor.fetchall() if row}
        
        adicionados, atualizados, ignorados = 0, 0, 0
        processados_log, erros_log = [], []

        # Inteligência Artificial do Delimitador: Descobre se o Excel usou Vírgula ou Ponto e Vírgula
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            content = f.read(1024)
            separador = ';' if content.count(';') > content.count(',') else ','

        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            reader = csv.reader(f, delimiter=separador)
            
            for i, row in enumerate(reader):
                linha_num = i + 1
                if len(row) < 5: continue
                
                # ==============================================================
                # EXPRESSÕES REGULARES: OS CAÇADORES DE DADOS (DATA MINING)
                # ==============================================================
                # CAÇADOR DE NOME: Procura textos longos ignorando palavras que costumam ser cabeçalho
                nome_raw = next((c for c in row if len(c) > 5 and not re.search(r'\d', c) and c.upper() not in ["EXTREMOZ", "PACIENTE", "NOME", "REGISTRO"]), "")
                if not nome_raw: continue
                
                # CAÇADOR DE CPF E SUS: Ignora a coluna que foi digitada e busca pela estrutura matemática
                cpf_plan = apenas_numeros(next((re.search(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}', c).group(0) for c in row if re.search(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}', c)), ""))
                sus_plan = apenas_numeros(next((c for c in row if len(apenas_numeros(c)) == 15 and apenas_numeros(c) in '12789'), ""))
                
                id_paciente = f"NOME: {nome_raw[:30].ljust(30)} | CPF: {cpf_plan.ljust(11)}"
                if not cpf_plan and not sus_plan: continue

                # ==============================================================
                # LÓGICA DE DECISÃO BIFURCADA
                # ==============================================================
                # Cenario 1: Já existe no Banco? (Foca em atualizar)
                if cpf_plan in mapa_banco:
                    cpf_orig_banco, sus_banco_limpo = mapa_banco[cpf_plan]
                    
                    # Se o SUS antigo do banco está corrompido, a gente insere o novo da planilha
                    if len(sus_banco_limpo) < 15:
                        if valida_cns(sus_plan):
                            cursor.execute("UPDATE pacientes SET sus = ? WHERE cpf = ?", (sus_plan, cpf_orig_banco))
                            atualizados += 1
                            processados_log.append(f"[ATUALIZADO] {id_paciente} | NOVO SUS: {sus_plan}")
                        else:
                            erros_log.append(f"Linha {linha_num:04d} | {id_paciente} | MOTIVO: SUS Inválido ({sus_plan})")
                    else:
                        ignorados += 1 # O Banco já tinha um SUS perfeito
                    continue

                # Cenario 2: É Novo Cadastro!
                if not valida_cns(sus_plan):
                    erros_log.append(f"Linha {linha_num:04d} | {id_paciente} | MOTIVO: SUS Inválido para novo cadastro")
                    continue
                
                # CAÇADOR DE DATA DE NASCIMENTO
                data_banco = ""
                for col in row:
                    m = re.search(r'(\d{2})[^\d]*(\d{2})[^\d]*(\d{4}|\d{2})', col)
                    if m and len(col) < 15:
                        dia, mes, ano = m.groups()
                        # Se digitou apenas '99' ou '02', o código adivinha se é 1999 ou 2002
                        if len(ano) == 2: ano = "20" + ano if int(ano) < 30 else "19" + ano
                        data_banco = f"{ano}-{mes}-{dia}"; break
                        
                if not data_banco:
                    erros_log.append(f"Linha {linha_num:04d} | {id_paciente} | MOTIVO: Data de Nascimento não encontrada")
                    continue
                    
                rua, num, bairro = parse_endereco_fixed(row[-1] if len(row) > 5 else "")
                
                # INSERT OR REPLACE impede que o banco bloqueie em caso de pequenos conflitos internos
                cursor.execute('''
                    INSERT OR REPLACE INTO pacientes (cpf, sus, nome, dn, sexo, raca, endereco, numero, bairro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cpf_plan, sus_plan, remove_accents(nome_raw), data_banco, " ", "PARDA", rua, num, bairro))
                
                adicionados += 1
                processados_log.append(f"[NOVO]       {id_paciente} | SUS: {sus_plan}")

        conn.commit()
        conn.close()

        # ======================================================================
        # GERADOR DE LOGS DE AUDITORIA (TXT)
        # ======================================================================
        pasta_planilha = os.path.dirname(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # O Arquivo de Sucesso
        if processados_log:
            with open(os.path.join(pasta_planilha, f"PROCESSADOS_{timestamp}.txt"), 'w', encoding='utf-8') as f:
                f.write(f"--- PACIENTES PROCESSADOS COM SUCESSO ---\n\n")
                for item in processados_log: f.write(item + "\n")
                
        # O Arquivo de Erro (A Lista de Tarefas das Recepcionistas)
        if erros_log:
            with open(os.path.join(pasta_planilha, f"ERROS_SINCRONIZACAO_{timestamp}.txt"), 'w', encoding='utf-8') as f:
                f.write(f"--- PACIENTES COM ERRO (CORRIGIR NA PLANILHA) ---\n\n")
                for item in erros_log: f.write(item + "\n")

        msg = f"Sincronização Finalizada!\n\n📈 Novos: {adicionados}\n🔄 Atualizados: {atualizados}\n🛡 Já OK: {ignorados}"
        if erros_log:
            msg += f"\n\n⚠ Atenção: {len(erros_log)} erros encontrados. Verifique o arquivo de ERROS."
        messagebox.showinfo("Sucesso", msg)

    except Exception as e:
        messagebox.showerror("Erro Grave", f"Erro no banco: {e}")

if __name__ == "__main__":
    sincronizar_contingencia()