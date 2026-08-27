"""
Phase 1B — generate_new_story() lives here until I patch it into app.py.
Generates a fresh bedtime story using the story_pools + the existing
educational layer (Word of the Day, Story Talk questions, Moment).
"""

from __future__ import annotations

import os
import random
import sys
from typing import Optional

import story_pools as P


# ------------------------------------------------------------------
# Word-count band. Default 200-300 (midpoint 250). The admin dashboard
# can override the midpoint via the settings table; the env var
# POCKETPLOT_WORD_COUNT_TARGET takes effect on the next process start.
# Band is midpoint ± 50.
# ------------------------------------------------------------------
def _resolve_target():
    env = os.environ.get("POCKETPLOT_WORD_COUNT_TARGET")
    try:
        midpoint = int(env) if env else 250
    except ValueError:
        midpoint = 250
    midpoint = max(120, min(500, midpoint))
    return max(80, midpoint - 50), midpoint + 50


TARGET_MIN_WORDS, TARGET_MAX_WORDS = _resolve_target()


def _pluralize(noun: str, n: int) -> str:
    """Tiny English pluralizer — covers the few cases the story uses."""
    if n == 1:
        return noun
    if noun.endswith("y"):
        return noun[:-1] + "ies"
    if noun.endswith("s"):
        return noun
    return noun + "s"


def _article(word: str) -> str:
    """Return "an" if the next word starts with a vowel sound, else "a".
    Uses a small pronouncing-style shortcut list — covers the time-of-day
    and setting names our pools use."""
    w = word.lstrip().lower()
    if w.startswith(("a", "e", "i", "o", "u")):
        # Exceptions: "one", "unique", "user" -> "a"; but our words are
        # always morning/afternoon/evening/etc., all of which take "an".
        return "an"
    return "a"


def _smooth_join(*parts: str) -> str:
    """Join prose fragments with a single space — strips double spaces."""
    s = " ".join(p.strip() for p in parts if p)
    return " ".join(s.split())


def _title_for(character: str, problem_key: str, setting: str) -> str:
    """Generate a cozy bedtime-story title from the chosen elements."""
    a = character
    b = setting.split()[0].capitalize()
    stem_titles = {
        "lost":                f"How {a} Found the Way Home from the {b}",
        "lonely":              f"How {a} Found a Friend on the {b}",
        "scared":              f"How {a} Learned the Dark Was Kind",
        "hungry":              f"How {a} Found an Unexpected Dinner",
        "cold":                f"How {a} Got Warm Again",
        "quiet":               f"How {a} Used Their Outside Voice",
        "hurting":             f"How {a} Let a Paw Rest",
        "broken":              f"How {a} Fixed a Dear Thing",
        "stuck":               f"How {a} Asked for Directions",
        "mistaken":            f"How {a} Made Peace with the Moon",
        "left-out":            f"How {a} Walked at Their Own Pace",
        "stubborn":            f"How {a} Asked for Help",
        "impatient":           f"How {a} Waited Out a Whole Minute",
        "unseen":              f"How {a} Felt Heard",
        "unkind":              f"How {a} Said 'I'm Sorry' and Meant It",
    }
    return stem_titles.get(problem_key, f"How {a} Came Through the {b}")


def _compose_prose(
    character_name: str,
    species: str,
    archetype: str,
    food: str,
    setting_name: str,
    sensory: str,
    time_of_day: str,
    lighting: str,
    problem_phrase: str,
    emotion: str,
    attempt_phrase: str,
    attempt_fails: str,
    resolution_phrase: str,
    moral: str,
    helper_name: str,
    child_name: str,
    pro_pinned_helper: Optional[str] = None,
    pro_pinned_theme: Optional[str] = None,
) -> str:
    """Compose the four-paragraph bedtime story from the selected elements.

    Sentence economy matters here. We aim for 200-300 words. Each paragraph
    has a single job:
        1. SETUP — who, where, what the small trouble is
        2. ATTEMPT — first try, which doesn't quite work
        3. TURN — someone or something helps
        4. RESOLUTION — the trouble ends + a gentle moral lands
    """

    # Resolve the helper. If a Pro user has a pinned helper name, honor it.
    helper = pro_pinned_helper or helper_name

    # The opening voice — slight variety across nights.
    opener = random.choice(P.OPENING_VOICES)

    # Pro theme — affects a single adjective or color in the prose.
    theme_color = ""
    if pro_pinned_theme:
        t = pro_pinned_theme.lower()
        if "winter" in t or "snow" in t:
            theme_color = " with snowlight in the air"
        elif "spring" in t:
            theme_color = " with the first new green"
        elif "summer" in t:
            theme_color = " in the warm honey air"
        elif "forest" in t or "wood" in t:
            theme_color = " under the long green shadow of trees"
        elif "ocean" in t or "sea" in t:
            theme_color = " with salt on the breeze"
        elif "garden" in t:
            theme_color = " with petals drifting"

    # Paragraph 1: SETUP
    # Handle grammar: the problem_phrase can start with "couldn't" (verb-after-subject)
    # or "was lonely" / "was scared" (verb-after-copula), etc. The most natural
    # join is "{Name} {problem_phrase}." when the phrase is verb-led.
    p1 = _smooth_join(
        opener,
        f"there lived a small {species} named {character_name},",
        f"who was, in every way, {archetype}.",
        f"On {_article(time_of_day)} {time_of_day} in the {setting_name}{theme_color},",
        f"with {sensory} and the {lighting} all around,",
        f"{character_name} {problem_phrase}.",
    )

    # Paragraph 2: ATTEMPT (fails)
    p2 = _smooth_join(
        f"{character_name} felt {emotion} in the smallest part of their chest.",
        f"They tried {attempt_phrase},",
        f"but {attempt_fails},",
        f"and the {emotion} grew a little.",
    )

    # Paragraph 3: TURN
    p3 = _smooth_join(
        f"Then {helper} came softly along the {setting_name}.",
        f"\"{character_name},\" said {helper},",
        f"\"would you like a small hand with this?\"",
        f"{character_name} wasn't sure, but they nodded.",
    )

    # Paragraph 4: RESOLUTION + moral landing.
    # Resolution phrases start with "they" (e.g. "they found their way home by listening..."),
    # so the subject is implicit. We use it as-is, just lowering the first letter so it flows.
    res_lowered = resolution_phrase[0].lower() + resolution_phrase[1:] if resolution_phrase else ""
    moral_for_child = (
        f"And so the {species} learned {moral}, and the night tucked that learning in beside {child_name}, "
        f"very softly, very warmly."
    )
    # Paragraph 5: the helper says goodnight to the child by name — the emotional landing.
    p5_5 = _smooth_join(
        f'"{character_name} looked up at {helper}, and {helper} said, '
        f'\u201cI think {child_name} would have liked being here tonight.\u201d',
        f"And the stars agreed, very quietly,",
    )
    # Paragraph 6: a small thematic gesture. The character carries something in their
    # pocket — echoing the "kindness / sharing" theme that runs through many resolutions.
    # This adds ~25-30 words and reliably lands the story inside the 200-300 band.
    p5_6 = _smooth_join(
        f"On the way home, {character_name} tucked {food} in their pocket,",
        f"in case someone else was hungry.",
        f"And it was so.",
    )
    p4 = _smooth_join(
        f"After a small while, {res_lowered},",
        f"and the {emotion} went quiet.",
        f"This is the part where the night folds in, like a long blanket.",
        moral_for_child,
        p5_5,
        p5_6,
    )

    # Closing voice — the bedtime beat.
    closer = random.choice(P.CLOSING_VOICES)
    return _smooth_join(p1, "", p2, "", p3, "", p4, "", closer)


def _trim_to_band(text: str, lo: int = TARGET_MIN_WORDS, hi: int = TARGET_MAX_WORDS) -> str:
    """If we went OVER the band, trim from the closing paragraph.
    If we went UNDER, leave it — but in practice paragraph 6 (the carrying-food
    gesture) reliably lifts us into the band, so under-runs are rare.
    Trim is preferred over padding: a tight story beats a long one."""
    words = text.split()
    if len(words) <= hi:
        return text
    # Drop sentences from the end until under hi.
    sentences = text.replace("\n", " ").split(".")
    sentences = [s.strip() for s in sentences if s.strip()]
    while sentences and len(".".join(sentences).split()) > hi:
        sentences.pop()
    return ".".join(sentences).strip() + ("." if sentences else "")


def generate_new_story(
    child_name: str,
    child_age: int,
    seed: Optional[int] = None,
    pro_pinned_helper: Optional[str] = None,
    pro_pinned_theme: Optional[str] = None,
    word_for_today: Optional[dict] = None,
) -> dict:
    """Generate a fresh bedtime story + educational layer.

    Returns a dict shaped like the existing generate_story() output so it
    can be passed directly to render_email() / deliver_email() without any
    shape changes downstream.
    """
    rng = random.Random(seed) if seed is not None else random.Random()

    # Pick elements
    character_name, species, archetype, food = rng.choice(P.CHARACTERS)
    setting_name, sensory, time_of_day, lighting = rng.choice(P.SETTINGS)

    problem_idx = rng.randrange(len(P.PROBLEMS))
    problem_phrase, emotion, attempt_phrase, attempt_fails = P.PROBLEMS[problem_idx]
    resolution_phrase, moral, image_prompt = P.RESOLUTIONS[problem_idx]

    # Pick a helper name (different from the main character).
    helper_candidates = [h for (h, *_rest) in P.CHARACTERS if h != character_name]
    helper_candidates += P.EXTRA_HELPERS
    helper_name = rng.choice(helper_candidates)

    # Compose
    body = _compose_prose(
        character_name, species, archetype, food,
        setting_name, sensory, time_of_day, lighting,
        problem_phrase, emotion, attempt_phrase, attempt_fails,
        resolution_phrase, moral,
        helper_name, child_name,
        pro_pinned_helper=pro_pinned_helper,
        pro_pinned_theme=pro_pinned_theme,
    )
    body = _trim_to_band(body)

    title = _title_for(character_name, emotion, setting_name)

    return {
        "title": title,
        "body": body,
        "cast": [character_name, helper_name],
        "helper_name": helper_name,
        "setting": setting_name,
        "moral": moral,
        # The visual composer will use these to pick the parts
        "image_prompt": image_prompt,
        "scene": {
            "species": species,
            "archetype": archetype,
            "time_of_day": time_of_day,
            "lighting": lighting,
            "food": food,
            "emotion": emotion,
        },
        "source": "generated_v1",
        "word_count": len(body.split()),
    }


# ============================================================================
# Standalone smoke test
# ============================================================================
if __name__ == "__main__":
    print(f"Pools loaded: {len(P.CHARACTERS)} characters, {len(P.SETTINGS)} settings, "
          f"{len(P.PROBLEMS)} problems/resolutions, {len(P.OPENING_VOICES)} opening voices")
    print()
    for i in range(3):
        s = generate_new_story(child_name="Wren", child_age=5, seed=i * 100)
        print(f"--- Story {i+1} ---")
        print(f"Title : {s['title']}")
        print(f"Cast  : {s['cast']}")
        print(f"Words : {s['word_count']}  (target: 200-300)")
        assert 200 <= s['word_count'] <= 300, f"Word count {s['word_count']} outside 200-300 band!"
        print()
        print(s["body"])
        print()
