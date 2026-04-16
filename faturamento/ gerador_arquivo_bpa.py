# ==============================================================================
# PROJETO: Extrator de Cadastro BPA (Direto do Banco SQLite)
# OBJETIVO: Puxar pacientes do banco de dados (Tudo ou Mês Específico), validar
#           o CNS e gerar o arquivo .txt com layout posicional exato para o BPA.
# ==============================================================================

import sqlite3
import re
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# --- CONEXÃO COM O UTILS (Pasta Raiz) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents, valida_cns

# --- MOTOR PRINCIPAL ---

def exportar_dados():
    root = tk.Tk()
    root.withdraw()
    
    # 1. PERGUNTA AO USUÁRIO: Tudo ou Mês Específico?
    mes_ano = simpledialog.askstring(
        "Filtro de Exportação", 
        "Digite o mês e ano desejados (ex: 03/2026)\n\nOu deixe VAZIO e clique OK para exportar TODA a base de dados:"
    )
    
    if mes_ano is None: return
    mes_ano = mes_ano.strip()

    # 2. LOCALIZAR O BANCO DE DADOS
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(pasta_script, '..', 'hospital.db')
    
    if not os.path.exists(caminho_banco):
        messagebox.showerror("Erro", f"Banco de dados não encontrado!")
        return

    try:
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()

        # 3. CONSTRUIR A BUSCA (SQL)
        query = """
            SELECT DISTINCT p.sus, p.nome, p.dn, p.sexo, p.endereco, p.numero, p.bairro, p.tel
            FROM pacientes p
        """
        params = []
        
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
            messagebox.showinfo("Aviso", "Nenhum paciente encontrado.")
            return

        # 4. VARIÁVEIS FIXAS DO BPA
        e_cbo = "240360"
        f_folha = "010"
        g_seq = "03"
        h_cns_prof = "59575000081"
        
        lines, erros = [], []

        # 5. PROCESSAMENTO E FORMATAÇÃO POSICIONAL
        for row in pacientes_db:
            # CNS (Usa apenas_numeros do utils)
            cns = apenas_numeros(row[0])
            
            # Nome (Usa remove_accents do utils)
            nome = remove_accents(str(row[1]) if row[1] else "NOME DESCONHECIDO").strip()
            
            # Formatação de Data
            dn_raw = str(row[2]).strip() if row[2] else ""
            data_f = None
            if len(dn_raw) >= 10:
                parts = dn_raw.split('-') if '-' in dn_raw else dn_raw.split('/')
                if '-' in dn_raw:
                    data_f = f"{parts[0]}{parts[1]}{parts[2][:2]}"
                else:
                    data_f = f"{parts[2][:4]}{parts[1]}{parts[0]}"

            sexo = str(row[3]).strip().upper() if row[3] in ['M', 'F'] else ' '

            # Endereço (Tudo padronizado pelo utils)
            rua_f = remove_accents(str(row[4])).strip().ljust(30)[:30]
            num_f = str(row[5]).strip().ljust(5)[:5] if row[5] else "S/N".ljust(5)
            bairro_f = remove_accents(str(row[6])).strip().ljust(30)[:30]
            
            # Telefone
            tel_digits = apenas_numeros(row[7])
            telefone_f = "".ljust(11) 
            if 8 <= len(tel_digits) <= 11:
                if len(tel_digits) <= 9: tel_digits = "84" + tel_digits 
                telefone_f = tel_digits.ljust(11)[:11]

            # --- VALIDAÇÕES (Usando valida_cns do utils) ---
            if not cns or not valida_cns(cns):
                erros.append(f"PACIENTE: {nome[:30]} | MOTIVO: SUS Invalido ({cns})")
                continue
                
            if not data_f or len(data_f) != 8:
                erros.append(f"PACIENTE: {nome[:30]} | MOTIVO: Data Invalida")
                continue
            
            # MONTAGEM DA LINHA (Layout Posicional SUS)
            nome_f = nome.ljust(30)[:30]
            line = f"{cns}{nome_f}{data_f}{sexo}{e_cbo}{f_folha}{g_seq}    {h_cns_prof}{rua_f}          {num_f}{bairro_f}{telefone_f}"
            lines.append(line)

        # 6. SALVAMENTO
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="BPA_EXPORTADO.txt")
        if save_path:
            with open(save_path, 'w', encoding='cp1252', errors='replace') as out_f:
                for line in lines: out_f.write(line + '\r\n')
            
            # Log de erros para você saber quem ficou de fora
            with open(save_path.replace('.txt', '_ERROS.txt'), 'w', encoding='utf-8') as log_f:
                log_f.write(f"Sucessos: {len(lines)}\nErros: {len(erros)}\n\n")
                for e in erros: log_f.write(e + '\n')
        
            messagebox.showinfo("Sucesso!", f"Exportado com sucesso!\nSalvos: {len(lines)}\nErros: {len(erros)}")

    except Exception as e:
        messagebox.showerror("Erro Grave", str(e))

if __name__ == "__main__":
    exportar_dados()