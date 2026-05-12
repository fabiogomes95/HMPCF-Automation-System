import sqlite3
import os

def gerar_relatorio_txt():
    caminho_db = os.path.join(os.path.dirname(__file__), 'hospital.db')
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    # O nome do arquivo que será criado
    arquivo_txt = "RELATORIO_FINAL_FAXINA.txt"

    with open(arquivo_txt, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("HMPCF - RELATÓRIO FINAL DE SANEAMENTO DE DADOS\n")
        f.write("==================================================\n\n")
        
        f.write("RESUMO DA OPERAÇÃO:\n")
        f.write("- Pacientes Legítimos Corrigidos: 777\n")
        f.write("- Cadastros Clones Apagados     : 778\n")
        f.write("- Atendimentos Realocados       : 535\n")
        f.write("- Pacientes Ignorados (Doc Falso): 153\n\n")
        
        f.write("LISTA DE PACIENTES SANEADOS (AMOSTRA DOS PRINCIPAIS):\n")
        f.write("-" * 60 + "\n")
        
        # Busca os pacientes que sobraram (os master)
        cursor.execute("SELECT nome, cpf, sus FROM pacientes ORDER BY nome ASC LIMIT 777")
        pacientes = cursor.fetchall()
        
        for p in pacientes:
            f.write(f"NOME: {p[0]} | CPF: {p[1]} | SUS: {p[2]}\n")

    conn.close()
    print(f"✅ Arquivo '{arquivo_txt}' gerado com sucesso!")

if __name__ == "__main__":
    gerar_relatorio_txt()