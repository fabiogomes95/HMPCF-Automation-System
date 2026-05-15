# ==============================================================================
# 🚀 INTEGRADOR DEFINITIVO: SQLITE (hospital.db) -> FIREBIRD (.GDB)
# ==============================================================================
# Puxa os dados limpos do seu banco local, verifica se o paciente já existe no BPA 
# (via Nome e Data de Nasc) e faz a atualização (UPDATE) ou criação (INSERT).
# ==============================================================================

import sqlite3
import firebirdsql
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, remove_accents

# ------------------------------------------------------------------------------
# ⚙️ MOTOR DE INTEGRAÇÃO
# ------------------------------------------------------------------------------
def sincronizar_sqlite_para_gdb():
    root = tk.Tk()
    root.withdraw()

    # 1. FILTRO DE MÊS (Opcional)
    mes_ano = simpledialog.askstring(
        "Filtro de Exportação", 
        "Digite o mês e ano desejados (ex: 03/2026)\n\nOu deixe VAZIO e clique OK para sincronizar TODA a base de dados:"
    )
    if mes_ano is None: return
    mes_ano = mes_ano.strip()

    # 2. LOCALIZAR O BANCO SQLITE (hospital.db)
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    caminho_sqlite = os.path.join(pasta_script, '..', 'hospital.db')
    
    # Se não achar na pasta raiz, pede para você selecionar manualmente
    if not os.path.exists(caminho_sqlite):
        caminho_sqlite = 'hospital.db'
        if not os.path.exists(caminho_sqlite):
            caminho_sqlite = filedialog.askopenfilename(title="Selecione o arquivo hospital.db", filetypes=[("Banco SQLite", "*.db *.sqlite")])
            if not caminho_sqlite: return

    # 3. SELECIONAR O BANCO FIREBIRD (.GDB)
    caminho_gdb = filedialog.askopenfilename(title="Selecione a base de dados (.gdb) do BPA", filetypes=[("Banco Firebird", "*.gdb *.fdb")])
    if not caminho_gdb: return

    # 4. BUSCAR DADOS NO SQLITE
    try:
        conn_sq = sqlite3.connect(caminho_sqlite)
        conn_sq.row_factory = sqlite3.Row
        cursor_sq = conn_sq.cursor()

        query = "SELECT DISTINCT p.* FROM pacientes p"
        params = []
        
        # Filtro de data baseado nos atendimentos (mesma lógica do seu outro script)
        if mes_ano:
            query += " JOIN atendimentos a ON p.sus = a.sus WHERE a.data_atendimento LIKE ? OR a.data_atendimento LIKE ?"
            parts = mes_ano.split('/')
            if len(parts) == 2:
                mm, yyyy = parts
                params.extend([f"%{mm}/{yyyy}%", f"%{yyyy}-{mm}%"])
            else:
                params.extend([f"%{mes_ano}%", f"%{mes_ano}%"])
                
        cursor_sq.execute(query, params)
        pacientes_db = cursor_sq.fetchall()
        conn_sq.close()
        
        if not pacientes_db:
            messagebox.showinfo("Aviso", "Nenhum paciente encontrado para este filtro no hospital.db.")
            return
    except Exception as e:
        messagebox.showerror("Erro no SQLite", f"Falha ao ler hospital.db:\n{e}")
        return

    # 5. CONECTAR AO FIREBIRD
    try:
        conexao_fb = firebirdsql.connect(
            host='localhost', 
            database=caminho_gdb,
            user='SYSDBA', 
            password='masterkey', 
            charset='WIN1252'
        )
        cursor_fb = conexao_fb.cursor()
    except Exception as e:
        messagebox.showerror("Erro de Ligação", f"Não foi possível conectar ao .gdb:\n{e}")
        return

    sucessos_upd = 0
    sucessos_ins = 0
    erros = 0
    lista_erros = []

    # 6. PROCESSAR E INTEGRAR
    for p in pacientes_db:
        try:
            # --- NOME ---
            nome = remove_accents(p['nome'])[:30].strip()
            if not nome or nome == 'NAN': continue

            # --- CPF E SUS ---
            cpf = apenas_numeros(p['cpf'])[:11] if 'cpf' in p.keys() and p['cpf'] else ""
            sus = apenas_numeros(p['sus'])[:15] if 'sus' in p.keys() and p['sus'] else ""

            # --- DATA DE NASCIMENTO (Injeção de 1990) ---
            dn_raw = str(p['dn']).strip() if 'dn' in p.keys() and p['dn'] else ""
            dt_nasc = '19900101'
            if '-' in dn_raw:
                parts = dn_raw.split('-')
                if len(parts) >= 3: dt_nasc = f"{parts[0][:4].zfill(4)}{parts[1][:2].zfill(2)}{parts[2][:2].zfill(2)}"
            elif '/' in dn_raw:
                parts = dn_raw.split('/')
                if len(parts) >= 3: dt_nasc = f"{parts[2][:4].zfill(4)}{parts[1][:2].zfill(2)}{parts[0][:2].zfill(2)}"
            if len(dt_nasc) != 8: dt_nasc = '19900101'

            # --- SEXO (Regra do I) ---
            sexo_raw = str(p['sexo']).strip().upper() if 'sexo' in p.keys() and p['sexo'] else ""
            sexo = sexo_raw[:1] if sexo_raw in ['M', 'F'] else 'I'

            # --- ENDEREÇO (Puxando direto das colunas limpas do banco) ---
            rua = remove_accents(p['endereco'])[:25] if 'endereco' in p.keys() and p['endereco'] else ""
            numero = remove_accents(p['numero'])[:5] if 'numero' in p.keys() and p['numero'] else "S/N"
            bairro = remove_accents(p['bairro'])[:15] if 'bairro' in p.keys() and p['bairro'] else ""

            # --- TELEFONE ---
            tel_full = apenas_numeros(p['tel']) if 'tel' in p.keys() and p['tel'] else ""
            if len(tel_full) <= 9 and tel_full: tel_full = "84" + tel_full
            ddd = tel_full[:2] if len(tel_full) >= 10 else ''
            tel = tel_full[-8:] if len(tel_full) >= 8 else tel_full

            co_lograd = "081"

            # ------------------------------------------------------------------
            # 🏗️ CHAVE COMPOSTA (NOME + DATA): UPDATE OU INSERT NO FIREBIRD
            # ------------------------------------------------------------------
            cursor_fb.execute("SELECT NOME FROM CADCNS WHERE NOME = ? AND DTNASC = ?", (nome, dt_nasc))
            reg = cursor_fb.fetchone()

            if reg:
                # O paciente já existe: Atualiza morada, telefone, cpf e sus
                sql_up = """
                    UPDATE CADCNS SET 
                        NUM_CPF = ?, LOGPCN = ?, NUMPCN = ?, BAIRRO_PCNTE = ?, 
                        DDTEL_PCNTE = ?, TEL_PCNTE = ?, CNS = ?, CO_LOGRAD = ?
                    WHERE NOME = ? AND DTNASC = ?
                """
                cursor_fb.execute(sql_up, (cpf, rua, numero, bairro, ddd, tel, sus, co_lograd, nome, dt_nasc))
                sucessos_upd += 1
            else:
                # O paciente é novo: Cria um registro completo de raiz
                sql_in = """
                    INSERT INTO CADCNS (
                        CNS, NOME, NUM_CPF, DTNASC, SEXO, RACA, LOGPCN, 
                        NUMPCN, BAIRRO_PCNTE, CEPPCN, IBGE, DDTEL_PCNTE, TEL_PCNTE, CO_LOGRAD
                    ) VALUES (?, ?, ?, ?, ?, '03', ?, ?, ?, '59575000', '240360', ?, ?, ?)
                """
                cursor_fb.execute(sql_in, (sus, nome, cpf, dt_nasc, sexo, rua, numero, bairro, ddd, tel, co_lograd))
                sucessos_ins += 1

        except Exception as e_linha:
            erros += 1
            lista_erros.append(f"Erro no paciente {p['nome']}: {str(e_linha)}")

    # 7. FINALIZAÇÃO
    conexao_fb.commit()
    conexao_fb.close()
    
    # Relatório Final
    msg = f"Sincronização Concluída!\n\n"
    msg += f"🔄 Pacientes Atualizados: {sucessos_upd}\n"
    msg += f"🆕 Novos Cadastros (Inseridos): {sucessos_ins}\n"
    msg += f"❌ Erros Residuais: {erros}\n\n"
    
    if erros > 0:
        with open("log_erros_sqlite_para_gdb.txt", "w", encoding="utf-8") as f:
            f.write("ERROS ENCONTRADOS DURANTE A INTEGRAÇÃO:\n\n")
            f.write("\n".join(lista_erros))
        msg += "Foi gerado o arquivo 'log_erros_sqlite_para_gdb.txt' detalhando as falhas."

    messagebox.showinfo("Sucesso", msg)

if __name__ == "__main__":
    sincronizar_sqlite_para_gdb()