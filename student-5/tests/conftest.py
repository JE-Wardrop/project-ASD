"""Shared fixtures for the student-5 test-suite.

The three services under student-5/ are plain scripts (no package), and the
backend uses top-level imports such as ``from routes.normal_ui import bp`` and
``from services import database_api as db``.  To import them from the test-suite
we put ``backend/`` on ``sys.path`` and load each ``app.py`` under an explicit
module name so the two ``app.py`` files do not collide.
"""

#  This file do 2 things:
# 1. Make the backend and database service modules importable from the test suite.
# 2. Provide client and fake database to test calling

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


#  Change the module name to avoid collisions between the app.py (backend) and app.py (database) files.
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# fake requests.Response when the backend calls the downstream services.  The backend expects a ``.json()`` method and a ``.status_code`` attribute.
class _FakeResp:
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
# Run student-5/backend/app.py and make it importable as "student5_backend_app".  The backend module is imported by the client fixture and the services fixture.
# scope="session" so the backend module is only loaded once per test session, and the same instance is used for all tests.
@pytest.fixture(scope="session")
def backend_module():
    return _load("student5_backend_app", BACKEND_DIR / "app.py")


@pytest.fixture
# Run backend_module() first so the function can reference to the backend_module.app object.
def client(backend_module):
    backend_module.app.config.update(TESTING=True)
    # app.test_client() is a Flask test client, allow us to make requests to the backend without running a server.
    return backend_module.app.test_client()


@pytest.fixture
def services(backend_module):
    import services.accounts_api as accounts_api
    import services.database_api as database_api
    import services.notifications_api as notifications_api
    from types import SimpleNamespace

    # Pack 3 module into 1 object -> services.db, services.accounts, services.notify
    return SimpleNamespace(
        db=database_api,
        accounts=accounts_api,
        notify=notifications_api,
    )


# --------------------------------------------------------------------------- #
# Database service                                                            #
# --------------------------------------------------------------------------- #
# DB test running real sql but in a temporary SQLite file.  
@pytest.fixture
def db_service(monkeypatch, tmp_path):
    # The database service wired to a fresh SQLite file (schema + seed)
    # run database/app.py, set the module name as student5_db_serivce
    module = _load("student5_db_service", DATABASE_DIR / "app.py")

    # Select the db file in the temporary path (not a real database file)
    db_file = tmp_path / "transactions.db"
    #  Force the database service to use the temporary SQLite file instead of the real database file
    monkeypatch.setattr(module, "DB_PATH", str(db_file))

    # Create the database file and populate it with schema and seed data
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

