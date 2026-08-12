import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_catalogiq.db"
Path("test_catalogiq.db").unlink(missing_ok=True)

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
