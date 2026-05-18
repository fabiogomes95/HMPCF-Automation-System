# ==============================================================================
# PADRONIZAR_GDB.PY — O Formatador Oficial do Hospital Café Filho
# ==============================================================================
# Esse script lê os pacientes diretamente do banco BPAMAG.GDB (tabela CADCNS)
# e padroniza os dados (remove acentos, ajusta telefones, sexos e endereços)
# para evitar erros na hora de gerar a produção do BPA.
# ==============================================================================

import firebirdsql
import re
import unicodedata

# Configurações do Banco de Dados
CAMINHO_GDB = r'C:/BPA/BPAMAG.GDB'
USER = 'SYSDBA'
PASS = 'masterkey'

def remove_accents(input_str):
    """Remove acentos e deixa tudo em MAIÚSCULO."""
    if not input_str: return ""
    nfkd_form = unicodedata.normalize('NFKD', str(input_str))
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()

def apenas_numeros(valor):
    """Remove traços e parênteses, deixando só números."""
    if not valor: return ""
    return re.sub(r'\D', '', str(valor))

def padronizar_banco_gdb():
    try:
        print(f"🔍 Conectando ao banco em: {CAMINHO_GDB}")
        con = firebirdsql.connect(host='localhost', database=CAMINHO_GDB, user=USER, password=PASS, charset='WIN1252')
        cur = con.cursor()

        print("⏳ Lendo todos os pacientes do banco...")
        # Busca todas as informações atuais do paciente no GDB
        cur.execute("""
            SELECT NOME, DTNASC, NUM_CPF, CNS, SEXO, 
                   LOGPCN, NUMPCN, BAIRRO_PCNTE, DDTEL_PCNTE, TEL_PCNTE 
            FROM CADCNS
        """)
        pacientes = cur.fetchall()

        if not pacientes:
            print("❌ Nenhum paciente encontrado no banco.")
            con.close()
            return

        sucessos_upd = 0
        erros = 0

        print(f"⚙️ Padronizando {len(pacientes)} registros. Isso pode levar um minuto...")

        for p in pacientes:
            try:
                nome_original = p[0]
                dtnasc = p[1]
                
                # Se não tiver nome ou data, pula (pois são a chave de busca)
                if not nome_original or not dtnasc:
                    continue

                # 1. NOME (Sem acentos, max 30 caracteres)
                nome_limpo = remove_accents(nome_original)[:30].strip()

                # 2. DOCUMENTOS (Apenas números)
                cpf = apenas_numeros(p[2])[:11] if p[2] else ""
                sus = apenas_numeros(p[3])[:15] if p[3] else ""

                # 3. SEXO (Garante que seja apenas M ou F)
                sexo_raw = str(p[4]).strip().upper() if p[4] else ""
                sexo = sexo_raw[:1] if sexo_raw in ['M', 'F'] else 'F' # Padrão F se estiver bagunçado

                # 4. ENDEREÇO (Sem acentos, preenchimento padrão se vazio)
                rua = remove_accents(p[5])[:25] if p[5] else "R. PRINCIPAL"
                numero = remove_accents(p[6])[:5] if p[6] else "S/N"
                bairro = remove_accents(p[7])[:15] if p[7] else "CENTRO"
                co_lograd = "081"  # Código de logradouro padrão aceito pelo SUS

                # 5. TELEFONE (Separa DDD do Número)
                ddd_original = apenas_numeros(p[8])
                tel_original = apenas_numeros(p[9])
                
                tel_full = ddd_original + tel_original
                if len(tel_full) <= 9 and tel_full:
                    tel_full = "84" + tel_full # Adiciona 84 se não tiver DDD
                
                ddd = tel_full[:2] if len(tel_full) >= 10 else ''
                tel = tel_full[-8:] if len(tel_full) >= 8 else tel_full

                # --- ATUALIZA O PACIENTE NO FIREBIRD ---
                # Usamos o nome ORIGINAL e a dtnasc ORIGINAL na cláusula WHERE 
                # para garantir que achamos o paciente certo antes de atualizar o nome dele
                sql_up = """
                    UPDATE CADCNS SET
                        NOME = ?, NUM_CPF = ?, CNS = ?, SEXO = ?,
                        LOGPCN = ?, NUMPCN = ?, BAIRRO_PCNTE = ?, 
                        DDTEL_PCNTE = ?, TEL_PCNTE = ?, CO_LOGRAD = ?
                    WHERE NOME = ? AND DTNASC = ?
                """
                cur.execute(sql_up, (
                    nome_limpo, cpf, sus, sexo,
                    rua, numero, bairro, ddd, tel, co_lograd,
                    nome_original, dtnasc
                ))
                sucessos_upd += 1

            except Exception as e_linha:
                erros += 1

        con.commit()
        con.close()

        print("\n" + "="*50)
        print("✅ PADRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*50)
        print(f"🔸 Pacientes Formatados: {sucessos_upd}")
        print(f"🔸 Erros durante a leitura: {erros}")
        print("="*50)
        print("Agora o seu banco está com nomes sem acentos e telefones corrigidos!")

    except Exception as e:
        print(f"❌ Erro de conexao ou execucao: {e}")

if __name__ == "__main__":
    padronizar_banco_gdb()
    input("\nPressione Enter para sair...")