import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_FOLDER = tempfile.TemporaryDirectory(prefix="agentcity-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(TEST_FOLDER.name) / 'test.sqlite3').as_posix()}"
os.environ["DEMO_ENABLED"] = "true"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["COOKIE_SECURE"] = "false"

from app.main import app, engine  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
    TEST_FOLDER.cleanup()
