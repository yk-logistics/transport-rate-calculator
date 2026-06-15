import os
import tempfile
import pytest

# Force a throwaway SQLite DB BEFORE importing the app/db modules.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "test-secret-key-not-for-prod"

from starlette.testclient import TestClient  # noqa: E402
import main as appmod  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(appmod.app) as c:
        yield c
