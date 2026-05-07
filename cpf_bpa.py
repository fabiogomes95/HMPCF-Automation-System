import sqlite3
import firebirdsql
from datetime import datetime

# ==============================================================================
# SISTEMA GESTÃO BPA - SINCRONIZADOR COM CO_LOGRAD E PROTEÇÃO DE DADOS
# AUTOR: FÁBIO GOMES DA SILVA
# ==============================================================================

DB_SQLITE = 'hospital.db'
DB_FIREBIRD = 'C:/BPA/BPAMAG.GDB'

def sincronizar():
    print("\n" + "="*45)
    print("   HMPCF - SINCRONIZADOR BPA (PRODUÇÃO)")
    print("="*45)
    
    mes = input("Digite o MÊS (ex: 05): ").strip().zfill(2)
    ano = input("Digite o ANO (ex: 2026): ").strip()

    sucessos = 0
    falhas = 0
    lista_novos = []
    lista_erros = []

    try:
        con_sqlite = sqlite3.connect(DB_SQLITE)
        con_sqlite.row_factory = sqlite3.Row
        cur_sqlite = con_sqlite.cursor()
        
        # Filtro de data sensível a múltiplos formatos (ISO e BR)
        query_sqlite = f"""
            SELECT DISTINCT pacientes.* FROM pacientes
            INNER JOIN atendimentos ON pacientes.cpf = atendimentos.cpf
            WHERE atendimentos.data_atendimento LIKE ? 
               OR atendimentos.data_atendimento LIKE ?
        """
        
        cur_sqlite.execute(query_sqlite, (f'%-%{mes}-%', f'%/%{mes}/%'))
        pacientes = cur_sqlite.fetchall()

        if not pacientes:
            print(f"\n[!] Nenhum atendimento encontrado para {mes}/{ano}.")
            return

        con_fb = firebirdsql.connect(
            host='localhost', database=DB_FIREBIRD,
            user='SYSDBA', password='masterkey', charset='WIN1252'
        )
        cur_fb = con_fb.cursor()

        for p in pacientes:
            try:
                # --- Tratamento de Dados ---
                nome_bpa = str(p['nome']).upper().strip()[:30].strip()
                cpf_limpo = ''.join(filter(str.isdigit, str(p['cpf'])))[:11]
                sus_limpo = ''.join(filter(str.isdigit, str(p['sus'] or '')))[:15]
                
                # Formatação YYYYMMDD para chave de busca
                dt_nasc_orig = str(p['dn']).strip()
                try:
                    if '/' in dt_nasc_orig:
                        dt_nasc = datetime.strptime(dt_nasc_orig, '%d/%m/%Y').strftime('%Y%m%d')
                    else:
                        dt_nasc = datetime.strptime(dt_nasc_orig, '%Y-%m-%d').strftime('%Y%m%d')
                except:
                    dt_nasc = '19000101'

                # --- BUSCA POR CHAVE COMPOSTA (NOME + DATA NASC) ---
                cur_fb.execute("SELECT NOME FROM CADCNS WHERE NOME = ? AND DTNASC = ?", (nome_bpa, dt_nasc))
                reg = cur_fb.fetchone()

                # Dados de endereço e contato
                end = str(p['endereco'] or '').upper().strip()[:25]
                num = str(p['numero'] or '').strip()[:5]
                bairro = str(p['bairro'] or '').upper().strip()[:15]
                tel_full = ''.join(filter(str.isdigit, str(p['tel'] or '')))
                ddd = tel_full[:2] if len(tel_full) >= 10 else ''
                tel = tel_full[-8:] if len(tel_full) >= 8 else tel_full
                sexo = str(p['sexo'] or 'M').upper()[:1]
                
                # Código Logradouro fixado conforme solicitado
                co_lograd = "081" 

                if reg:
                    # UPDATE: Atualiza os dados, incluindo o código da rua
                    nome_alvo = reg[0]
                    sql_up = """
                        UPDATE CADCNS SET 
                            NUM_CPF = ?, LOGPCN = ?, NUMPCN = ?, BAIRRO_PCNTE = ?, 
                            DDTEL_PCNTE = ?, TEL_PCNTE = ?, CNS = ?, CO_LOGRAD = ?
                        WHERE NOME = ? AND DTNASC = ?
                    """
                    cur_fb.execute(sql_up, (cpf_limpo, end, num, bairro, ddd, tel, sus_limpo, co_lograd, nome_alvo, dt_nasc))
                    con_fb.commit()
                    sucessos += 1
                else:
                    # INSERT: Novo cadastro completo
                    sql_in = """
                        INSERT INTO CADCNS (
                            CNS, NOME, NUM_CPF, DTNASC, SEXO, RACA, LOGPCN, 
                            NUMPCN, BAIRRO_PCNTE, CEPPCN, IBGE, DDTEL_PCNTE, TEL_PCNTE, CO_LOGRAD
                        ) VALUES (?, ?, ?, ?, ?, '03', ?, ?, ?, '59575000', '240360', ?, ?, ?)
                    """
                    cur_fb.execute(sql_in, (sus_limpo, nome_bpa, cpf_limpo, dt_nasc, sexo, end, num, bairro, ddd, tel, co_lograd))
                    con_fb.commit()
                    sucessos += 1
                    lista_novos.append(f"[NOVO] {nome_bpa} ({dt_nasc}) | Logradouro: {co_lograd}")

            except Exception as e:
                con_fb.rollback()
                falhas += 1
                lista_erros.append(f"Erro em {p['nome']}: {e}")

    except Exception as e_fatal:
        print(f"\n[!] Erro Crítico: {e_fatal}")

    finally:
        if 'con_fb' in locals(): con_fb.close()
        if 'con_sqlite' in locals(): con_sqlite.close()
        
        nome_log = f"log_sincronia_{mes}_{ano}.txt"
        with open(nome_log, "w", encoding="utf-8") as f:
            f.write(f"--- RELATÓRIO DE PRODUÇÃO HMPCF: {mes}/{ano} ---\n")
            f.write(f"Sincronizados: {sucessos} | Falhas: {falhas}\n")
            f.write("-" * 50 + "\n\n")
            if lista_novos:
                f.write("--- CADASTRADOS/ATUALIZADOS ---\n")
                for n in lista_novos: f.write(n + "\n")
            if lista_erros:
                f.write("\n--- ERROS ENCONTRADOS ---\n")
                for e in lista_erros: f.write(e + "\n")

        print(f"\n[OK] Sincronização finalizada! Relatório salvo em: {nome_log}")

if __name__ == "__main__":
    sincronizar()