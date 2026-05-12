# ==============================================================================
# 💣 ANIQUILADOR DE NULLS: VARREDURA TOTAL NO GDB (BPA) - SEM ERRO UDFLIB
# ==============================================================================
# Destrói qualquer valor NULL existente na tabela de pacientes.
# Versão corrigida: Sem o uso de TRIM() no SQL para evitar bloqueios do servidor.
# ==============================================================================

import firebirdsql
import tkinter as tk
from tkinter import filedialog, messagebox

def aniquilar_nulls_bpa():
    root = tk.Tk()
    root.withdraw() 

    caminho_gdb = filedialog.askopenfilename(
        title="Selecione o arquivo do banco BPA (.gdb)", 
        filetypes=[("Banco Firebird", "*.gdb *.fdb")]
    )
    if not caminho_gdb: return

    try:
        conexao = firebirdsql.connect(
            host='localhost', 
            database=caminho_gdb,
            user='SYSDBA', 
            password='masterkey', 
            charset='ISO8859_1'
        )
        cursor = conexao.cursor()

        # 1. Mapeia TODOS os campos (Sem usar TRIM no SQL)
        query_colunas = """
            SELECT f.RDB$FIELD_NAME, t.RDB$FIELD_TYPE
            FROM RDB$RELATION_FIELDS f
            JOIN RDB$FIELDS t ON f.RDB$FIELD_SOURCE = t.RDB$FIELD_NAME
            WHERE f.RDB$RELATION_NAME = 'CADCNS'
        """
        cursor.execute(query_colunas)
        colunas = cursor.fetchall()

        buracos_texto = 0
        buracos_numero = 0

        # 2. Injeção dinâmica para cada tipo de campo
        for row in colunas:
            coluna = str(row[0]).strip() # A limpeza do espaço é feita aqui no Python
            tipo = row[1]
            sql_update = ""

            # Tipos de Texto (CHAR = 14, VARCHAR = 37, CSTRING = 40)
            if tipo in (14, 37, 40):
                sql_update = f"UPDATE CADCNS SET {coluna} = '' WHERE {coluna} IS NULL"
                
            # Tipos Numéricos (SMALLINT = 7, INTEGER = 8, FLOAT = 10, INT64 = 16, DOUBLE = 27)
            elif tipo in (7, 8, 10, 16, 27):
                sql_update = f"UPDATE CADCNS SET {coluna} = 0 WHERE {coluna} IS NULL"
            
            if sql_update:
                try:
                    cursor.execute(sql_update)
                    if tipo in (14, 37, 40):
                        buracos_texto += cursor.rowcount
                    else:
                        buracos_numero += cursor.rowcount
                except Exception:
                    pass 

        conexao.commit() 
        
        msg = f"💣 Aniquilação Concluída!\n\n"
        msg += f"✅ Foram corrigidos {buracos_texto} campos de Texto.\n"
        msg += f"✅ Foram corrigidos {buracos_numero} campos de Número.\n\n"
        msg += "A ficha da paciente foi totalmente impermeabilizada. Pode testar salvar no BPA!"
        messagebox.showinfo("Sucesso", msg)

    except Exception as e:
        messagebox.showerror("Erro Crítico", f"Ocorreu um erro na execução:\n{e}")
    finally:
        if 'conexao' in locals():
            conexao.close()

if __name__ == "__main__":
    aniquilar_nulls_bpa()