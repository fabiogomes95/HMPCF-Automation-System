# ==============================================================================
# 🧹 SCRIPT DE SUPER FAXINA: BPA (HMPCF)
# ==============================================================================
# Limpa CPFs/CNS inválidos, corrige datas impossíveis e preenche endereços vazios.
# Sem dependência de UDF/DLL externa para compatibilidade com Firebird antigo.
# ==============================================================================

import firebirdsql
import re

CAMINHO_GDB = r'C:/BPA/BPAMAG.GDB'
USER = 'SYSDBA'
PASS = 'masterkey'

# --- FUNÇÕES DE VALIDAÇÃO ---
def apenas_numeros(valor):
    if not valor: return ""
    return re.sub(r'\D', '', str(valor))

def valida_cns(cns):
    if not cns or len(cns) != 15 or cns[0] not in '12789': return False
    try:
        soma = sum(int(cns[i]) * (15 - i) for i in range(15))
        return soma % 11 == 0
    except: return False

def valida_cpf(cpf):
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1: return False
    try:
        soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito_1 = (soma_1 * 10 % 11) % 10
        soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito_2 = (soma_2 * 10 % 11) % 10
        return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]
    except: return False

# --- MOTOR DA FAXINA ---
def iniciar_faxina():
    try:
        print(f"🔍 Conectando ao banco em: {CAMINHO_GDB}")
        con = firebirdsql.connect(host='localhost', database=CAMINHO_GDB, user=USER, password=PASS, charset='WIN1252')
        cur = con.cursor()

        print("⏳ Analisando todos os registros do banco... Isso pode levar alguns segundos.")

        # 1. VERIFICAR DATAS
        cur.execute("""
            SELECT NOME, DTNASC FROM CADCNS
            WHERE DTNASC < '18900101' OR DTNASC > '20261231'
               OR DTNASC IS NULL OR DTNASC = '00000000' OR DTNASC = '99999999'
        """)
        datas_invalidas = cur.fetchall()

        # 2. VERIFICAR ENDEREÇOS (Sem usar TRIM)
        cur.execute("SELECT COUNT(*) FROM CADCNS WHERE LOGPCN IS NULL OR LOGPCN = ''")
        ruas_vazias = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM CADCNS WHERE NUMPCN IS NULL OR NUMPCN = ''")
        num_vazios = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM CADCNS WHERE BAIRRO_PCNTE IS NULL OR BAIRRO_PCNTE = ''")
        bairros_vazios = cur.fetchone()[0]

        # 3. VERIFICAR DOCUMENTOS
        cur.execute("SELECT NOME, CNS, NUM_CPF FROM CADCNS")
        pacientes = cur.fetchall()

        cpfs_invalidos, cns_invalidos = [], []
        for p in pacientes:
            nome, cns, cpf = p[0], p[1], p[2]
            if cns_limpo := apenas_numeros(cns):
                if not valida_cns(cns_limpo): cns_invalidos.append((nome, cns))
            if cpf_limpo := apenas_numeros(cpf):
                if not valida_cpf(cpf_limpo): cpfs_invalidos.append((nome, cpf))

        # --- RELATÓRIO ---
        total_docs = len(cpfs_invalidos) + len(cns_invalidos)
        total_end = ruas_vazias + num_vazios + bairros_vazios
        
        if total_docs == 0 and len(datas_invalidas) == 0 and total_end == 0:
            print("✅ Faxina concluída! O banco está em perfeito estado.")
            con.close()
            return

        print("\n" + "="*50)
        print("⚠️ RELATÓRIO DE INCONSISTÊNCIAS ENCONTRADAS")
        print("="*50)
        print(f"🔸 Documentos Inválidos: {len(cpfs_invalidos)} CPFs | {len(cns_invalidos)} SUS")
        print(f"🔸 Datas de Nascimento Absurdas: {len(datas_invalidas)} pacientes")
        print(f"🔸 Endereços Incompletos: {ruas_vazias} Ruas | {num_vazios} Números | {bairros_vazios} Bairros")
        print("="*50)

        escolha = input("\nDeseja aplicar todas as correções automaticamente agora? (S/N): ")

        if escolha.upper() == 'S':
            print("\n⏳ Iniciando as correções...")

            if len(cpfs_invalidos) > 0:
                print("   -> Limpando CPFs inválidos...")
                for nome, cpf in cpfs_invalidos:
                    cur.execute("UPDATE CADCNS SET NUM_CPF = '' WHERE NOME = ? AND NUM_CPF = ?", (nome, cpf))
            
            if len(cns_invalidos) > 0:
                print("   -> Limpando Cartões SUS inválidos...")
                for nome, cns in cns_invalidos:
                    cur.execute("UPDATE CADCNS SET CNS = '' WHERE NOME = ? AND CNS = ?", (nome, cns))

            if len(datas_invalidas) > 0:
                print("   -> Padronizando Datas de Nascimento...")
                cur.execute("""
                    UPDATE CADCNS 
                    SET DTNASC = '19900304'
                    WHERE DTNASC < '18900101' OR DTNASC > '20261231' 
                       OR DTNASC IS NULL OR DTNASC = '00000000' OR DTNASC = '99999999'
                """)

            if total_end > 0:
                print("   -> Preenchendo Ruas, Números e Bairros vazios...")
                cur.execute("UPDATE CADCNS SET LOGPCN = 'R. PRINCIPAL' WHERE LOGPCN IS NULL OR LOGPCN = ''")
                cur.execute("UPDATE CADCNS SET NUMPCN = 'S/N' WHERE NUMPCN IS NULL OR NUMPCN = ''")
                cur.execute("UPDATE CADCNS SET BAIRRO_PCNTE = 'CENTRO' WHERE BAIRRO_PCNTE IS NULL OR BAIRRO_PCNTE = ''")

            con.commit()
            print("\n✅ SUPER FAXINA REALIZADA COM SUCESSO! Banco pronto para exportação.")
        else:
            print("\n❌ Operação cancelada.")

        con.close()

    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    iniciar_faxina()