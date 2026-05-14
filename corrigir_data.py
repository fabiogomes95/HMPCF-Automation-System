# ==============================================================================
# 🩺 SCRIPT DE MANUTENÇÃO: CORREÇÃO DE DATAS IMPOSSÍVEIS (HMPCF)
# ==============================================================================
# Este script localiza datas de nascimento absurdas no banco de dados
# e as padroniza para 01/01/1990 para evitar erros no validador do BPA.
# ==============================================================================

import firebirdsql
from datetime import datetime

# Configurações do Banco de Dados
CAMINHO_GDB = r'C:/BPA/BPAMAG.GDB'
USER = 'SYSDBA'
PASS = 'masterkey'
DATA_PADRAO = '19900101'  # 01/01/1990 no formato do banco

def corrigir_banco():
    try:
        print(f"🔍 Conectando ao banco em: {CAMINHO_GDB}")
        con = firebirdsql.connect(host='localhost', database=CAMINHO_GDB, user=USER, password=PASS, charset='WIN1252')
        cur = con.cursor()

        # 1. Identificar datas absurdas (Humanamente impossíveis)
        # Consideramos absurdo: Anos antes de 1890 ou anos no futuro (depois de 2026)
        print("⏳ Analisando registros, aguarde...")
        
        sql_busca = """
            SELECT CNS, NOME, DTNASC 
            FROM CADCNS 
            WHERE DTNASC < '18900101' 
               OR DTNASC > '20261231'
               OR DTNASC IS NULL
               OR DTNASC = '00000000'
               OR DTNASC = '99999999'
        """
        
        cur.execute(sql_busca)
        pacientes_com_erro = cur.fetchall()

        if not pacientes_com_erro:
            print("✅ Nenhuma data absurda encontrada! O banco está limpo.")
            con.close()
            return

        print(f"\n⚠️  ATENÇÃO: Foram encontrados {len(pacientes_com_erro)} pacientes com datas inválidas.")
        print("-" * 50)
        # Mostra os 10 primeiros como exemplo
        for p in pacientes_com_erro[:10]:
            print(f"PACIENTE: {p[1][:25]} | DATA ATUAL: {p[2]}")
        print("-" * 50)

        # 2. Pedir confirmação (Segurança em primeiro lugar)
        confirmar = input(f"\nDESEJA CORRIGIR TODOS ESSES {len(pacientes_com_erro)} REGISTROS PARA {DATA_PADRAO}? (S/N): ")
        
        if confirmar.upper() == 'S':
            print("⏳ Corrigindo registros no banco de dados...")
            
            sql_update = f"""
                UPDATE CADCNS 
                SET DTNASC = '{DATA_PADRAO}'
                WHERE DTNASC < '18900101' 
                   OR DTNASC > '20261231'
                   OR DTNASC IS NULL
                   OR DTNASC = '00000000'
                   OR DTNASC = '99999999'
            """
            
            cur.execute(sql_update)
            con.commit() # Salva as alterações de verdade no banco
            
            print(f"✅ SUCESSO! {len(pacientes_com_erro)} pacientes foram atualizados para 01/01/1990.")
        else:
            print("❌ Operação cancelada pelo usuário. Nada foi alterado.")

        con.close()

    except Exception as e:
        print(f"❌ ERRO AO ACESSAR O BANCO: {e}")

if __name__ == "__main__":
    corrigir_banco()
    input("\nPressione Enter para sair...")