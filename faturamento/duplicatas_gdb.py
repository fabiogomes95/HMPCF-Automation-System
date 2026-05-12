# ==============================================================================
# 🧹 FAXINA DE DUPLICADOS DIRETO NO FIREBIRD (BPAMAG.GDB) - ANTI-CORRUPÇÃO
# ==============================================================================

import firebirdsql
import tkinter as tk
from tkinter import filedialog, messagebox

def limpar_duplicados_gdb():
    root = tk.Tk()
    root.withdraw() 

    # 1. SELECIONAR O BANCO FIREBIRD (.GDB)
    caminho_gdb = filedialog.askopenfilename(
        title="Selecione o arquivo do banco BPA (.gdb)", 
        filetypes=[("Banco Firebird", "*.gdb *.fdb")]
    )
    if not caminho_gdb: return

    try:
        # 2. CONEXÃO COM O FIREBIRD (Agora imune a caracteres corrompidos)
        conexao = firebirdsql.connect(
            host='localhost', 
            database=caminho_gdb,
            user='SYSDBA', 
            password='masterkey', 
            charset='ISO8859_1' # <-- A MÁGICA ACONTECE AQUI
        )
        cursor = conexao.cursor()

        # 3. PUXAR TODOS OS PACIENTES COM SUS
        query = """
            SELECT RDB$DB_KEY, CNS, NUM_CPF, LOGPCN, TEL_PCNTE 
            FROM CADCNS 
            WHERE CNS IS NOT NULL
        """
        cursor.execute(query)
        pacientes = cursor.fetchall()

        # 4. AGRUPAR PACIENTES PELO NÚMERO DO SUS
        agrupados_por_sus = {}
        for p in pacientes:
            db_key = p[0]
            sus_limpo = str(p[1]).strip() if p[1] else ""
            
            if not sus_limpo:
                continue
            
            ficha = {
                'db_key': db_key,
                'sus': sus_limpo,
                'cpf': str(p[2]).strip() if p[2] else "",
                'endereco': str(p[3]).strip() if p[3] else "",
                'tel': str(p[4]).strip() if p[4] else ""
            }
            
            if sus_limpo not in agrupados_por_sus:
                agrupados_por_sus[sus_limpo] = []
            agrupados_por_sus[sus_limpo].append(ficha)

        ids_para_deletar = []
        pacientes_arrumados = 0

        # 5. AVALIAR OS DUPLICADOS E ESCOLHER O VENCEDOR
        for sus, lista_fichas in agrupados_por_sus.items():
            if len(lista_fichas) > 1: 
                pacientes_arrumados += 1
                
                def calcular_pontuacao(ficha):
                    pontos = 0
                    if ficha['cpf'] and len(ficha['cpf']) >= 11: pontos += 5
                    if ficha['endereco']: pontos += 1
                    if ficha['tel']: pontos += 1
                    return pontos

                lista_ordenada = sorted(lista_fichas, key=calcular_pontuacao, reverse=True)
                
                for ficha_perdedora in lista_ordenada[1:]:
                    ids_para_deletar.append(ficha_perdedora['db_key'])

        # 6. EXECUTAR A LIMPEZA NO BANCO
        if ids_para_deletar:
            for db_key in ids_para_deletar:
                cursor.execute("DELETE FROM CADCNS WHERE RDB$DB_KEY = ?", (db_key,))
            
            conexao.commit() 
            
            msg = f"Faxina Concluída com Sucesso no BPA!\n\n"
            msg += f"✅ Pacientes com duplicidade: {pacientes_arrumados}\n"
            msg += f"🗑️ Cadastros removidos: {len(ids_para_deletar)}\n\n"
            messagebox.showinfo("Limpeza Finalizada", msg)
        else:
            messagebox.showinfo("Tudo Limpo!", "Nenhum SUS duplicado foi encontrado!")

    except Exception as e:
        messagebox.showerror("Erro de Execução", f"Ocorreu um erro durante a conexão/limpeza:\n{e}")
    finally:
        if 'conexao' in locals():
            conexao.close()

if __name__ == "__main__":
    limpar_duplicados_gdb()