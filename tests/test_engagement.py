"""
Engagement tests: likes, comments, reactions, view counter.
"""
import sys
sys.path.insert(0, '/root/pocketplot')

import engagement
import social


def test_like_world(db, test_user, test_world):
    """like_world adds a like; unlike_world removes it."""
    # First like - returns True (newly liked)
    r1 = engagement.like_world(db, test_user['id'], test_world['id'])
    assert r1 is True
    # Already liked - returns False (IntegrityError)
    r2 = engagement.like_world(db, test_user['id'], test_world['id'])
    assert r2 is False
    # Unlike - returns True
    r3 = engagement.unlike_world(db, test_user['id'], test_world['id'])
    assert r3 is True
    # Like again - True
    r4 = engagement.like_world(db, test_user['id'], test_world['id'])
    assert r4 is True


def test_like_count(db, test_user, test_world):
    """like_count returns the total."""
    engagement.like_world(db, test_user['id'], test_world['id'])
    assert engagement.like_count(db, test_world['id']) == 1
    # Note: like_world doesn't toggle, so we need to delete manually to test 0
    db.execute("DELETE FROM likes WHERE subscriber_id=? AND world_id=?",
               (test_user['id'], test_world['id']))
    db.commit()
    assert engagement.like_count(db, test_world['id']) == 0


def test_is_liked(db, test_user, test_world):
    """is_liked returns True if the user liked."""
    assert engagement.is_liked(db, test_user['id'], test_world['id']) is False
    engagement.like_world(db, test_user['id'], test_world['id'])
    assert engagement.is_liked(db, test_user['id'], test_world['id']) is True


def test_add_comment(db, test_user, test_world):
    """add_comment creates a comment."""
    cid = social.add_comment(db, test_world['id'], test_user['id'], 'Hello world')
    assert cid is not None
    assert cid > 0


def test_add_comment_rejects_empty(db, test_user, test_world):
    """add_comment raises ValueError on empty body."""
    import pytest
    with pytest.raises(ValueError):
        social.add_comment(db, test_world['id'], test_user['id'], '')
    with pytest.raises(ValueError):
        social.add_comment(db, test_world['id'], test_user['id'], '   ')


def test_list_comments(db, test_user, test_world):
    """list_comments returns top-level + replies."""
    cid1 = social.add_comment(db, test_world['id'], test_user['id'], 'Top-level')
    cid2 = social.add_comment(db, test_world['id'], test_user['id'], 'Reply', parent_id=cid1)
    comments = social.list_comments(db, test_world['id'])
    assert len(comments) == 1  # one top-level
    assert comments[0]['id'] == cid1
    assert len(comments[0]['replies']) == 1
    assert comments[0]['replies'][0]['id'] == cid2


def test_soft_delete_comment(db, test_user, test_world):
    """soft_delete_comment hides the body but keeps structure."""
    cid = social.add_comment(db, test_world['id'], test_user['id'], 'Original')
    deleted = social.soft_delete_comment(db, cid, subscriber_id=test_user['id'])
    assert deleted is True
    # Re-list, body should be [deleted]
    comments = social.list_comments(db, test_world['id'])
    assert comments[0]['body'] == '[deleted]'


def test_soft_delete_unauthorized(db, test_user, test_world):
    """soft_delete_comment rejects non-author non-admin."""
    import sqlite3
    # Create another user
    db.execute("INSERT INTO subscribers(email, child_name, child_age, active, created_at, plan) "
               "VALUES (?, ?, ?, 1, '2026-01-01', 'free')", ('other@example.com', 'Other', 7))
    db.commit()
    other_id = db.execute("SELECT id FROM subscribers WHERE email=?",
                          ('other@example.com',)).fetchone()[0]
    cid = social.add_comment(db, test_world['id'], test_user['id'], 'Original')
    # Try to delete as other user
    deleted = social.soft_delete_comment(db, cid, subscriber_id=other_id)
    assert deleted is False


def test_toggle_reaction(db, test_user, test_world):
    """toggle_reaction adds then removes."""
    r1 = social.toggle_reaction(db, test_world['id'], test_user['id'], 'heart')
    assert r1 == 'added'
    r2 = social.toggle_reaction(db, test_world['id'], test_user['id'], 'heart')
    assert r2 == 'removed'


def test_reaction_counts(db, test_user, test_world):
    """reaction_counts returns counts per kind."""
    social.toggle_reaction(db, test_world['id'], test_user['id'], 'heart')
    social.toggle_reaction(db, test_world['id'], test_user['id'], 'fire')
    counts = social.reaction_counts(db, test_world['id'])
    assert counts['heart'] == 1
    assert counts['fire'] == 1
    assert counts['sparkles'] == 0


def test_reaction_invalid_kind(db, test_user, test_world):
    """toggle_reaction raises ValueError on unknown kind."""
    import pytest
    with pytest.raises(ValueError):
        social.toggle_reaction(db, test_world['id'], test_user['id'], 'unknown_kind')
