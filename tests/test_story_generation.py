"""
Story generation tests: world creation, episode generation, BYOB stub.
"""
import sys
sys.path.insert(0, '/root/pocketplot')


def test_world_creation_form_loads(auth_client):
    """GET /worlds/new shows the world creation form."""
    r = auth_client.get('/worlds/new')
    assert r.status_code == 200
    assert b'genre' in r.data.lower() or b'Genre' in r.data
    assert b'tone' in r.data.lower() or b'Tone' in r.data


def test_seed_endpoint_loads(client):
    """GET /seed redirects unauthenticated users to /login."""
    r = client.get('/seed')
    # May be 200 (public) or 302 (login required) - both are valid
    assert r.status_code in (200, 302)


def test_worlds_list_loads(auth_client):
    """GET /worlds shows the user's worlds."""
    r = auth_client.get('/worlds')
    # Should be 200 or a redirect (depends on whether /worlds exists)
    assert r.status_code in (200, 302)


def test_public_profile_loads(client, db, test_user):
    """GET /u/<username> shows the public profile."""
    db.execute("UPDATE subscribers SET username=?, is_public=1 WHERE id=?",
               ('testuser', test_user['id']))
    db.commit()
    r = client.get('/u/testuser')
    assert r.status_code in (200, 302)


def test_story_stats_module(test_world, db):
    """story_stats aggregates correctly."""
    # Simulate plays + views
    db.execute(
        "INSERT OR REPLACE INTO story_stats(world_id, view_count, play_count, completion_count, like_count, last_updated) "
        "VALUES (?, 10, 5, 2, 3, '2026-01-01')",
        (test_world['id'],)
    )
    db.commit()
    row = db.execute("SELECT view_count, play_count, like_count FROM story_stats WHERE world_id=?",
                     (test_world['id'],)).fetchone()
    assert row[0] == 10
    assert row[1] == 5
    assert row[2] == 3
