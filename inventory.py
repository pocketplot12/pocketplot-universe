"""
PocketPlot Universe - inventory + build system (v24).

Items catalog (in migrations_phase24.py):
  golden_key, silver_compass, rune_of_return, manuscript_page,
  inkwell, brass_gear, crystal_shard, map_fragment

User inventory (per subscriber):
  inventory_grants - what items they have, how many

World placement (Minecraft-style):
  world_inventory - items placed at (x, y) in a specific world
  Only Pro/Creator can place items.

History (audit):
  inventory_history - grant, transfer, place, pick_up, use
"""
import datetime as dt
import json


def _conn(db):
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


# ====================================================================
# CATALOG
# ====================================================================

def list_items(db, rarity=None):
    """List all items in the catalog, optionally filtered by rarity."""
    c = _conn(db)
    if rarity:
        rows = c.execute("SELECT * FROM inventory_items WHERE rarity=? ORDER BY rarity, name",
                         (rarity,)).fetchall()
    else:
        # Order by rarity tiers
        rows = c.execute(
            "SELECT * FROM inventory_items ORDER BY "
            "CASE rarity WHEN 'legendary' THEN 1 WHEN 'epic' THEN 2 "
            "WHEN 'rare' THEN 3 WHEN 'uncommon' THEN 4 WHEN 'common' THEN 5 END, name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_item(db, key):
    c = _conn(db)
    row = c.execute("SELECT * FROM inventory_items WHERE key=?", (key,)).fetchone()
    return dict(row) if row else None


# ====================================================================
# GRANTS
# ====================================================================

def grant_item(db, subscriber_id, item_key, quantity=1, source='admin_grant', source_id=None):
    """Grant an item to a user."""
    c = _conn(db)
    c.execute(
        "INSERT INTO inventory_grants(subscriber_id, item_key, quantity, source, source_id, granted_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (subscriber_id, item_key, quantity, source, source_id,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.execute(
        "INSERT INTO inventory_history(subscriber_id, item_key, action, quantity_delta, created_at) "
        "VALUES (?, ?, 'grant', ?, ?)",
        (subscriber_id, item_key, quantity,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.commit()


def user_inventory(db, subscriber_id):
    """Return dict of {item_key: quantity} for a user's inventory."""
    c = _conn(db)
    rows = c.execute(
        "SELECT item_key, SUM(quantity) AS total FROM inventory_grants "
        "WHERE subscriber_id=? GROUP BY item_key ORDER BY item_key",
        (subscriber_id,),
    ).fetchall()
    return {row['item_key']: row['total'] for row in rows}


def has_item(db, subscriber_id, item_key, quantity=1):
    """Return True if the user has at least `quantity` of this item."""
    inv = user_inventory(db, subscriber_id)
    return inv.get(item_key, 0) >= quantity


def consume_item(db, subscriber_id, item_key, quantity=1):
    """Consume an item. Returns True on success."""
    if not has_item(db, subscriber_id, item_key, quantity):
        return False
    c = _conn(db)
    # Insert a negative grant
    c.execute(
        "INSERT INTO inventory_grants(subscriber_id, item_key, quantity, source, granted_at) "
        "VALUES (?, ?, ?, 'consume', ?)",
        (subscriber_id, item_key, -quantity,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.execute(
        "INSERT INTO inventory_history(subscriber_id, item_key, action, quantity_delta, created_at) "
        "VALUES (?, ?, 'use', ?, ?)",
        (subscriber_id, item_key, -quantity,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.commit()
    return True


# ====================================================================
# WORLD PLACEMENT
# ====================================================================

def place_item(db, world_id, subscriber_id, item_key, x, y):
    """Place an item at (x, y) in a world."""
    if not has_item(db, subscriber_id, item_key):
        return False
    c = _conn(db)
    c.execute(
        "INSERT INTO world_inventory(world_id, subscriber_id, item_key, x, y, placed_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (world_id, subscriber_id, item_key, float(x), float(y),
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.execute(
        "INSERT INTO inventory_history(subscriber_id, item_key, action, world_id, created_at) "
        "VALUES (?, ?, 'place', ?, ?)",
        (subscriber_id, item_key, world_id,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.commit()
    return True


def world_items(db, world_id):
    """Return all items placed in a world."""
    c = _conn(db)
    rows = c.execute(
        "SELECT wi.*, ii.name, ii.icon, ii.rarity FROM world_inventory wi "
        "JOIN inventory_items ii ON wi.item_key = ii.key "
        "WHERE wi.world_id=? ORDER BY wi.placed_at",
        (world_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def remove_world_item(db, world_item_id, subscriber_id):
    """Remove a placed item (returns it to inventory)."""
    c = _conn(db)
    row = c.execute("SELECT subscriber_id, world_id, item_key FROM world_inventory WHERE id=?",
                    (world_item_id,)).fetchone()
    if not row or row['subscriber_id'] != subscriber_id:
        return False
    # Return to inventory
    c.execute(
        "INSERT INTO inventory_grants(subscriber_id, item_key, quantity, source, granted_at) "
        "VALUES (?, ?, 1, 'pick_up', ?)",
        (row['subscriber_id'], row['item_key'],
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.execute("DELETE FROM world_inventory WHERE id=?", (world_item_id,))
    c.execute(
        "INSERT INTO inventory_history(subscriber_id, item_key, action, world_id, related_id, created_at) "
        "VALUES (?, ?, 'pick_up', ?, ?, ?)",
        (row['subscriber_id'], row['item_key'], row['world_id'], world_item_id,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.commit()
    return True


def history(db, subscriber_id, limit=50):
    """Return recent inventory history for a user."""
    c = _conn(db)
    rows = c.execute(
        "SELECT * FROM inventory_history WHERE subscriber_id=? ORDER BY created_at DESC LIMIT ?",
        (subscriber_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ====================================================================
# SEED GRANTS
# ====================================================================

def seed_starter_pack(db, subscriber_id):
    """Give new users a starter pack on first login."""
    starter = [
        ('inkwell', 2, 'starter_pack'),
        ('map_fragment', 1, 'starter_pack'),
        ('brass_gear', 1, 'starter_pack'),
    ]
    for key, qty, source in starter:
        grant_item(db, subscriber_id, key, qty, source=source)


def ensure_starter_pack(db, subscriber_id):
    """Check if user has any items; if not, grant the starter pack."""
    inv = user_inventory(db, subscriber_id)
    if not inv:
        seed_starter_pack(db, subscriber_id)
