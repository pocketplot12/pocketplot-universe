"""
PocketPlot Universe - test suite (v25).

Run with:
  cd /root/pocketplot
  /usr/bin/python3 -m pytest tests/ -v
"""
import os
import sys
import pytest
import secrets as _secrets

sys.path.insert(0, '/root/pocketplot')

TEST_DB_PATH = '/root/pocketplot/tests/test_pocketplot.db'

os.environ['POCKETPLOT_SECRET'] = 'test-secret-' + _secrets.token_hex(16)
os.environ['POCKETPLOT_ADMIN_EMAIL'] = 'test-admin@pocketplot.local'

# Patch sqlite3.connect BEFORE any test imports happen
import sqlite3 as _sqlite3
_original_connect = _sqlite3.connect


def patched_connect(path, *args, **kwargs):
    # Handle both str and PathLike
    path_str = str(path) if path is not None else ''
    if 'pocketplot.db' in path_str and 'test' not in path_str:
        path = TEST_DB_PATH
    return _original_connect(path, *args, **kwargs)


_sqlite3.connect = patched_connect


def _init_test_db():
    """Initialize the test database fresh."""
    import importlib

    # Remove old test DB
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)

    # Force reimport to pick up the patched connect
    for mod_name in list(sys.modules.keys()):
        if mod_name in ('app', 'migrations_phase11', 'migrations_phase17',
                        'migrations_phase23', 'migrations_phase24',
                        'engagement', 'exports', 'promo', 'qrcode_lib',
                        'analytics', 'follows', 'validation_system',
                        'external_api_manager', 'pocketplot_api'):
            del sys.modules[mod_name]

    import app as app_module
    app_module.init_db()
    return TEST_DB_PATH


@pytest.fixture(scope='session', autouse=True)
def session_init():
    """Initialize the test DB once for the session."""
    _init_test_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)


@pytest.fixture
def db(session_init):
    """Direct DB connection. Each test gets a fresh DB."""
    _init_test_db()
    conn = _original_connect(TEST_DB_PATH)
    conn.row_factory = _sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def app(db):
    """Create the Flask app with test config."""
    if 'app' in sys.modules:
        del sys.modules['app']
    import app as app_module
    app_module.app.config['TESTING'] = True
    app_module.app.config['WTF_CSRF_ENABLED'] = False
    return app_module.app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    import datetime as dt
    db.execute(
        "INSERT INTO subscribers(email, child_name, child_age, active, created_at, plan) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ('test@example.com', 'Test Child', 8, 1,
         dt.datetime.utcnow().isoformat(timespec='seconds'),
         'free'),
    )
    db.commit()
    user_id = db.execute("SELECT id FROM subscribers WHERE email=?",
                          ('test@example.com',)).fetchone()[0]
    return {'id': user_id, 'email': 'test@example.com', 'child_name': 'Test Child', 'plan': 'free'}


@pytest.fixture
def auth_client(client, test_user, db):
    """Test client with a logged-in session."""
    import datetime as dt
    token = _secrets.token_urlsafe(32)
    now = dt.datetime.utcnow()
    expires = now + dt.timedelta(hours=1)
    db.execute(
        "INSERT INTO magic_tokens(token, subscriber_id, purpose, created_at, expires_at, used) "
        "VALUES (?, ?, 'login', ?, ?, 0)",
        (token, test_user['id'], now.isoformat(timespec='seconds'), expires.isoformat(timespec='seconds')),
    )
    db.commit()
    client.get(f'/login/{token}')
    return client


@pytest.fixture
def test_world(db, test_user):
    """Create a test world with 4 episodes."""
    import datetime as dt
    now = dt.datetime.utcnow().isoformat(timespec='seconds')
    db.execute(
        "INSERT INTO worlds(subscriber_id, title, genre, tone, setting, seed, "
        "is_public, slug, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (test_user['id'], 'Test World', 'fantasy', 'mysterious',
         'A small lantern-lit quarter', 12345, 1, 'test-world', now),
    )
    world_id = db.execute("SELECT id FROM worlds WHERE subscriber_id=? ORDER BY id DESC LIMIT 1",
                          (test_user['id'],)).fetchone()[0]
    for i in range(1, 5):
        db.execute(
            "INSERT INTO world_episodes(world_id, subscriber_id, episode_number, title, body, choices_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (world_id, test_user['id'], i, f'Episode {i}', f'Body of episode {i}.', '[]', now),
        )
    db.commit()
    return {'id': world_id, 'title': 'Test World', 'subscriber_id': test_user['id']}
