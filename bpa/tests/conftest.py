import os

# Nos testes a migração automática nunca dispara sozinha (ela iria ao
# PostgreSQL de verdade); os testes dela chamam as funções diretamente.
os.environ["BPA_MIGRACAO_AUTO"] = "0"
