"""
PocketPlot Universe — StoryWorld engine (v11).

A scaffolded branching-narrative system:

  - A "world" is a (subscriber, title, genre, tone, setting, seed) tuple.
  - Each world has a state (small JSON blob — current location,
    relationships, plot flags).
  - Each "episode" is a 200-400 word story beat that ends with 3
    choices for the next episode.
  - The user's choice updates the state; the next episode is generated
    from the new state.

HONEST SCOPE:
  - This module produces coherent single-episode beats with deterministic
    seeding. It does NOT maintain deep narrative coherence across many
    episodes — that requires a reasoning model with state-tracking
    capability that we don't have. Episodes will be locally consistent
    (genre/tone, character, location) but not micro-continuity-perfect.
  - The branching tree is shallow: 3 choices per episode, ~10 episodes
    per session before the user is nudged to "conclude this story."
  - All outputs pass through validation_system.validate_for_tier().

FUTURE EXPANSION (documented in EVOLUTION_PLAN.md):
  - Swap the procedural generator for an LLM (BYOB) for richer episodes.
  - Add a memory vector store (SQLite FTS or similar) so episodes can
    reference earlier beats.
  - Add a "world export" feature (single markdown or PDF for the
    whole session's tree).
"""
import datetime as dt
import json
import logging
import re
import sqlite3

import story_gen as _story_gen
import story_pools as _pools
import validation_system as _val

log = logging.getLogger("pocketplot.worlds")


# ---- Genre + tone catalogs (small on purpose) ----
# Each genre has a "grammar" (naming conventions + motif vocabulary)
# applied during generation. Tone adjusts the prose register.

GENRES = {
    "fantasy":   {
        "magic_words":   ["glyphs", "wards", "enchantments", "threads of light"],
        "antagonist":    ["the Hollow King", "the Whisperer", "the Iron Duke"],
        "motif_verbs":   ["whisper", "hum", "glow", "shift", "ripple"],
        "settings":      ["feywood", "crystal cathedral", "moss bridge", "lantern quarter"],
    },
    "scifi":     {
        "magic_words":   ["quantum", "neural", "plasma", "ion", "vector"],
        "antagonist":    ["the Architect", "the Cartel", "the Driftmind"],
        "motif_verbs":   ["ping", "boot", "scan", "lock", "phase"],
        "settings":      ["orbital station", "lower tier", "drone dock", "satellite array"],
    },
    "noir":      {
        "magic_words":   ["cigarettes", "rain", "shadows", "doss", "lamps"],
        "antagonist":    ["the Fixer", "the Widow", "the Lieutenant"],
        "motif_verbs":   ["lean", "drag", "lower", "scan", "sigh"],
        "settings":      ["the back office", "the rain-slick pier", "the bus depot", "the upstairs bar"],
    },
    "romance":   {
        "magic_words":   ["letters", "roses", "windows", "letters", "songs"],
        "antagonist":    ["the past", "the rumor", "the distance"],
        "motif_verbs":   ["smile", "reach", "linger", "remember", "promise"],
        "settings":      ["a corner booth", "the rooftop garden", "the bookshop", "the river walk"],
    },
    "adventure": {
        "magic_words":   ["maps", "ropes", "matches", "binoculars", "tide charts"],
        "antagonist":    ["the storm", "the cartel", "the rockfall"],
        "motif_verbs":   ["climb", "swing", "scramble", "haul", "navigate"],
        "settings":      ["a salt cliff", "the smugglers' cove", "a crashed glider", "the canyon mouth"],
    },
    "horror":    {
        "magic_words":   ["breath", "rust", "static", "shadows", "echoes"],
        "antagonist":    ["the Watcher", "the Voice", "the Quiet Man"],
        "motif_verbs":   ["hold", "stop", "listen", "feel", "freeze"],
        "settings":      ["the long hallway", "the basement", "the empty house", "the back road"],
    },
}

TONES = {
    "hopeful":   "warm, easy, with little light at the end of every passage.",
    "grim":      "hard, plain, with the cost of every choice on the page.",
    "romantic":  "tender, slow, attentive to small gestures and small words.",
    "mysterious": "restrained, observational, letting the silence do the work.",
    "comedic":   "light, slightly off-key, with a wry inner voice.",
    "epic":      "wide-angled, confident, the camera pulled back.",
}


# ---- Database CRUD ----

def create_world(db, subscriber_id: int, title: str, genre: str,
                  tone: str, setting: str, seed: int = None,
                  spec: dict = None) -> int:
    """Create a new world. Returns the world id.

    v16: accepts an optional `spec` dict (the Story Specification Form
    output) and persists it in state_json under `spec`. The default
    engine + BYOB both read from this when composing episodes.
    """
    if genre not in GENRES:
        # v16: accept any of the 16 GENRES_V16 even if they're not in the
        # legacy GENRES dict. Story composer / scene mapping handle them.
        try:
            from story_image_composer import GENRES_V16 as _g16
            if genre not in _g16:
                raise ValueError(f"Unknown genre: {genre!r}")
        except Exception:
            raise ValueError(f"Unknown genre: {genre!r}")
    if tone not in TONES:
        raise ValueError(f"Unknown tone: {tone!r}")
    seed = seed or int(dt.datetime.utcnow().timestamp()) % (2**31)
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    state = {"spec": spec or {}}
    state_json = json.dumps(state, ensure_ascii=False)
    conn = db()
    cur = conn.execute(
        "INSERT INTO worlds(subscriber_id, title, genre, tone, setting, "
        "state_json, seed, is_active, created_at, last_played_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (subscriber_id, title, genre, tone, setting, state_json, seed, now, now),
    )
    wid = cur.lastrowid
    conn.commit(); conn.close()
    return wid


def list_worlds(db, subscriber_id: int, limit: int = 50):
    conn = db()
    rows = conn.execute(
        "SELECT id, title, genre, tone, setting, seed, is_active, "
        "created_at, last_played_at FROM worlds WHERE subscriber_id=? "
        "ORDER BY last_played_at DESC LIMIT ?",
        (subscriber_id, limit),
    ).fetchall()
    conn.close()
    return rows


def get_world(db, world_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    return row


def _next_episode_number(db, world_id: int) -> int:
    conn = db()
    row = conn.execute(
        "SELECT COALESCE(MAX(episode_number), 0) AS n FROM world_episodes WHERE world_id=?",
        (world_id,),
    ).fetchone()
    conn.close()
    return int(row["n"]) + 1


def _save_episode(db, world_id: int, subscriber_id: int, episode_number: int,
                   title: str, body: str, choices: list) -> int:
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn = db()
    cur = conn.execute(
        "INSERT INTO world_episodes(world_id, subscriber_id, episode_number, "
        "title, body, choices_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (world_id, subscriber_id, episode_number, title, body,
         json.dumps(choices), now),
    )
    eid = cur.lastrowid
    # Update the world's last_played_at timestamp.
    conn.execute(
        "UPDATE worlds SET last_played_at=? WHERE id=?",
        (now, world_id),
    )
    conn.commit(); conn.close()
    return eid


def _load_episode(db, episode_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM world_episodes WHERE id=?",
                        (episode_id,)).fetchone()
    conn.close()
    return row


def _update_state(db, world_id: int, new_state: dict):
    conn = db()
    conn.execute("UPDATE worlds SET state_json=? WHERE id=?",
                  (json.dumps(new_state), world_id))
    conn.commit(); conn.close()


# ---- Generation ----

# How many episodes before we nudge the user to "conclude this world"?
MAX_EPISODES = 10


def generate_episode(db, subscriber_id: int, world_id: int,
                      choice_from_episode_id: int = None,
                      chosen_index: int = None,
                      tier: str = "pro") -> dict:
    """Generate the next episode for a world. If `choice_from_episode_id`
    and `chosen_index` are given, the world state is updated with the
    chosen choice's `state_update` before generation.

    Returns the episode dict (title, body, choices, episode_number, id).

    Pass-through `validate_for_tier` keeps every output within policy.
    """
    world = get_world(db, world_id)
    if not world:
        return {"ok": False, "reason": "World not found."}
    if world["subscriber_id"] != subscriber_id:
        return {"ok": False, "reason": "World belongs to another subscriber."}

    ep_num = _next_episode_number(db, world_id)
    if ep_num > MAX_EPISODES:
        return {"ok": False, "reason":
                f"This world has reached the maximum {MAX_EPISODES} episodes. "
                f"Conclude or restart to continue."}

    # 1. Apply the user's choice (if any) to update world state.
    state = json.loads(world["state_json"] or "{}")
    if choice_from_episode_id is not None and chosen_index is not None:
        prev = _load_episode(db, choice_from_episode_id)
        if prev and prev["choices_json"]:
            try:
                choices = json.loads(prev["choices_json"])
                if 0 <= chosen_index < len(choices):
                    update = choices[chosen_index].get("state_update", {}) or {}
                    for k, v in update.items():
                        state[k] = v
            except (json.JSONDecodeError, IndexError):
                log.warning("bad choice data for ep %s", choice_from_episode_id)

    # 2. Generate the episode body using the procedural pipeline.
    genre = world["genre"]
    tone = world["tone"]
    setting = world["setting"]
    seed = (world["seed"] * 1000) + ep_num
    body, title, choices = _compose_episode(genre, tone, setting, state, seed)

    # 3. Per-tier word ceiling + validation.
    validated = _val.validate_for_tier(body, tier=tier,
                                        subscriber_id=subscriber_id, db=db)
    if not validated["ok"]:
        return {"ok": False, "reason": validated.get("reason",
                                                      "Generation failed validation.")}
    body = validated["text"]

    # 4. Persist.
    eid = _save_episode(db, world_id, subscriber_id, ep_num, title, body, choices)
    _update_state(db, world_id, state)

    return {
        "ok": True,
        "episode_id": eid,
        "world_id": world_id,
        "episode_number": ep_num,
        "title": title,
        "body": body,
        "choices": choices,
        "max_episodes": MAX_EPISODES,
    }


def _compose_episode(genre: str, tone: str, setting: str,
                      state: dict, seed: int) -> tuple:
    """Compose one episode (body + title + 3 choices).

    The output is locally consistent (genre + tone + setting all show
    up in the prose) but not deeply coherent across episodes. Each
    episode is built fresh from the deterministic seed.

    v16: if state['spec'] is present (the Story Specification Form output),
    the user's character description + primary objective thread into
    both the title and the prose. The BYOB engine uses the same spec.
    """
    # Deterministic RNG from the seed.
    import random
    rng = random.Random(seed)

    gmeta = GENRES.get(genre, GENRES["fantasy"])
    tone_desc = TONES.get(tone, TONES["hopeful"])
    chosen_setting = state.get("location") or rng.choice(gmeta["settings"])
    chosen_antagonist = state.get("antagonist") or rng.choice(gmeta["antagonist"])
    motif_verb = rng.choice(gmeta["motif_verbs"])
    magic_word = rng.choice(gmeta["magic_words"])

    # v16: thread the user's structured Story Specification into the prompt.
    spec = state.get("spec") or {}
    character_desc = spec.get("character_description") or ""
    primary_objective = spec.get("primary_objective") or ""

    # Pick a helper from story_pools if available (keeps a touch of the
    # existing cast register), else fall back to a placeholder. CHARACTERS
    # is a list of (name, species, trait, food) tuples in story_pools.
    helper_pick = None
    if getattr(_pools, "CHARACTERS", None):
        try:
            helper_pick = rng.choice(_pools.CHARACTERS)
        except Exception:
            helper_pick = None
    helper_name = helper_pick[0] if helper_pick else "the helper"

    # Title.
    title_templates = [
        f"Episode: the {magic_word} at {chosen_setting}",
        f"Episode: {helper_name.title()} at the {chosen_setting}",
        f"Episode: a {magic_word} begins to {motif_verb}",
    ]
    title = rng.choice(title_templates)

    # Body. 4 short paragraphs.
    # v16: when the Story Specification Form has been filled in, prepend a
    # one-line character+objective paragraph so the prose starts from a
    # real person + a real goal instead of pure atmosphere.
    if character_desc or primary_objective:
        spec_intro_parts = []
        if character_desc:
            spec_intro_parts.append(character_desc.rstrip("."))
        if primary_objective:
            spec_intro_parts.append("Their goal: " + primary_objective.rstrip(".") + ".")
        spec_intro = " ".join(spec_intro_parts)
    else:
        spec_intro = ""
    intro = (
        f"The {magic_word} at the {chosen_setting} was supposed to {motif_verb} "
        f"by itself. It did not. {helper_name.title()} was waiting at the door, "
        f"and what they said next was not what was expected."
    )
    middle = (
        f"Things in the {chosen_setting} are rarely what they seem, and this "
        f"was no exception. {chosen_antagonist.title()} had been mentioned only "
        f"once before, and now the mention was back, like a {magic_word} that "
        f"would not stop {motif_verb}ing. The prose is {tone_desc} {helper_name.title()} "
        f"knew the {magic_word} better than most, but not better than {chosen_antagonist}."
    )
    twist = (
        f"There was a small sound from the back of the {chosen_setting} — not "
        f"a noise, exactly, but the shape a noise leaves behind. {helper_name.title()} "
        f"went very still. The {magic_word} {motif_verb}ed once, twice, then went out. "
        f"Now there was only the question."
    )
    closing = (
        f"And the question, as it always is, was what to do next. {helper_name.title()} "
        f"had three options. So did you."
    )
    body = "\n\n".join([p for p in [spec_intro, intro, middle, twist, closing] if p])

    # Three choices. Each carries a state update that influences the
    # next episode.
    choices_pool = [
        {
            "label": f"Step toward the {magic_word} and ask what it {motif_verb}ed.",
            "state_update": {"location": chosen_setting, "stance": "approaching"},
        },
        {
            "label": f"Follow {helper_name.title()} to a quieter corner of the {chosen_setting}.",
            "state_update": {"location": chosen_setting, "stance": "observing"},
        },
        {
            "label": f"Confront {chosen_antagonist} directly and see what falls out.",
            "state_update": {"location": chosen_setting, "stance": "confronting",
                              "antagonist": chosen_antagonist},
        },
    ]
    rng.shuffle(choices_pool)

    return body, title, choices_pool
