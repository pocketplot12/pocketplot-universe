"""
Share token tests: create game/read tokens, validate, revoke, play session.
"""
import secrets
import datetime as dt
import sys
sys.path.insert(0, '/root/pocketplot')

import engagement


def test_create_share_token(db, test_user, test_world):
    """create_share_token returns a URL-safe token."""
    tok = engagement.create_share_token(db, test_user['id'], test_world['id'], kind='game')
    assert tok['token'] is not None
    assert len(tok['token']) >= 8
    assert tok['kind'] == 'game'
    assert tok['world_id'] == test_world['id']


def test_lookup_share_token(db, test_user, test_world):
    """lookup_share_token finds a valid token."""
    created = engagement.create_share_token(db, test_user['id'], test_world['id'], kind='read')
    found = engagement.lookup_share_token(db, created['token'])
    assert found is not None
    assert found['token'] == created['token']


def test_revoke_share_token(db, test_user, test_world):
    """revoke_share_token marks the token as revoked."""
    created = engagement.create_share_token(db, test_user['id'], test_world['id'], kind='game')
    success = engagement.revoke_share_token(db, created['token'], test_user['id'])
    assert success is True
    found = engagement.lookup_share_token(db, created['token'])
    assert found is None  # revoked tokens aren't returned


def test_player_session_advance(db, test_user, test_world):
    """Player sessions can be created and advanced."""
    tok = engagement.create_share_token(db, test_user['id'], test_world['id'], kind='game')
    sess = engagement.create_player_session(db, tok['id'])
    assert sess['share_token_id'] == tok['id']
    # Advance (session_id, next_episode, path_addition)
    engagement.advance_player_session(db, sess['id'], next_episode=2, path_addition=0)
    # Verify
    cur = db.execute("SELECT current_episode FROM player_sessions WHERE id=?",
                     (sess['id'],)).fetchone()
    assert cur[0] == 2


def test_record_play(db, test_user, test_world):
    """record_play increments play_count."""
    tok = engagement.create_share_token(db, test_user['id'], test_world['id'], kind='game')
    engagement.record_play(db, tok['id'])
    engagement.record_play(db, tok['id'])
    row = db.execute("SELECT play_count FROM share_tokens WHERE id=?", (tok['id'],)).fetchone()
    assert row[0] == 2
