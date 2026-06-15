import os
import tempfile
import pytest

# Force a throwaway SQLite DB BEFORE importing the app/db modules.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "test-secret-key-not-for-prod"

from sqlmodel import SQLModel  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from db_config import engine  # noqa: E402
import main as appmod  # noqa: E402


@pytest.fixture()
def client():
    # Fresh schema + seed per test so one test's mutations (e.g. yk1 password)
    # never leak into another. Eliminates cross-test ordering fragility.
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with TestClient(appmod.app) as c:
        yield c
