"""O fallback do frontend (main.spa_fallback) nunca pode servir arquivo de fora
de frontend/dist -- antes, GET /../../backend/.env devolvia a senha do banco."""
import pytest
from fastapi.testclient import TestClient

from app.main import DIST, app

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="precisa do build do frontend (frontend/dist)")

ESCAPES = [
    "/%2e%2e/%2e%2e/backend/.env",
    "/..%2f..%2fbackend%2f.env",
    "/%2e%2e/%2e%2e/backend/app/main.py",
]


@pytest.mark.parametrize("caminho", ESCAPES)
def test_caminho_com_ponto_ponto_nao_sai_do_dist(caminho):
    resp = TestClient(app).get(caminho)
    assert "POSTGRES" not in resp.text
    assert "spa_fallback" not in resp.text
    assert resp.content == (DIST / "index.html").read_bytes()


def test_arquivo_do_dist_continua_sendo_servido():
    resp = TestClient(app).get("/index.html")
    assert resp.status_code == 200
    assert resp.content == (DIST / "index.html").read_bytes()
