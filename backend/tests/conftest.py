"""Testes executam contra PostgreSQL real (banco de teste dedicado).

Variável: DVI_TEST_DATABASE_URL (padrão: postgresql+psycopg://dvi:dvi_dev@localhost:5432/dvi_test).
O banco de teste é recriado (schema public) no início da sessão de testes.
"""

import os
import tempfile

import pytest

TEST_DB = os.environ.get("DVI_TEST_DATABASE_URL", "postgresql+psycopg://dvi:dvi_dev@localhost:5432/dvi_test")
os.environ["DVI_DATABASE_URL"] = TEST_DB
os.environ["DVI_STORAGE_DIR"] = tempfile.mkdtemp(prefix="dvi-test-storage-")
os.environ["DVI_MAX_UPLOAD_MB"] = "2"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import SessionLocal, reset_engine  # noqa: E402

LAB_PASSWORD = "senha-de-laboratorio-teste"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def database():
    get_settings.cache_clear()
    eng = create_engine(TEST_DB)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    eng.dispose()
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(cfg, "head")
    reset_engine()
    from app.seed import demo_records, ensure_reference_data

    with SessionLocal() as db:
        op = ensure_reference_data(db, LAB_PASSWORD)
        demo_records(db, op)
        db.commit()
    yield


class Api:
    """Cliente autenticado com contexto, como o frontend."""

    def __init__(self, username: str | None = None):
        from app.main import app

        self.c = TestClient(app, headers={"x-dvi-request": "1"})
        self.me = None
        if username:
            r = self.c.post("/api/auth/login", json={"username": username, "password": LAB_PASSWORD})
            assert r.status_code == 200, r.text
            self.me = self.c.get("/api/auth/me").json()

    def auth_for(self, base_code: str, role: str) -> dict:
        for a in self.me["authorizations"]:
            if a["base"]["code"] == base_code and a["role"] == role:
                return a
        raise AssertionError(f"autorização {base_code}/{role} não encontrada")

    def use(self, base_code: str, role: str):
        a = self.auth_for(base_code, role)
        r = self.c.put("/api/auth/context", json={"operation_id": a["operation"]["id"],
                                                  "base_id": a["base"]["id"], "role": role})
        assert r.status_code == 200, r.text
        return self

    def __getattr__(self, name):
        return getattr(self.c, name)


@pytest.fixture
def api():
    return Api


@pytest.fixture
def am_user():
    return Api("operador.am").use("AM", "OPERADOR_AM")


@pytest.fixture
def pm_user():
    return Api("operador.pm").use("PM", "OPERADOR_PM")


@pytest.fixture
def reviewer():
    return Api("revisor").use("COMANDO", "REVISOR_RECONCILIACAO")
