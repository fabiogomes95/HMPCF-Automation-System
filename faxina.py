import sqlite3
import re
import os

# Garante que vai achar o banco na pasta certa
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIRETORIO_ATUAL)
DB_NAME = 'hospital.db'

# ==============================================================================
# 🛡️ FUNÇÕES DE VALIDAÇÃO (O Inspetor Implacável)
# ==============================================================================
def limpar_numero(valor):
    """Remove pontuações mantendo os zeros à esquerda"""
    if not valor: return ""
    return re.sub(r'\D', '', str(valor)).strip()

def valida_cns(cns):
    """Matemática oficial do DATASUS"""
    if not cns or len(cns) != 15 or cns[0] not in '12789': 
        return False
    soma = sum(int(cns[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0

def valida_cpf(cpf):
    """Matemática oficial da Receita Federal"""
    if not cpf or len(cpf) != 11 or len(set(cpf)) == 1: 
        return False
    soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma_1 * 10 % 11) % 10
    soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma_2 * 10 % 11) % 10
    return str(digito_1) == cpf[9] and str(digito_2) == cpf[10]

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
        cpf_bruto = limpar_numero(dados.get('cpf', ''))
        sus_bruto = limpar_numero(dados.get('sus', ''))
        
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
        a_cpf = limpar_numero(a['cpf'])
        a_sus = limpar_numero(a['sus'])
        
        # Valida os dados históricos
        a_cpf_ok = a_cpf if valida_cpf(a_cpf) else ""
        a_sus_ok = a_sus if valida_cns(a_sus) else ""
        
        cursor.execute("UPDATE atendimentos SET cpf=?, sus=? WHERE id=?", (a_cpf_ok, a_sus_ok, id_atend))

    conn.commit()
    conn.close()
    print("✅ Faxina e Auditoria Concluídas! O seu Banco de Dados agora é impenetrável.")

if __name__ == '__main__':
    fazer_faxina()