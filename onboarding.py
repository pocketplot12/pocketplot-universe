"""
PocketPlot Universe - onboarding wizard (v24).

3-step flow for first-time users:
  Step 1: Pick a genre (from 16 genres)
  Step 2: Describe your character (free-text)
  Step 3: Choose a tone (from 5 tones)

Stored in onboarding_state. After completing, the user is dropped into /worlds/new
with their choices pre-filled in the form.

API:
  - get_state(db, subscriber_id)
  - update_step(db, subscriber_id, step, data)
  - mark_complete(db, subscriber_id)
  - is_complete(db, subscriber_id)
"""
import json
import datetime as dt


def _conn(db):
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


# Match story_gen.py / worlds_new form options
GENRES = ['fantasy', 'scifi', 'noir', 'romance', 'adventure', 'horror',
          'cyberpunk', 'fairytales', 'superhero', 'chicklit',
          'roleplaying', 'historical', 'thriller', 'comedy', 'drama', 'action']

TONES = ['hopeful', 'mysterious', 'suspenseful', 'romantic', 'epic']

GENRE_LABELS = {
    'fantasy': 'Fantasy',
    'scifi': 'Science Fiction',
    'noir': 'Noir',
    'romance': 'Romance',
    'adventure': 'Adventure',
    'horror': 'Horror',
    'cyberpunk': 'Cyberpunk',
    'fairytales': 'Fairytales',
    'superhero': 'Superhero',
    'chicklit': 'Chick-Lit',
    'roleplaying': 'Roleplaying',
    'historical': 'Historical',
    'thriller': 'Thriller',
    'comedy': 'Comedy',
    'drama': 'Drama',
    'action': 'Action',
}

TONE_LABELS = {
    'hopeful': 'Hopeful',
    'mysterious': 'Mysterious',
    'suspenseful': 'Suspenseful',
    'romantic': 'Romantic',
    'epic': 'Epic',
}


def get_state(db, subscriber_id):
    """Return the user's onboarding state. Create if missing."""
    c = _conn(db)
    row = c.execute("SELECT * FROM onboarding_state WHERE subscriber_id=?",
                    (subscriber_id,)).fetchone()
    if not row:
        c.execute("INSERT INTO onboarding_state(subscriber_id) VALUES (?)",
                  (subscriber_id,))
        c.commit()
        row = c.execute("SELECT * FROM onboarding_state WHERE subscriber_id=?",
                        (subscriber_id,)).fetchone()
    return dict(row)


def update_step(db, subscriber_id, step, data):
    """Update a step's data (data is a dict)."""
    c = _conn(db)
    col = f'step{step}_data'
    if col not in ('step1_data', 'step2_data', 'step3_data'):
        raise ValueError("Invalid step")
    c.execute(
        f"UPDATE onboarding_state SET {col}=?, current_step=? WHERE subscriber_id=?",
        (json.dumps(data), step, subscriber_id),
    )
    c.commit()


def advance_step(db, subscriber_id, current_step, new_step, data):
    """Update step data + advance to next step."""
    c = _conn(db)
    col = f'step{current_step}_data'
    if col not in ('step1_data', 'step2_data', 'step3_data'):
        raise ValueError("Invalid step")
    c.execute(
        f"UPDATE onboarding_state SET {col}=?, current_step=? WHERE subscriber_id=?",
        (json.dumps(data), new_step, subscriber_id),
    )
    c.commit()


def mark_complete(db, subscriber_id):
    """Mark onboarding complete (sets completed_at)."""
    c = _conn(db)
    c.execute(
        "UPDATE onboarding_state SET completed_at=? WHERE subscriber_id=?",
        (dt.datetime.utcnow().isoformat(timespec='seconds'), subscriber_id),
    )
    c.commit()


def skip(db, subscriber_id):
    """Mark onboarding as skipped."""
    c = _conn(db)
    c.execute(
        "UPDATE onboarding_state SET skipped_at=? WHERE subscriber_id=?",
        (dt.datetime.utcnow().isoformat(timespec='seconds'), subscriber_id),
    )
    c.commit()


def is_complete(db, subscriber_id):
    """Return True if user finished or skipped onboarding."""
    state = get_state(db, subscriber_id)
    return state.get('completed_at') is not None or state.get('skipped_at') is not None
