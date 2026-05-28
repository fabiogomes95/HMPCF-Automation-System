import sqlite3

def padronizar_sqlite_para_firebird():
    print("⏳ Conectando ao banco SQLite (hospital.db)...")
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    try:
        # 1. Limpa tentativa anterior (caso tenha dado erro)
        cursor.execute("DROP TABLE IF EXISTS CADCNS_SQLITE;")

        # 2. Cria a nova tabela misturando o padrão Firebird + os seus dados do painel
        print("⏳ Criando nova tabela padronizada 'CADCNS_SQLITE'...")
        cursor.execute('''
            CREATE TABLE CADCNS_SQLITE (
                -- CAMPOS PADRÃO FIREBIRD (CADCNS)
                CNS TEXT,
                NUM_CPF TEXT,
                NOME TEXT,
                DTNASC TEXT,
                SEXO TEXT,
                RACA TEXT,
                MAEPCN TEXT,
                LOGPCN TEXT,          -- Receberá os dados de 'endereco'
                NUMPCN TEXT,          -- Receberá os dados de 'numero'
                BAIRRO_PCNTE TEXT,    -- Receberá os dados de 'bairro'
                CEPPCN TEXT,          -- Fixo: 59575000
                IBGE TEXT,            -- Fixo: 240360 (Extremoz)
                ETNIA TEXT,           -- Vazio (não é obrigatório)
                NACIONALIDADE TEXT,   -- Receberá os dados de 'naturalidade'
                
                -- CAMPOS EXCLUSIVOS DO SEU PAINEL (Para você não perder seus dados)
                NOME_SOCIAL TEXT,
                IDADE TEXT,
                ESTADO_CIVIL TEXT,
                OCUPACAO TEXT,
                RESPONSAVEL TEXT,
                TELEFONE TEXT,        -- Receberá os dados de 'tel'
                CIDADE TEXT,
                ESTADO TEXT
            )
        ''')

        # 3. Faz o DE -> PARA (Migração e formatação)
        print("⏳ Fazendo o 'De -> Para' e formatando os dados...")
        cursor.execute('''
            INSERT INTO CADCNS_SQLITE (
                CNS, NUM_CPF, NOME, DTNASC, SEXO, RACA, MAEPCN, LOGPCN, NUMPCN, 
                BAIRRO_PCNTE, CEPPCN, IBGE, ETNIA, NACIONALIDADE, NOME_SOCIAL, 
                IDADE, ESTADO_CIVIL, OCUPACAO, RESPONSAVEL, TELEFONE, CIDADE, ESTADO
            )
            SELECT 
                sus,                                    -- Vai para CNS
                cpf,                                    -- Vai para NUM_CPF
                nome,                                   -- Vai para NOME
                REPLACE(dn, '-', ''),                   -- Vai para DTNASC (Remove os traços)
                UPPER(sexo),                            -- Vai para SEXO
                CASE UPPER(TRIM(raca))                  -- Vai para RACA (Converte para código)
                    WHEN 'BRANCA' THEN '01'
                    WHEN 'PRETA' THEN '02'
                    WHEN 'PARDA' THEN '03'
                    WHEN 'AMARELA' THEN '04'
                    WHEN 'INDIGENA' THEN '05'
                    WHEN 'INDÍGENA' THEN '05'
                    ELSE '99'
                END,
                mae,                                    -- Vai para MAEPCN
                endereco,                               -- Mapeamento corrigido: endereco -> LOGPCN
                numero,                                 -- Mapeamento corrigido: numero -> NUMPCN
                bairro,                                 -- Mapeamento corrigido: bairro -> BAIRRO_PCNTE
                '59575000',                             -- CEPPCN (Fixo)
                '240360',                               -- IBGE (Fixo)
                '',                                     -- ETNIA (Vazio)
                naturalidade,                           -- Vai para NACIONALIDADE
                nomeSocial,                             -- Mantém no SQLite
                idade,                                  -- Mantém no SQLite
                civil,                                  -- Mantém no SQLite
                ocupacao,                               -- Mantém no SQLite
                responsavel,                            -- Mantém no SQLite
                tel,                                    -- Mantém no SQLite
                cidade,                                 -- Mantém no SQLite
                estado                                  -- Mantém no SQLite
            FROM pacientes;
        ''')

        # 4. Troca os nomes das tabelas para o seu painel continuar rodando
        print("⏳ Substituindo tabelas...")
        cursor.execute("ALTER TABLE pacientes RENAME TO pacientes_backup;")
        cursor.execute("ALTER TABLE CADCNS_SQLITE RENAME TO pacientes;")

        conn.commit()
        print("\n✅ BANCO PADRONIZADO COM SUCESSO!")
        print("✅ O Opencode agora reconhecerá a tabela 'pacientes' com as colunas do Firebird.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro durante a padronização: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    padronizar_sqlite_para_firebird()