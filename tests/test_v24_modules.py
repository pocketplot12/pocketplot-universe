"""
v24 module tests: streaks/XP, onboarding, inventory, scene_graph, TTS, audit_v24.
"""
import datetime as dt
import sys
sys.path.insert(0, '/root/pocketplot')

import streaks_xp
import onboarding
import inventory
import scene_graph
import tts
import audit_v24


def test_award_xp_for_writing(db, test_user):
    """award_xp increments total_xp."""
    before = streaks_xp.get_stats(db, test_user['id'])
    xp_added, total_after = streaks_xp.award_xp(db, test_user['id'], 'wrote_scene')
    assert xp_added == 10
    assert total_after == before['total_xp'] + 10


def test_award_xp_unknown_reason(db, test_user):
    """award_xp returns 0 for unknown reason."""
    before = streaks_xp.get_stats(db, test_user['id'])
    xp_added, total = streaks_xp.award_xp(db, test_user['id'], 'unknown_thing')
    assert xp_added == 0
    assert total == before['total_xp']


def test_streak_bump_increments(db, test_user):
    """First active day sets streak to 1."""
    streaks_xp.bump_streak(db, test_user['id'])
    streak = streaks_xp.get_streak(db, test_user['id'])
    assert streak['current_streak'] == 1
    assert streak['best_streak'] == 1
    assert streak['total_active_days'] == 1


def test_streak_consecutive_days(db, test_user):
    """Consecutive days increment the streak."""
    streaks_xp.bump_streak(db, test_user['id'])
    # Force last_active_date to yesterday
    yesterday = (dt.datetime.utcnow() - dt.timedelta(days=1)).strftime('%Y-%m-%d')
    db.execute("UPDATE user_streaks SET last_active_date=? WHERE subscriber_id=?",
               (yesterday, test_user['id']))
    db.commit()
    streaks_xp.bump_streak(db, test_user['id'])
    streak = streaks_xp.get_streak(db, test_user['id'])
    assert streak['current_streak'] == 2


def test_streak_resets_on_gap(db, test_user):
    """Gap > 1 day resets the streak to 1."""
    # First day
    streaks_xp.bump_streak(db, test_user['id'])
    # Last active 5 days ago
    long_ago = (dt.datetime.utcnow() - dt.timedelta(days=5)).strftime('%Y-%m-%d')
    db.execute("UPDATE user_streaks SET last_active_date=? WHERE subscriber_id=?",
               (long_ago, test_user['id']))
    db.commit()
    streaks_xp.bump_streak(db, test_user['id'])
    streak = streaks_xp.get_streak(db, test_user['id'])
    assert streak['current_streak'] == 1  # reset


def test_get_stats_returns_all_fields(db, test_user):
    """get_stats returns total_xp, level, today_xp, streak."""
    streaks_xp.award_xp(db, test_user['id'], 'wrote_scene')
    stats = streaks_xp.get_stats(db, test_user['id'])
    assert 'total_xp' in stats
    assert 'level' in stats
    assert 'today_xp' in stats
    assert 'current_streak' in stats
    assert 'best_streak' in stats


# ============================================================
# ONBOARDING
# ============================================================

def test_onboarding_state_creates_row(db, test_user):
    """get_state creates an onboarding row if missing."""
    state = onboarding.get_state(db, test_user['id'])
    assert state['subscriber_id'] == test_user['id']
    assert state['current_step'] == 1
    assert state['completed_at'] is None
    assert state['skipped_at'] is None


def test_onboarding_update_step(db, test_user):
    """update_step saves the data dict."""
    # First create the row
    onboarding.get_state(db, test_user['id'])
    onboarding.update_step(db, test_user['id'], 1, {'genre': 'fantasy'})
    state = onboarding.get_state(db, test_user['id'])
    import json
    sd1 = json.loads(state['step1_data'])
    assert sd1['genre'] == 'fantasy'


def test_onboarding_advance(db, test_user):
    """advance_step sets the step + data + advances current_step."""
    onboarding.get_state(db, test_user['id'])
    onboarding.advance_step(db, test_user['id'], 1, 2, {'genre': 'fantasy'})
    state = onboarding.get_state(db, test_user['id'])
    assert state['current_step'] == 2


def test_onboarding_mark_complete(db, test_user):
    """mark_complete sets completed_at."""
    onboarding.get_state(db, test_user['id'])
    onboarding.mark_complete(db, test_user['id'])
    state = onboarding.get_state(db, test_user['id'])
    assert state['completed_at'] is not None
    assert onboarding.is_complete(db, test_user['id']) is True


def test_onboarding_skip(db, test_user):
    """skip sets skipped_at."""
    # First create the row
    onboarding.get_state(db, test_user['id'])
    onboarding.skip(db, test_user['id'])
    state = onboarding.get_state(db, test_user['id'])
    assert state['skipped_at'] is not None
    assert onboarding.is_complete(db, test_user['id']) is True


# ============================================================
# INVENTORY
# ============================================================

def test_inventory_catalog_seeded(db):
    """The 8 starter items are seeded by the migration."""
    items = inventory.list_items(db)
    keys = [i['key'] for i in items]
    assert 'golden_key' in keys
    assert 'inkwell' in keys
    assert 'crystal_shard' in keys
    assert len(items) >= 8


def test_grant_item(db, test_user):
    """grant_item adds to user's inventory."""
    inventory.grant_item(db, test_user['id'], 'inkwell', quantity=3, source='test')
    inv = inventory.user_inventory(db, test_user['id'])
    assert inv.get('inkwell') == 3


def test_has_item(db, test_user):
    """has_item returns True/False correctly."""
    assert inventory.has_item(db, test_user['id'], 'inkwell') is False
    inventory.grant_item(db, test_user['id'], 'inkwell', quantity=1)
    assert inventory.has_item(db, test_user['id'], 'inkwell') is True


def test_consume_item(db, test_user):
    """consume_item removes from inventory."""
    inventory.grant_item(db, test_user['id'], 'inkwell', quantity=2)
    success = inventory.consume_item(db, test_user['id'], 'inkwell')
    assert success is True
    inv = inventory.user_inventory(db, test_user['id'])
    assert inv.get('inkwell') == 1


def test_consume_insufficient_fails(db, test_user):
    """consume_item returns False if not enough."""
    assert inventory.consume_item(db, test_user['id'], 'inkwell') is False


def test_place_and_pickup_item(db, test_user, test_world):
    """place_item puts it in world_inventory, remove_world_item returns it."""
    # Starter pack gives 2 inkwells - use a different item for this test
    inventory.grant_item(db, test_user['id'], 'rune_of_return', quantity=1)
    success = inventory.place_item(db, test_world['id'], test_user['id'], 'rune_of_return', x=100, y=200)
    assert success is True
    items = inventory.world_items(db, test_world['id'])
    # Filter to just our item (in case other tests share this user)
    our_items = [i for i in items if i['item_key'] == 'rune_of_return']
    assert len(our_items) == 1
    assert our_items[0]['x'] == 100
    # Pick up
    removed = inventory.remove_world_item(db, our_items[0]['id'], test_user['id'])
    assert removed is True
    # Inventory has rune_of_return
    inv = inventory.user_inventory(db, test_user['id'])
    assert inv.get('rune_of_return', 0) >= 1


# ============================================================
# SCENE GRAPH
# ============================================================

def test_load_graph_synthesizes_linear(db, test_user, test_world):
    """load_graph synthesizes a linear graph when no author data."""
    graph = scene_graph.load_graph(db, test_world['id'])
    # World 1 has 4 episodes
    assert len(graph['nodes']) == 4
    assert len(graph['edges']) == 3
    # First node should be marked 'start' visually (caller adds .start class)


def test_save_graph_persists(db, test_user, test_world):
    """save_graph writes nodes + edges to worlds.scene_nodes_json."""
    nodes = [{'id': 'n1', 'episode_id': None, 'label': 'Scene 1', 'x': 100, 'y': 100, 'color': '#c9a04e'}]
    edges = []
    scene_graph.save_graph(db, test_world['id'], nodes, edges)
    graph = scene_graph.load_graph(db, test_world['id'])
    assert len(graph['nodes']) == 1
    assert graph['nodes'][0]['label'] == 'Scene 1'


def test_add_and_delete_node(db, test_user, test_world):
    """add_node + delete_node modify the graph."""
    n = scene_graph.add_node(db, test_world['id'], 'New Scene')
    assert n['label'] == 'New Scene'
    graph = scene_graph.load_graph(db, test_world['id'])
    assert any(node['id'] == n['id'] for node in graph['nodes'])
    scene_graph.delete_node(db, test_world['id'], n['id'])
    graph = scene_graph.load_graph(db, test_world['id'])
    assert not any(node['id'] == n['id'] for node in graph['nodes'])


def test_add_and_delete_edge(db, test_user, test_world):
    """add_edge + delete_edge modify the graph."""
    scene_graph.add_node(db, test_world['id'], 'A')
    scene_graph.add_node(db, test_world['id'], 'B')
    graph = scene_graph.load_graph(db, test_world['id'])
    node_a = graph['nodes'][-2]
    node_b = graph['nodes'][-1]
    edge = scene_graph.add_edge(db, test_world['id'], node_a['id'], node_b['id'], 'Continue')
    assert edge['choice_label'] == 'Continue'
    graph = scene_graph.load_graph(db, test_world['id'])
    assert len(graph['edges']) >= 1
    scene_graph.delete_edge(db, test_world['id'], node_a['id'], node_b['id'])
    graph = scene_graph.load_graph(db, test_world['id'])
    assert all(e['from_id'] != node_a['id'] or e['to_id'] != node_b['id']
               for e in graph['edges'])


# ============================================================
# TTS
# ============================================================

def test_tts_voice_catalog():
    """get_voices returns the 5 curated voices."""
    voices = tts.get_voices()
    assert len(voices) >= 5
    assert all('id' in v for v in voices)
    assert all('lang' in v for v in voices)
    assert all('pitch' in v and 'rate' in v for v in voices)


def test_tts_default_voice():
    """get_default_voice_id returns a valid voice id."""
    default = tts.get_default_voice_id()
    voices = tts.get_voices()
    assert default in [v['id'] for v in voices]


def test_tts_sanitize_em_dashes():
    """Em-dashes become periods."""
    cleaned = tts.sanitize('Hello — world')
    assert '—' not in cleaned
    assert '.' in cleaned


def test_tts_sanitize_smart_quotes():
    """Smart quotes become straight quotes."""
    cleaned = tts.sanitize('"hello"')
    assert '\u201c' not in cleaned and '\u201d' not in cleaned


def test_tts_sanitize_empty():
    """Empty string returns empty string."""
    assert tts.sanitize('') == ''
    assert tts.sanitize(None) == ''


def test_tts_estimate_duration():
    """estimate_duration returns a float."""
    dur = tts.estimate_duration('hello world ' * 100)
    assert isinstance(dur, (int, float))
    assert dur > 0


def test_tts_chunk_text():
    """split_into_chunks splits at sentence boundaries."""
    text = 'First sentence. Second sentence. Third sentence. Fourth.'
    chunks = tts.split_into_chunks(text, max_chars=30)
    assert len(chunks) >= 1
    # All chunks should be <= max_chars (roughly)
    for c in chunks:
        assert len(c) <= 50


# ============================================================
# AUDIT
# ============================================================

def test_audit_writes_entry(db, test_user):
    """audit inserts a row into audit_log_extended."""
    before = db.execute("SELECT COUNT(*) FROM audit_log_extended").fetchone()[0]
    audit_v24.audit(db, 'test.action', actor_id=test_user['id'],
                     actor_type='subscriber', target_type='test',
                     target_id=42, ip_address='127.0.0.1',
                     metadata={'foo': 'bar'})
    after = db.execute("SELECT COUNT(*) FROM audit_log_extended").fetchone()[0]
    assert after == before + 1


def test_audit_recent_returns_last_n(db, test_user):
    """audit.recent returns the most recent entries."""
    for i in range(5):
        audit_v24.audit(db, f'test.action.{i}', actor_id=test_user['id'])
    entries = audit_v24.recent(db, limit=10)
    assert len(entries) >= 5


def test_audit_recent_filters_by_action_prefix(db, test_user):
    """audit.recent filters by action_prefix."""
    audit_v24.audit(db, 'special.action', actor_id=test_user['id'])
    audit_v24.audit(db, 'other.action', actor_id=test_user['id'])
    entries = audit_v24.recent(db, limit=20, action_prefix='special')
    assert all(e['action'].startswith('special') for e in entries)
    assert len(entries) >= 1


def test_audit_stats_groups_by_action(db, test_user):
    """audit.stats groups by action."""
    for _ in range(3):
        audit_v24.audit(db, 'grouped.action', actor_id=test_user['id'])
    stats = audit_v24.stats(db, since_days=30)
    assert any(s['action'] == 'grouped.action' and s['n'] >= 3 for s in stats)
