# ==============================================================================
# 🧹 FAXINA GERAL V3: DEDUPLICAÇÃO COM INTELIGÊNCIA ARTIFICIAL (Nomes e Vínculos)
# ==============================================================================
import sqlite3
import os

try:
    from utils import apenas_numeros, valida_cpf, valida_cns
except ImportError:
    print("❌ ERRO: Arquivo 'utils.py' não encontrado.")
    exit()

def faxina_definitiva():
    print("==================================================")
    print("🛡️ FAXINA V3 - MÁXIMA SEGURANÇA E PREVENÇÃO DE ERROS")
    print("==================================================\n")

    caminho_db = os.path.join(os.path.dirname(__file__), 'hospital.db')
    
    confirmar = input("⚠️ ATENÇÃO: Você RESTAUROU O BACKUP original de novo? (S/N): ").strip().upper()
    if confirmar != 'S':
        print("🛑 Operação cancelada. Restaure o backup antes de tentar novamente.")
        return

    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT rowid, nome, cpf, sus FROM pacientes")
        todos_pacientes = cursor.fetchall()
        
        grupos = {}
        pacientes_sem_doc = 0

        for paciente in todos_pacientes:
            rowid, nome, cpf_bruto, sus_bruto = paciente
            
            chave_unica = None
            
            # Validações matemáticas do seu utils
            if cpf_bruto and valida_cpf(cpf_bruto):
                chave_unica = apenas_numeros(cpf_bruto)
            elif sus_bruto and valida_cns(sus_bruto):
                chave_unica = apenas_numeros(sus_bruto)
            
            if chave_unica:
                if chave_unica not in grupos:
                    grupos[chave_unica] = []
                grupos[chave_unica].append(paciente)
            else:
                pacientes_sem_doc += 1

        total_grupos_fundidos = 0
        total_clones_apagados = 0
        total_atend_movidos = 0
        cpf_generico_ignorado = 0

        for chave, lista_pacientes in grupos.items():
            if len(lista_pacientes) > 1:
                
                # 🛡️ TRAVA 1: PREVENÇÃO DO CPF GENÉRICO (O CASO TAISE 183)
                # Se esse documento estiver sendo usado por muitas pessoas diferentes, é falso!
                nomes_unicos = set([str(p[1]).strip().upper() for p in lista_pacientes if p[1]])
                if len(nomes_unicos) > 3:
                    cpf_generico_ignorado += len(lista_pacientes)
                    continue # Pula esse grupo inteiro, não funde ninguém!
                    
                total_grupos_fundidos += 1
                
                # 🧠 TRAVA 2: O MELHOR NOME FICA (O CASO "09:23")
                # Ordena pelo tamanho da string, do maior para o menor.
                lista_pacientes.sort(key=lambda x: len(str(x[1]).strip()), reverse=True)
                
                master = lista_pacientes[0]
                master_id = master[0]
                master_nome = master[1]
                
                # 🛠️ TRAVA 3: PROTEÇÃO CONTRA CAMPOS VAZIOS (O CASO DA BUSCA QUEBRADA)
                # Vamos garimpar o melhor CPF e SUS de todos os clones para montar o "Master Perfeito"
                melhor_cpf = master[2]
                melhor_sus = master[3]
                
                for p in lista_pacientes:
                    if not melhor_cpf and p[2] and valida_cpf(p[2]): melhor_cpf = p[2]
                    if not melhor_sus and p[3] and valida_cns(p[3]): melhor_sus = p[3]

                # Atualiza a tabela Pacientes garantindo que o Master tenha os documentos completos
                cursor.execute("UPDATE pacientes SET cpf = ?, sus = ?, nome = ? WHERE rowid = ?", 
                               (melhor_cpf, melhor_sus, master_nome, master_id))
                
                clones = lista_pacientes[1:]
                for clone in clones:
                    clone_id, clone_nome, clone_cpf, clone_sus = clone
                    
                    # Move os atendimentos apontando sempre para o Melhor CPF/SUS
                    if clone_sus and str(clone_sus).strip() != '':
                        cursor.execute("UPDATE atendimentos SET sus = ? WHERE sus = ?", (melhor_sus, clone_sus))
                        total_atend_movidos += cursor.rowcount
                        
                    if clone_cpf and str(clone_cpf).strip() != '':
                        cursor.execute("UPDATE atendimentos SET cpf = ? WHERE cpf = ?", (melhor_cpf, clone_cpf))
                        total_atend_movidos += cursor.rowcount
                        
                    # Deleta o clone do banco
                    cursor.execute("DELETE FROM pacientes WHERE rowid = ?", (clone_id,))
                    total_clones_apagados += 1
                    
                    print(f"  ➜ Clone '{clone_nome}' absorvido pelo Master '{master_nome}'")

        conn.commit()

        print("\n" + "="*50)
        print("🎉 FAXINA DEFINITIVA CONCLUÍDA!")
        print("="*50)
        print(f"👥 Pacientes legítimos corrigidos : {total_grupos_fundidos}")
        print(f"🗑️ Cadastros Clones apagados      : {total_clones_apagados}")
        print(f"🔄 Atendimentos realocados        : {total_atend_movidos}")
        print(f"⚠️ Ignorados (Sem Doc Válido)     : {pacientes_sem_doc}")
        print(f"🚨 Ignorados (CPF/SUS Coringa)    : {cpf_generico_ignorado}")
        print("==================================================")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    faxina_definitiva()