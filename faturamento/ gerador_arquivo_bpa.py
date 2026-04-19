# ==============================================================================
# PROJETO: EXTRATOR DE CADASTRO BPA (DIRETO DO BANCO SQLITE)
# ==============================================================================
# OBJETIVO: 
# Puxar pacientes do banco de dados, aplicar as regras do Ministério da Saúde 
# e gerar um arquivo .txt com "Layout Posicional" exato, onde cada caractere
# tem seu lugar obrigatório (A forma antiquada, porém obrigatória, do Governo).
# ==============================================================================

import sqlite3
import re
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# --- CONEXÃO COM O UTILS (Pasta Raiz) ---
# Adiciona a pasta pai ao caminho para poder importar o limpador e validador.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents, valida_cns

def exportar_dados():
    # Oculta a janela preta principal do Tkinter para mostrar só o Pop-up bonitinho
    root = tk.Tk()
    root.withdraw()
    
    # ==========================================================================
    # 1. INTERAÇÃO E REGRAS DE BUSCA
    # ==========================================================================
    mes_ano = simpledialog.askstring(
        "Filtro de Exportação",
        "Digite o mês e ano desejados (ex: 03/2026)\n\nOu deixe VAZIO e clique OK para exportar TODA a base:"
    )
    if mes_ano is None: return # Se o usuário clicar em Cancelar
    mes_ano = mes_ano.strip()

    pasta_script = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(pasta_script, '..', 'hospital.db')
    
    if not os.path.exists(caminho_banco):
        messagebox.showerror("Erro", f"Banco de dados não encontrado!")
        return

    # ==========================================================================
    # 2. CONEXÃO E CONSULTA SQL DINÂMICA
    # ==========================================================================
    try:
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()
        
        # A Query Mestra de Exportação (Seleciona pacientes únicos pelo SUS)
        query = """
        SELECT DISTINCT p.sus, p.nome, p.dn, p.sexo, p.endereco, p.numero, p.bairro, p.tel
        FROM pacientes p
        """
        params = []
        
        # Se ele digitou um mês, junta a tabela de pacientes com a de atendimentos
        if mes_ano:
            query += """
            JOIN atendimentos a ON p.sus = a.sus
            WHERE a.data_atendimento LIKE ? OR a.data_atendimento LIKE ?
            """
            parts = mes_ano.split('/')
            if len(parts) == 2:
                mm, yyyy = parts
                params.extend([f"%{mm}/{yyyy}%", f"%{yyyy}-{mm}%"])
            else:
                params.extend([f"%{mes_ano}%", f"%{mes_ano}%"])
                
        cursor.execute(query, params)
        pacientes_db = cursor.fetchall()
        conn.close()
        
        if not pacientes_db:
            messagebox.showinfo("Aviso", "Nenhum paciente encontrado para esse período.")
            return

        # ==========================================================================
        # 3. VARIÁVEIS FIXAS EXIGIDAS PELO GOVERNO (CABECALHO DO LAYOUT BPA)
        # ==========================================================================
        e_cbo = "240360"
        f_folha = "010"
        g_seq = "03"
        h_cns_prof = "59575000081"
        lines, erros = [], []

        # ==========================================================================
        # 4. PROCESSAMENTO E FORMATAÇÃO POSICIONAL (DATA MAPPING)
        # ==========================================================================
        for row in pacientes_db:
            cns = apenas_numeros(row)
            nome = remove_accents(str(row[1]) if row[1] else "NOME DESCONHECIDO").strip()
            
            # --- Tratamento Espacial de Data (Transformando DD/MM/AAAA para AAAAMMDD) ---
            dn_raw = str(row[2]).strip() if row[2] else ""
            data_f = None
            if len(dn_raw) >= 10:
                parts = dn_raw.split('-') if '-' in dn_raw else dn_raw.split('/')
                if '-' in dn_raw:
                    data_f = f"{parts}{parts[1]}{parts[2][:2]}"
                else:
                    data_f = f"{parts[2][:4]}{parts[1]}{parts}"
            
            sexo = str(row[3]).strip().upper() if row[3] in ['M', 'F'] else ' '
            
            # --- O Pulo do Gato (Ljust): Se o nome tem 10 letras, ljust(30) bota 20 espaços em branco.
            # Isso impede que as colunas se desmontem no arquivo TXT do Governo! ---
            rua_f = remove_accents(str(row[4])).strip().ljust(30)[:30]
            num_f = str(row[5]).strip().ljust(5)[:5] if row[5] else "S/N".ljust(5)
            bairro_f = remove_accents(str(row[6])).strip().ljust(30)[:30]
            
            # Tratamento de Telefone
            tel_digits = apenas_numeros(row[7])
            telefone_f = "".ljust(11)
            if 8 <= len(tel_digits) <= 11:
                if len(tel_digits) <= 9: tel_digits = "84" + tel_digits
                telefone_f = tel_digits.ljust(11)[:11]

            # --- PREVENÇÃO DE GLOSA (Erro de Faturamento) ---
            if not cns or not valida_cns(cns):
                erros.append(f"PACIENTE: {nome[:30]} | MOTIVO: SUS Invalido ({cns})")
                continue
                
            if not data_f or len(data_f) != 8:
                erros.append(f"PACIENTE: {nome[:30]} | MOTIVO: Data Invalida")
                continue

            # Montagem final do Bloco como se fosse um quebra-cabeça posicional!
            nome_f = nome.ljust(30)[:30]
            line = f"{cns}{nome_f}{data_f}{sexo}{e_cbo}{f_folha}{g_seq}{h_cns_prof}{rua_f}          {num_f}{bairro_f}{telefone_f}"
            lines.append(line)

        # ==========================================================================
        # 5. EXPORTAÇÃO E LOG DE AUDITORIA
        # ==========================================================================
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="BPA_EXPORTADO.txt")
        if save_path:
            # cp1252 é o formato de codificação aceito pelos programas em Delphi do MS.
            with open(save_path, 'w', encoding='cp1252', errors='replace') as out_f:
                for line in lines: 
                    out_f.write(line + '\r\n')
                    
            # Gera um Log paralelo para a gestão saber quem o arquivo jogou fora.
            with open(save_path.replace('.txt', '_ERROS.txt'), 'w', encoding='utf-8') as log_f:
                log_f.write(f"Sucessos: {len(lines)}\nErros: {len(erros)}\n\n")
                for e in erros: 
                    log_f.write(e + '\n')
                    
            messagebox.showinfo("Sucesso!", f"Exportado com sucesso!\nSalvos: {len(lines)}\nErros: {len(erros)}")
            
    except Exception as e:
        messagebox.showerror("Erro Grave", str(e))

if __name__ == "__main__":
    exportar_dados()
