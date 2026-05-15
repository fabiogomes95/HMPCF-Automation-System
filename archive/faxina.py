import sqlite3
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import apenas_numeros, valida_cns, valida_cpf

# Garante que vai achar o banco na pasta certa
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(DIRETORIO_ATUAL, '..'))
DB_NAME = 'hospital.db'

# ==============================================================================
# 🧹 A GRANDE FAXINA COM AUDITORIA E REESTRUTURAÇÃO
# ==============================================================================
def fazer_faxina():
    print("🧹 Iniciando a Grande Faxina e Auditoria no Banco de Dados...")
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Puxa todos os pacientes do banco de dados
    cursor.execute("SELECT * FROM pacientes")
    pacientes_sujos = cursor.fetchall()
    
    pacientes_limpos = {}
    fichas_excluidas = 0
    
    for p in pacientes_sujos:
        dados = dict(p)
        cpf_bruto = apenas_numeros(dados.get('cpf', ''))
        sus_bruto = apenas_numeros(dados.get('sus', ''))
        
        # 1. PASSA PELA AUDITORIA: Se o documento for falso, ele vira vazio ("")
        cpf_puro = cpf_bruto if valida_cpf(cpf_bruto) else ""
        sus_puro = sus_bruto if valida_cns(sus_bruto) else ""
        
        # 2. A GUILHOTINA: A ficha não tem nem CPF nem SUS válidos? Lixo nela!
        if not cpf_puro and not sus_puro:
            fichas_excluidas += 1
            continue
            
        # Atualiza os dados da ficha apagando a sujeira que falhou na auditoria
        dados['cpf'] = cpf_puro
        dados['sus'] = sus_puro
        
        # A chave mestre: agrupa pelo documento VÁLIDO que restou
        chave_unica = cpf_puro if cpf_puro else sus_puro
        
        if chave_unica in pacientes_limpos:
            # MÁGICA DA MESCLAGEM: Se já tem esse paciente, funde os dados pra não perder nada!
            paciente_guardado = pacientes_limpos[chave_unica]
            for coluna, valor in dados.items():
                if not paciente_guardado.get(coluna) and valor:
                    paciente_guardado[coluna] = valor
        else:
            pacientes_limpos[chave_unica] = dados

    print(f"📉 Encontrados {len(pacientes_sujos)} registros totais no sistema.")
    print(f"🗑️  FORAM APAGADAS {fichas_excluidas} fichas por não terem CPF ou SUS verdadeiros.")
    print(f"✨ Após a auditoria e mesclagem, restaram {len(pacientes_limpos)} pacientes VÁLIDOS e ÚNICOS.")

    # 3. REESTRUTURAÇÃO: Recria a tabela com a Chave Primária Composta (A salvação do banco)
    print("♻️  Recriando a tabela com a nova arquitetura blindada...")
    cursor.execute("DROP TABLE pacientes")
    
    # 💡 ATENÇÃO AQUI: Mudamos a PRIMARY KEY para abraçar o CPF e o SUS ao mesmo tempo
    cursor.execute('''CREATE TABLE pacientes (
        cpf TEXT, sus TEXT, nome TEXT, nomeSocial TEXT, naturalidade TEXT, 
        dn TEXT, idade TEXT, sexo TEXT, civil TEXT, raca TEXT, ocupacao TEXT, 
        mae TEXT, responsavel TEXT, tel TEXT, endereco TEXT, numero TEXT, 
        bairro TEXT, cidade TEXT, estado TEXT, 
        PRIMARY KEY (cpf, sus)
    )''')
    
    print("💾 Salvando pacientes sobreviventes...")
    for chave, dados in pacientes_limpos.items():
        colunas = ', '.join(dados.keys())
        placeholders = ', '.join(['?'] * len(dados))
        valores = tuple(dados.values())
        cursor.execute(f'''INSERT INTO pacientes ({colunas}) VALUES ({placeholders})''', valores)

    # 4. Limpa e valida também as ocorrências (atendimentos passados)
    print("🩹 Auditando pontuações da tabela de atendimentos...")
    cursor.execute("SELECT id, cpf, sus FROM atendimentos")
    for a in cursor.fetchall():
        id_atend = a['id']
        a_cpf = apenas_numeros(a['cpf'])
        a_sus = apenas_numeros(a['sus'])
        
        # Valida os dados históricos
        a_cpf_ok = a_cpf if valida_cpf(a_cpf) else ""
        a_sus_ok = a_sus if valida_cns(a_sus) else ""
        
        cursor.execute("UPDATE atendimentos SET cpf=?, sus=? WHERE id=?", (a_cpf_ok, a_sus_ok, id_atend))

    conn.commit()
    conn.close()
    print("✅ Faxina e Auditoria Concluídas! O seu Banco de Dados agora é impenetrável.")

if __name__ == '__main__':
    fazer_faxina()