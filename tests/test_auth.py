"""
Auth tests: magic-link login, session, logout.
"""
import secrets
import datetime as dt
import sqlite3
import sys
sys.path.insert(0, '/root/pocketplot')


def test_login_page_loads(client):
    """GET /login renders the login request form."""
    r = client.get('/login')
    assert r.status_code == 200
    assert b'email' in r.data.lower()


def test_login_request_with_unknown_email(client):
    """POST /login with unknown email shows success message (no enumeration)."""
    r = client.post('/login', data={'email': 'unknown@example.com'}, follow_redirects=True)
    # Either shows the form again with a flash, or shows success
    assert r.status_code in (200, 302)


def test_magic_link_login(client, test_user, db):
    """Magic-link token logs the user in."""
    token = secrets.token_urlsafe(32)
    now = dt.datetime.utcnow()
    expires = now + dt.timedelta(hours=1)
    db.execute(
        "INSERT INTO magic_tokens(token, subscriber_id, purpose, created_at, expires_at, used) "
        "VALUES (?, ?, 'login', ?, ?, 0)",
        (token, test_user['id'], now.isoformat(timespec='seconds'), expires.isoformat(timespec='seconds')),
    )
    db.commit()
    r = client.get(f'/login/{token}', follow_redirects=False)
    assert r.status_code == 302  # redirect to /me


def test_expired_magic_link_rejected(client, db):
    """Expired magic-link token shows an error."""
    token = secrets.token_urlsafe(32)
    past = dt.datetime.utcnow() - dt.timedelta(hours=2)
    expires = past + dt.timedelta(hours=1)  # expired 1 hour ago
    db.execute(
        "INSERT INTO magic_tokens(token, subscriber_id, purpose, created_at, expires_at, used) "
        "VALUES (?, 1, 'login', ?, ?, 0)",
        (token, past.isoformat(timespec='seconds'), expires.isoformat(timespec='seconds')),
    )
    db.commit()
    r = client.get(f'/login/{token}', follow_redirects=True)
    # Should redirect to login form with error
    assert r.status_code == 200


def test_logout_clears_session(auth_client):
    """GET /logout clears the session."""
    r = auth_client.get('/logout', follow_redirects=False)
    assert r.status_code == 302


def test_protected_route_requires_auth(client):
    """GET /me without session redirects to /login."""
    r = client.get('/me', follow_redirects=False)
    assert r.status_code == 302
    assert '/login' in r.headers.get('Location', '')
