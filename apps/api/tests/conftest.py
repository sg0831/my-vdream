import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["APP_ENV"] = "test"
os.environ["SEED_ON_EMPTY"] = "false"
os.environ["UPLOAD_DIR"] = "./test_uploads"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import reset_and_seed  # noqa: E402


@pytest.fixture(scope="session")
def client():
    reset_and_seed()
    with TestClient(app) as c:
        yield c


def login(client, role: str) -> dict:
    r = client.post("/api/v1/auth/demo-login", json={"role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['token']}"}
