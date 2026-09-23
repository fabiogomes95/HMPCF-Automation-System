"""BPA local (FastAPI) — roda em cada notebook do faturamento, ao lado do
Firebird e do BPA Magnético. Mesmo padrão em camadas do backend:
api (rotas finas) → services (regras) → domínio validado (bpa_gerador,
conferencia, fechamento_mes)."""

# Carrega os .env antes de qualquer submódulo importar o bpa_gerador (ele lê
# FIREBIRD_* e BPA_LOTES_DIR do ambiente na importação).
from bpa_local import config  # noqa: F401
