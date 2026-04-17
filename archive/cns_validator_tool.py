# Script para garantir a integridade dos dados hospitalares, 
# removendo registros com CNS (SUS) matematicamente inválidos.


import sqlite3
import re
import os

# 1. Garante que o Python está rodando na mesma pasta do banco de dados
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def apenas_numeros(v):
    return re.sub(r'\D', '', str(v)) if v else ""

def valida_cns(cns):
    cns = apenas_numeros(cns)
    if len(cns) != 15: return False
    if cns[0] not in ['1', '2', '7', '8', '9']: return False

    if cns[0] in ['7', '8', '9']:
        soma = sum(int(cns[i]) * (15 - i) for i in range(15))
        return soma % 11 == 0
    else:
        pis = cns[:11]
        soma = sum(int(pis[i]) * (15 - i) for i in range(11))
        resto = soma % 11
        dv = 11 - resto
        if dv == 11: dv = 0
        if dv == 10:
            soma += 2
            resto = soma % 11
            dv = 11 - resto
            resultado = pis + "001" + str(dv)
        else:
            resultado = pis + "000" + str(dv)
        return cns == resultado

print("🧹 Iniciando a FAXINA CIRÚRGICA (Focada APENAS em SUS Inválido)...")

try:
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
    
    # Usamos o 'rowid' que é o ID invisível do SQLite para garantir que 
    # vamos apagar/atualizar a pessoa exata.
    cursor.execute("SELECT rowid, cpf, sus, dn, nome FROM pacientes")
    todos_pacientes = cursor.fetchall()
    
    pacientes_apagados = 0
    fichas_apagadas = 0
    datas_limpas = 0

    with open('relatorio_faxina.txt', 'w', encoding='utf-8') as f:
        f.write("=== RELATÓRIO DE FAXINA DE BANCO DE DADOS - HOSPITAL CAFÉ FILHO ===\n")
        f.write(f"Data da limpeza: {os.popen('date').read()}\n")
        f.write("-" * 80 + "\n\n")

        for paciente in todos_pacientes:
            rowid = paciente[0]
            cpf_cru = paciente[1]
            sus_cru = paciente[2]
            dn_cru = paciente[3]
            nome_paciente = paciente[4]
            
            sus_limpo = apenas_numeros(sus_cru)
            
            # --- REGRA 1: SUS ---
            # Só dá erro se tiver algo escrito lá dentro e a matemática falhar.
            erro_sus = False
            if sus_limpo:
                erro_sus = not valida_cns(sus_cru) 
                
            # --- REGRA 2: DATA ERRADA ---
            # Se a data for menor que 4 caracteres e não estiver vazia, aciona o alerta.
            erro_data = False
            if dn_cru and len(str(dn_cru).strip()) > 0 and len(str(dn_cru).strip()) < 4:
                erro_data = True
            
            # Formatações para o TXT ficar bonito
            nome_fmt = nome_paciente if nome_paciente else "NOME EM BRANCO"
            cpf_fmt = cpf_cru if cpf_cru else "SEM CPF"
            sus_fmt = sus_cru if sus_cru else "SEM SUS"
            dn_fmt = dn_cru if dn_cru else "SEM DATA"
            
            # AÇÃO 1: SUS INVÁLIDO (Deleta TUDO)
            if erro_sus:
                f.write(f"❌ EXCLUÍDO  : {nome_fmt.ljust(40)} | SUS: {sus_fmt.ljust(15)} | MOTIVO: SUS Matemático Inválido\n")
                
                # Deleta as fichas e o paciente
                cursor.execute("DELETE FROM atendimentos WHERE cpf = ?", (cpf_cru,))
                fichas_apagadas += cursor.rowcount
                cursor.execute("DELETE FROM pacientes WHERE rowid = ?", (rowid,))
                pacientes_apagados += 1
                
            # AÇÃO 2: SUS VÁLIDO MAS DATA ERRADA (Mantém o paciente, limpa a data)
            elif erro_data:
                f.write(f"⚠️ DATA LIMPA: {nome_fmt.ljust(40)} | DN ANTIGA: {dn_fmt.ljust(10)} | MOTIVO: Apenas Data Removida\n")
                
                # Atualiza apenas a data do paciente para VAZIO no banco de dados
                cursor.execute("UPDATE pacientes SET dn = '' WHERE rowid = ?", (rowid,))
                datas_limpas += 1

            # Ação 3: Se o CPF for inválido... O CÓDIGO IGNORA COMPLETAMENTE! O PACIENTE FICA SALVO!

            if (pacientes_apagados + datas_limpas) > 0 and (pacientes_apagados + datas_limpas) % 50 == 0:
                print(f"📦 Processando... {pacientes_apagados} apagados e {datas_limpas} datas limpas.")

        f.write("\n" + "=" * 80 + "\n")
        f.write(f"RESUMO FINAL:\n")
        f.write(f"- {pacientes_apagados} pacientes EXCLUÍDOS (SUS Inválido).\n")
        f.write(f"- {fichas_apagadas} fichas de atendimento EXCLUÍDAS.\n")
        f.write(f"- {datas_limpas} Datas de Nascimento APAGADAS (Os pacientes foram mantidos).\n")

    conn.commit()
    
    print("\n======================================================")
    print("✅ FAXINA CIRÚRGICA CONCLUÍDA COM SUCESSO!")
    print(f"-> {pacientes_apagados} Pacientes removidos (Apenas os com SUS falso/inválido).")
    print(f"-> {datas_limpas} Datas de Nascimento foram limpas (Pacientes preservados).")
    print(f"-> Os problemas de CPF foram completamente ignorados e mantidos no banco.")
    print("======================================================")

except Exception as e:
    print(f"❌ Ocorreu um erro: {e}")
finally:
    conn.close()