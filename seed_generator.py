"""
PocketPlot Universe - Story Seed Generator (v17).

Random creative-prompt generator. Returns a complete Story
Specification Form pre-fill: genre + character description + setting +
primary objective. Uses the same in-house word pools as story_gen.py
and story_pools.py.

The /seed page lets users "Try Another" until they find a prompt they
like, then "Use this prompt" routes them to /worlds/new with the
prompt pre-filled.
"""
import random
import logging
from typing import Optional

log = logging.getLogger("pocketplot.seed_generator")


# A curated bank of character traits, motivations, and quirks. Kept
# in-house; no third-party content.
CHARACTER_TEMPLATES = [
    "a {role} who {trait}, {motivation}",
    "an {age_range} {role} whose greatest fear is {fear}",
    "a {role} with a secret - {secret}",
    "the last {role} in a world that has forgotten them",
    "a {role} who has been running from {danger} for {duration}",
    "an {role} whose {relationship} just disappeared",
    "a {role} who once {past}, and is now trying to {present}",
    "two {roles} who share {bond} but disagree on {conflict}",
]

ROLES = [
    "cartographer", "chef", "clockmaker", "detective", "diplomat",
    "doctor", "explorer", "forger", "gardener", "historian",
    "judge", "lighthouse keeper", "librarian", "mercenary", "messenger",
    "musician", "oracle", "outlaw", "pilot", "pirate", "privateer",
    "priest", "queen's champion", "rogue archivist", "royal cartographer",
    "sailor", "scout", "scribe", "shipwright", "spy", "street artist",
    "surgeon", "tax collector", "tinker", "tomb raider", "trader",
    "undertaker", "vampire hunter", "wanderer", "warden", "witch",
]

TRAITS = [
    "speaks three languages but lies in all of them",
    "remembers every face but no one's name",
    "draws maps that change when no one is looking",
    "always knows the time but never the date",
    "sleeps with one eye open and a knife in the other hand",
    "hums when they're nervous and stops when they're dangerous",
    "collects buttons from people they've outlived",
    "never lies, but never tells the whole truth either",
    "writes everything down, then burns it",
    "laughs at funerals and cries at weddings",
]

MOTIVATIONS = [
    "trying to get home",
    "trying to forget one specific person",
    "trying to finish something they started ten years ago",
    "trying to pay off a debt no one else remembers",
    "trying to find a person who doesn't want to be found",
    "trying to prove something to someone who's already dead",
    "trying to build something that will outlast them",
    "trying to undo one specific decision",
]

FEARS = [
    "silence", "mirrors", "small enclosed spaces",
    "the colour their mother used to wear",
    "a specific kind of weather",
    "being forgotten while still alive",
    "their own cleverness",
    "being right about something terrible",
]

SECRETS = [
    "they are the only one who can read the old language",
    "they were supposed to die three winters ago",
    "they wrote the letter that started the war",
    "they can hear the city's heartbeat through the floor",
    "their shadow is two days behind them",
    "they remember a future that hasn't happened yet",
    "they are the lost heir to a forgotten kingdom",
    "every lie they tell becomes true the next day",
]

AGE_RANGES = [
    "middle-aged", "elderly", "fresh out of school",
    "ancient", "younger than they look", "older than they look",
]

DANGERS = [
    "an old enemy", "their own reflection", "a debt collector",
    "the same nightmare", "their past", "a stranger who knows their name",
    "the organisation they used to work for", "the voice in the wall",
]

DURATIONS = [
    "six months", "a year and a day", "longer than they care to admit",
    "since the last festival", "ever since the incident",
    "as long as anyone can remember",
]

RELATIONSHIPS = [
    "mentor", "sister", "father", "best friend", "wife",
    "partner", "sworn enemy", "guardian", "apprentice", "twin",
]

PASTS = [
    "saved a city from a flood", "killed a man for the right reasons",
    "betrayed the only person who trusted them", "lost a war",
    "won a war and lost themselves in it", "walked away from a throne",
    "invented something terrible",
]

PRESENTS = [
    "build something small that matters",
    "live long enough to apologize",
    "find someone worth trusting again",
    "write down the truth before they die",
    "raise a child who doesn't carry their name",
    "learn to sleep without a weapon",
]

BONDS = [
    "a promise", "a scar", "a secret", "a debt", "a song", "a child",
]

CONFLICTS = [
    "what to do with the body",
    "whether to stay or run",
    "which one of them is the traitor",
    "whether the spell should be broken",
    "how much of the truth to tell",
    "whether the gods exist",
]


def _pick(rng: random.Random, pool: list) -> str:
    return rng.choice(pool)


def generate_prompt(rng: Optional[random.Random] = None,
                    genre: Optional[str] = None) -> dict:
    """Generate a complete Story Specification prompt.

    Returns:
        {
            "genre": str,
            "tone": str,
            "setting": str,
            "character_description": str,
            "primary_objective": str,
            "title_hint": str,
        }
    """
    rng = rng or random.Random()
    from story_image_composer import GENRES_V16 as GENRES, GENRE_LABELS as LABELS
    chosen_genre = genre or _pick(rng, GENRES)

    # The character's full description is a single natural-language string
    # built from a template + randomly picked slots.
    role      = _pick(rng, ROLES)
    trait     = _pick(rng, TRAITS)
    motivation = _pick(rng, MOTIVATIONS)
    age       = _pick(rng, AGE_RANGES)
    fear      = _pick(rng, FEARS)
    secret    = _pick(rng, SECRETS)
    danger    = _pick(rng, DANGERS)
    duration  = _pick(rng, DURATIONS)
    rel       = _pick(rng, RELATIONSHIPS)
    past      = _pick(rng, PASTS)
    present   = _pick(rng, PRESENTS)
    bond      = _pick(rng, BONDS)
    conflict  = _pick(rng, CONFLICTS)

    # Pick a template and substitute.
    template = _pick(rng, CHARACTER_TEMPLATES)
    try:
        character = template.format(
            role=role, trait=trait, motivation=motivation, age_range=age,
            fear=fear, secret=secret, danger=danger, duration=duration,
            relationship=rel, past=past, present=present,
            bond=bond, conflict=conflict,
        )
    except KeyError:
        # Templates that don't use all slots fall through cleanly.
        character = template

    # Objective: a small set of patterns mixed with character-driven verbs.
    objective_templates = [
        f"Find {secret} before anyone else does",
        f"Outrun {danger} and reach {present}",
        f"Convince {role}s everywhere that {secret}",
        f"Recover what was lost when the {rel} disappeared",
        f"Survive long enough to {present}",
        f"Solve the puzzle of {secret} without {trait}",
    ]
    objective = _pick(rng, objective_templates).format(
        role=role, trait=trait, secret=secret, danger=danger, rel=rel,
        present=present,
    )

    # Setting: drawn from genre-specific pool if available, else generic.
    setting = _setting_for_genre(chosen_genre, rng)

    # Title hint: short evocative phrase.
    title_templates = [
        f"The Last {role.title()}",
        f"{LABELS.get(chosen_genre, 'Story')} at {setting.title()}",
        f"When the {rel.title()} Disappeared",
        f"A {role.title()}'s Reckoning",
        f"The {secret.title()}",
    ]
    title_hint = _pick(rng, title_templates)

    tone = _pick(rng, ["hopeful", "mysterious", "dark", "whimsical",
                        "epic", "romantic", "comedic", "suspenseful"])

    return {
        "genre": chosen_genre,
        "genre_label": LABELS.get(chosen_genre, chosen_genre.title()),
        "tone": tone,
        "setting": setting,
        "character_description": character,
        "primary_objective": objective,
        "title_hint": title_hint,
    }


def _setting_for_genre(genre: str, rng: random.Random) -> str:
    """Genre-aware setting pool."""
    pools = {
        "cyberpunk":   ["a neon-drenched city at midnight",
                          "a corporate tower's underground server farm",
                          "a flooded city district where the trains don't run anymore"],
        "romance":     ["a seaside bookshop in autumn",
                          "a small town where everyone knows your name",
                          "a quiet farm in late winter"],
        "action":      ["a burning cargo ship",
                          "a desert highway with no fuel",
                          "a city under siege, three blocks from the wall"],
        "drama":       ["a hospital waiting room at 3am",
                          "a family kitchen during a long argument",
                          "an empty theatre the morning after closing night"],
        "thriller":    ["a basement server room with no exit",
                          "a small hotel with too few guests",
                          "a city that wasn't on the map yesterday"],
        "fantasy":     ["a mountain monastery where the bells ring on their own",
                          "a forest where the trees grow backwards",
                          "an empire's last library, half-buried in sand"],
        "comedy":      ["a touring theatre company with no money and two shows left",
                          "a town that has never held a festival",
                          "a startup that just realized it's been out of business for a month"],
        "scifi":       ["a generation ship three hundred years from anywhere",
                          "a research base on a moon that doesn't have a name",
                          "an abandoned orbital station with one occupant left"],
        "horror":      ["a small town where the children stopped laughing last winter",
                          "a hospital wing that's been closed for twenty years",
                          "a basement that wasn't there yesterday"],
        "detective":   ["a city where every witness has the same alibi",
                          "a small town with one unsolved case from thirty years ago",
                          "a hotel where the same guest keeps checking in under different names"],
        "fairytales":  ["a kingdom where the queen has forgotten her own name",
                          "a forest at the edge of every map",
                          "a tower where the clock has run backwards for a hundred years"],
        "superhero":   ["a city where the heroes have all retired",
                          "a school for children with abilities they've been told to hide",
                          "a building on fire with no one allowed to see"],
        "chicklit":    ["a small magazine that just lost its star columnist",
                          "a coffee shop with one regular table",
                          "a long weekend in a city where you used to live"],
        "adventure":   ["an uncharted island with a signal on the radio",
                          "a desert with a city buried under the sand",
                          "a sky kingdom reachable only by a specific storm"],
        "roleplaying": ["a tavern at the edge of a ruined kingdom",
                          "a wizard's tower that has been empty for two hundred years",
                          "a guild hall on the night of the new moon"],
        "historical":  ["a monastery scriptorium in the year 1104",
                          "a colonial port city the day the new governor arrives",
                          "a frontier outpost the year the telegraph arrives"],
    }
    pool = pools.get(genre)
    if not pool:
        return "a quiet place where something is about to go wrong"
    return _pick(rng, pool)
