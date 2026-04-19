# ==============================================================================
# FERRAMENTA DE AUDITORIA PROFUNDA (A FAXINA CIRÚRGICA)
# ==============================================================================
# OBJETIVO:
# Entrar no Banco de Dados SQLite, vasculhar o histórico inteiro de pacientes
# e aplicar a lei matemática do Cartão SUS. Quem tiver SUS falso é DELETADO, 
# quem tiver Data de Nascimento corrompida tem a data limpa. 
# Tudo é logado em um arquivo TXT de relatório final.
# ==============================================================================

import sqlite3
import re
import os

# Garante que o Python está rodando na mesma pasta do script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ==============================================================================
# 1. FUNÇÕES DE VALIDAÇÃO (O ALGORITMO DO MINISTÉRIO DA SAÚDE)
# ==============================================================================
def apenas_numeros(v):
    # Usa Regex (\D) para arrancar letras, traços e espaços
    return re.sub(r'\D', '', str(v)) if v else ""

def valida_cns(cns):
    # Lógica de validação do Módulo 11 (Padrão Ouro do DATASUS)
    cns = apenas_numeros(cns)
    if len(cns) != 15: return False
    if cns not in ['1', '2', '7', '8', '9']: return False
    
    if cns in ['7', '8', '9']:
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

# ==============================================================================
# 2. CONEXÃO E VARREDURA DO BANCO
# ==============================================================================
try:
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
    
    # 'rowid' é o identificador numérico interno e secreto do SQLite. 
    # Usamos ele para garantir que a exclusão vai deletar apenas a pessoa exata.
    cursor.execute("SELECT rowid, cpf, sus, dn, nome FROM pacientes")
    todos_pacientes = cursor.fetchall()
    
    pacientes_apagados, fichas_apagadas, datas_limpas = 0, 0, 0
    
    # Cria o arquivo de relatório físico da faxina
    with open('relatorio_faxina.txt', 'w', encoding='utf-8') as f:
        f.write("=== RELATÓRIO DE FAXINA DE BANCO DE DADOS - HOSPITAL CAFÉ FILHO ===\n")
        f.write("-" * 80 + "\n\n")
        
        # ======================================================================
        # 3. LÓGICA DE AUDITORIA PACIENTE POR PACIENTE
        # ======================================================================
        for paciente in todos_pacientes:
            rowid, cpf_cru, sus_cru, dn_cru, nome_paciente = paciente
            sus_limpo = apenas_numeros(sus_cru)
            
            # Regra 1: Avalia falha matemática no SUS
            erro_sus = False
            if sus_limpo:
                erro_sus = not valida_cns(sus_cru)
                
            # Regra 2: Avalia lixo no campo data (ex: digitou apenas '19')
            erro_data = False
            if dn_cru and len(str(dn_cru).strip()) > 0 and len(str(dn_cru).strip()) < 4:
                erro_data = True
                
            # Formatação amigável para leitura no TXT
            nome_fmt = nome_paciente if nome_paciente else "NOME EM BRANCO"
            cpf_fmt = cpf_cru if cpf_cru else "SEM CPF"
            sus_fmt = sus_cru if sus_cru else "SEM SUS"
            dn_fmt = dn_cru if dn_cru else "SEM DATA"

            # ==================================================================
            # 4. APLICAÇÃO DAS PENALIDADES (DELETE ou UPDATE)
            # ==================================================================
            if erro_sus:
                f.write(f"❌ EXCLUÍDO  : {nome_fmt.ljust(40)} | SUS: {sus_fmt.ljust(15)} | MOTIVO: SUS Matemático Inválido\n")
                
                # Deleta todo o rastro (Fichas primeiro, Paciente depois)
                cursor.execute("DELETE FROM atendimentos WHERE cpf = ?", (cpf_cru,))
                fichas_apagadas += cursor.rowcount
                
                cursor.execute("DELETE FROM pacientes WHERE rowid = ?", (rowid,))
                pacientes_apagados += 1
                
            elif erro_data:
                # O SUS é válido, mas a data é ruim. Mantemos o paciente, mas apagamos a data.
                f.write(f"⚠ DATA LIMPA: {nome_fmt.ljust(40)} | DN ANTIGA: {dn_fmt.ljust(10)} | MOTIVO: Apenas Data Removida\n")
                cursor.execute("UPDATE pacientes SET dn = '' WHERE rowid = ?", (rowid,))
                datas_limpas += 1

            # Ação 3 (Exceção de Regra de Negócio): Problemas de CPF são totalmente ignorados 
            # para focar exclusivamente na exigência principal do Governo (Cartão SUS).

        # ======================================================================
        # 5. RESUMO FINAL E FECHAMENTO
        # ======================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"RESUMO FINAL:\n")
        f.write(f"- {pacientes_apagados} pacientes EXCLUÍDOS (SUS Inválido).\n")
        f.write(f"- {fichas_apagadas} fichas de atendimento EXCLUÍDAS.\n")
        f.write(f"- {datas_limpas} Datas de Nascimento APAGADAS.\n")
        
    conn.commit() # Efetiva a faxina
    print("✅ FAXINA CIRÚRGICA CONCLUÍDA COM SUCESSO!")

except Exception as e:
    print(f"❌ Ocorreu um erro: {e}")
finally:
    conn.close()
