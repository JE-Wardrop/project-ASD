"""Shared fixtures for the student-5 test-suite.

The three services under student-5/ are plain scripts (no package), and the
backend uses top-level imports such as ``from routes.normal_ui import bp`` and
``from services import database_api as db``.  To import them from the test-suite
we put ``backend/`` on ``sys.path`` and load each ``app.py`` under an explicit
module name so the two ``app.py`` files do not collide.
"""

import importlib.util
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent          # student-5/
BACKEND_DIR = ROOT / "backend"
DATABASE_DIR = ROOT / "database"

# Backend uses package-style imports -> backend/ must be importable.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _FakeResp:
    """Stand-in for a ``requests.Response`` returned by a downstream service."""

    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.fixture
def FakeResp():
    return _FakeResp


# --------------------------------------------------------------------------- #
# Backend service                                                             #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def backend_module():
    return _load("student5_backend_app", BACKEND_DIR / "app.py")


@pytest.fixture
def client(backend_module):
    backend_module.app.config.update(TESTING=True)
    return backend_module.app.test_client()


@pytest.fixture
def services(backend_module):
    """The three downstream-service modules the backend routes talk to."""
    import services.accounts_api as accounts_api
    import services.database_api as database_api
    import services.notifications_api as notifications_api
    from types import SimpleNamespace

    return SimpleNamespace(
        db=database_api,
        accounts=accounts_api,
        notify=notifications_api,
    )


# --------------------------------------------------------------------------- #
# Database service                                                            #
# --------------------------------------------------------------------------- #
@pytest.fixture
def db_service(monkeypatch, tmp_path):
    """The database service wired to a fresh SQLite file (schema + seed)."""
    module = _load("student5_db_service", DATABASE_DIR / "app.py")

    db_file = tmp_path / "transactions.db"
    monkeypatch.setattr(module, "DB_PATH", str(db_file))

    con = sqlite3.connect(db_file)
    con.executescript(pathlib.Path(module.SCHEMA_PATH).read_text(encoding="utf-8"))
    con.executescript(pathlib.Path(module.SEED_PATH).read_text(encoding="utf-8"))
    con.commit()
    con.close()

    module.app.config.update(TESTING=True)
    return module


@pytest.fixture
def db_client(db_service):
    return db_service.app.test_client()
