# ==============================================================================
# 🚀 PROJETO: EXTRATOR DE CADASTRO BPA (DIRETO DO BANCO SQLITE)
# ==============================================================================
# Puxar pacientes do banco de dados (Tudo ou Mês Específico), garantir o formato
# dos dados e gerar o arquivo .txt com layout posicional exato para o BPA.
# REGRA 1: Sexo não reconhecido vira 'I' (Indefinido).
# REGRA 2: Data de nascimento inválida/vazia vira '19900101' (01/01/1990).
# ==============================================================================

import sqlite3
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# --- CONEXÃO COM O UTILS (Pasta Raiz) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents

# ==============================================================================
# MOTOR PRINCIPAL
# ==============================================================================
def exportar_dados():
    root = tk.Tk()
    root.withdraw()
    
    # 1. PERGUNTA AO USUÁRIO
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
        messagebox.showerror("Erro", f"Banco de dados não encontrado em:\n{caminho_banco}")
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
            messagebox.showinfo("Aviso", "Nenhum paciente encontrado para este filtro.")
            return

        # 4. VARIÁVEIS FIXAS DO BPA
        e_cbo = "240360"
        f_folha = "010"
        g_seq = "03"
        h_cns_prof = "59575000081"
        
        lines, erros = [], []

        # 5. PROCESSAMENTO
        for row in pacientes_db:
            # --- SUS ---
            raw_sus = str(row[0]).split('.')[0] if row[0] else ""
            cns = apenas_numeros(raw_sus)
            
            # --- NOME ---
            nome = remove_accents(str(row[1]) if row[1] else "NOME DESCONHECIDO").strip()
            
            # --- DATA DE NASCIMENTO (COM INJEÇÃO DE DATA PADRÃO) ---
            dn_raw = str(row[2]).strip() if row[2] else ""
            data_f = None
            
            if '-' in dn_raw:
                parts = dn_raw.split('-')
                if len(parts) >= 3: 
                    data_f = f"{parts[0][:4]}{parts[1][:2]}{parts[2][:2]}"
            elif '/' in dn_raw:
                parts = dn_raw.split('/')
                if len(parts) >= 3: 
                    data_f = f"{parts[2][:4]}{parts[1][:2]}{parts[0][:2]}"

            # SE A DATA NÃO EXISTIR OU FOR INVÁLIDA, COLOCA 01/01/1990
            if not data_f or len(data_f) != 8:
                data_f = "19900101"

            # --- SEXO (REGRA DO 'I') ---
            sexo_raw = str(row[3]).strip().upper() if row[3] else ""
            sexo_limpo = sexo_raw[:1]
            sexo = sexo_limpo if sexo_limpo in ['M', 'F'] else 'I'

            # --- ENDEREÇO ---
            rua_f = remove_accents(str(row[4] if row[4] else "")).strip().ljust(30)[:30]
            num_f = remove_accents(str(row[5] if row[5] else "")).strip().ljust(5)[:5]
            if not num_f.strip(): num_f = "S/N".ljust(5)
            bairro_f = remove_accents(str(row[6] if row[6] else "")).strip().ljust(30)[:30]
            
            # --- TELEFONE ---
            tel_digits = apenas_numeros(str(row[7]) if row[7] else "")
            telefone_f = "".ljust(11) 
            if 8 <= len(tel_digits) <= 11:
                if len(tel_digits) <= 9: tel_digits = "84" + tel_digits 
                telefone_f = tel_digits.ljust(11)[:11]

            # --- VALIDAÇÃO FINAL (AGORA SÓ BARRA SE O SUS ESTIVER ERRADO) ---
            if len(cns) != 15:
                erros.append(f"PACIENTE: {nome[:30]} | MOTIVO: SUS Inválido ou Ausente ({cns})")
                continue
            
            # --- MONTAGEM DA LINHA ---
            nome_f = nome.ljust(30)[:30]
            line = f"{cns}{nome_f}{data_f}{sexo}{e_cbo}{f_folha}{g_seq}    {h_cns_prof}{rua_f}          {num_f}{bairro_f}{telefone_f}"
            lines.append(line)

        # 6. SALVAMENTO E RELATÓRIO
        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt", 
            initialfile="BPA_EXPORTADO_SQLITE.txt",
            title="Onde quer salvar o arquivo BPA?"
        )
        
        if save_path:
            with open(save_path, 'w', encoding='cp1252', errors='replace') as out_f:
                for line in lines: out_f.write(line + '\r\n')
            
            if erros:
                with open(save_path.replace('.txt', '_ERROS.txt'), 'w', encoding='utf-8') as log_f:
                    log_f.write(f"--- RELATÓRIO DE EXPORTAÇÃO ---\n")
                    log_f.write(f"✅ Sucessos gerados: {len(lines)}\n")
                    log_f.write(f"❌ Erros barrados (Apenas SUS): {len(erros)}\n")
                    log_f.write(f"-------------------------------\n\n")
                    for e in erros: log_f.write(e + '\n')
            
            msg = f"Exportação concluída!\n\n✅ Pacientes salvos: {len(lines)}\n❌ Barrados (Sem SUS): {len(erros)}"
            messagebox.showinfo("Sucesso!", msg)

    except Exception as e:
        messagebox.showerror("Erro Grave", f"Erro durante a execução:\n{str(e)}")

if __name__ == "__main__":
    exportar_dados()