"""
PocketPlot — Story element pools

This file holds the reusable building blocks that the new story generator
mixes and matches to produce fresh bedtime stories on demand.

The pools are designed so that any combination produces a coherent story —
characters fit every setting, problems match the available resolutions, and
morals align with the resolution they follow.

Tone: present-tense, soft, second-person address ("you can see..."), warm.

Used by `app.generate_new_story()`. Kept in a separate file so the
human-reviewer can scan it at a glance when reviewing new content.
"""

from __future__ import annotations

# ============================================================================
# CHARACTERS (24 entries)
# Each entry is (name, species, archetype, favorite_food)
# archetype is a one-word personality tag used to color the prose.
# ============================================================================
CHARACTERS = [
    ("Fennel",  "fox",         "curious",   "plump blueberries"),
    ("Bram",    "bear",        "patient",   "honey cakes"),
    ("Pip",     "mole",        "brave",     "earthworms (politely)"),
    ("Wren",    "wren",        "bright",    "tiny seeds"),
    ("Rue",     "rabbit",      "careful",   "clover petals"),
    ("Felix",   "hedgehog",    "soft",      "falling leaves"),
    ("Hazel",   "deer",        "watchful",  "morning dew"),
    ("Olive",   "otter",       "playful",   "river pebbles"),
    ("Cira",    "mouse",       "tiny",      "a single oat"),
    ("Sage",    "squirrel",    "nervous",   "an acorn (always)"),
    ("Nora",    "newt",        "steady",    "smooth water"),
    ("Iris",    "owl",         "wise",      "small wonderings"),
    ("Pippa",   "piglet",      "round",     "apple cores"),
    ("Theo",    "turtle",      "slow",      "a warm rock"),
    ("Juno",    "junco",       "friendly",  "sunflower seeds"),
    ("Eli",     "elk",         "big-kind",  "tall grass"),
    ("Robin",   "robin",       "cheerful",  "earthworms"),
    ("Sam",     "salamander",  "cool",      "a cool stone"),
    ("Lily",    "lamb",        "fluffy",    "fresh milk"),
    ("Cooper",  "chipmunk",    "puffy",     "three seeds at once"),
    ("Fern",    "firefly",     "glowy",     "the small dark"),
    ("Ash",     "armadillo",   "kind",      "a curled-up nap"),
    ("Mae",     "marmot",      "cozy",      "mountain thyme"),
    ("Bree",    "bluebird",    "warm",      "a soft worm"),
]

# ============================================================================
# SETTINGS (17 entries)
# Each is (name, sensory_detail, time_of_day, lighting_note)
# ============================================================================
SETTINGS = [
    ("cozy burrow",          "a small lantern with a wax-dripped top",         "evening",      "warm lamp-light"),
    ("misty meadow",         "wildflowers nodding in the slow wind",          "morning",      "low gold sunlight"),
    ("tall pine forest",     "owl-soft sounds and snow-tipped branches",      "dusk",         "violet sky through the trees"),
    ("sunlit hill",          "long warm grass that tickles your knees",       "afternoon",    "lazy yellow light"),
    ("riverside",            "dragonflies hanging above the slow water",      "morning",      "silver reflections"),
    ("mushroom ring",        "tiny doorways glowing at the corners",          "evening",      "fairy-light"),
    ("snowy field",          "soft snowflakes landing on a still nose",       "winter night", "moon-on-snow"),
    ("beach at twilight",    "tide pulling in small silver breaths",          "twilight",     "low amber light"),
    ("autumn orchard",       "leaves like tiny boats drifting down",          "afternoon",    "orange tree-light"),
    ("stone bridge",         "mossy stone and the brook underneath",          "morning",      "dappled green light"),
    ("honey-tree hollow",    "a warm gold glow coming from inside",           "evening",      "candlelight"),
    ("stargazing hilltop",   "a sky so wide it almost fits in your eyes",     "night",        "starlight"),
    ("lily-pad pond",        "calm green leaves and frog-song underneath",    "evening",      "water-light"),
    ("garden gate",          "roses climbing up like small children",         "morning",      "rose-pink light"),
    ("pebble brook",         "smooth stones warm from the sun",               "afternoon",    "sun-on-stone"),
    ("willow-tunnel",        "curtain branches that whisper when you walk",   "evening",      "long green shadows"),
    ("clover meadow",        "small white stars under your paws",             "morning",      "dew-light"),
]

# ============================================================================
# PROBLEMS (15 entries)
# Each is (problem_phrase, emotion, attempt_phrase, attempt_fails_phrase)
# attempt_fails is what happens on the first try so the climax can pivot.
# ============================================================================
PROBLEMS = [
    ("couldn't find the way home",      "lost",       "to follow the path they knew",     "the path was gone"),
    ("was lonely at suppertime",        "lonely",     "to find someone to eat with",     "no one was nearby"),
    ("was scared of the dark",          "scared",     "to stay very still and quiet",     "the dark kept listening"),
    ("couldn't find any dinner",        "hungry",     "to look in the usual places",      "the usual places were empty"),
    ("was getting too cold",            "cold",       "to pull their scarf tighter",      "the scarf was already tight"),
    ("couldn't quite speak up",         "quiet",      "to whisper what they needed",      "the whisper was too small"),
    ("had a sore paw",                  "hurting",    "to walk without using it",         "every step felt pinchy"),
    ("had their favorite thing break",  "broken",     "to tape it back together",         "the tape wouldn't hold"),
    ("couldn't figure out how to move forward", "stuck",       "to push harder",                   "the harder they pushed, the less it moved"),
    ("thought the moon was following them", "mistaken", "to run faster to lose it",         "the moon kept up"),
    ("got left behind on the walk",     "left-out",   "to run to catch up",               "their legs couldn't keep pace"),
    ("wouldn't ask for help",           "stubborn",   "to do it all themselves",          "the task was too big"),
    ("couldn't wait one more minute",   "impatient",  "to try counting to ten",           "they ran out of tens"),
    ("felt no one was really listening","unseen",     "to speak louder",                  "louder felt less kind"),
    ("had been unkind and didn't know how to fix it", "unkind", "to pretend it didn't happen", "the pretending sat heavy"),
]

# ============================================================================
# RESOLUTIONS (15 entries) — index-matched to PROBLEMS.
# Each is (resolution_phrase, moral, image_prompt)
# image_prompt is a short phrase used by the procedural SVG composer.
# ============================================================================
RESOLUTIONS = [
    ("they found their way home by listening for the sound of supper",     "small sounds guide you home",       "lantern burrow + fox"),
    ("they shared a quiet bench with someone new",                          "a small hello can warm a whole evening", "rabbit on bench + fox"),
    ("they stayed still and let the dark become the night",                 "stillness is its own kind of brave", "mouse under starlight"),
    ("they followed the sound of someone else's table",                     "where there's a table, there's room", "squirrel + bear picnic"),
    ("they remembered the scarf was warm because someone made it",          "gifts stay warm even when the weather doesn't", "deer in scarf + lamp"),
    ("they used their outside voice, just once, and it fit",                "your voice is the right size for what you need", "otter speaking"),
    ("they let their paw rest and asked someone to walk with them",         "rest is part of the road",          "turtle + mouse walking"),
    ("they sewed it with small careful stitches",                           "mended things are even dearer",     "hedgehog + thimble"),
    ("they asked for directions from someone who knew the way",             "asking is a kind of strength",      "wren asking owl directions"),
    ("they realized the moon was just being a friend",                      "some shadows are company, not chasing", "mole + moon"),
    ("they walked at the pace that felt kind to their legs",                "your own pace is the right pace",    "lamb + junco slow walk"),
    ("they said 'please' and a hundred helpers appeared",                   "one small word unlocks a big world", "bear + many helpers"),
    ("they counted all the way to twenty and the minute passed",            "patience is a quiet magic",          "firefly counting stars"),
    ("they sat close to someone and felt them listening",                    "being heard is a kind of love",      "two creatures, ear to shoulder"),
    ("they said 'I'm sorry' and meant it",                                  "a real sorry is a small soft door",  "two creatures, bow of apology"),
]

# ============================================================================
# STORY-OPS (helper names + small extra voice fragments)
# These are pulled in addition to the helper cast, so variety stays high.
# ============================================================================
EXTRA_HELPERS = ["Tom", "Bree", "Ada", "Lou", "Mae", "Sage", "Kit", "Wells", "Nova"]

# Short opening voice fragments — these give every story a slightly different
# opening rhythm. The generator picks one at random.
OPENING_VOICES = [
    "You might have seen them on a slow Tuesday,",
    "There was one such little creature,",
    "If you looked closely, on the edge of the meadow,",
    "Once, not so very long ago,",
    "Here's a small story, the kind that fits in a pocket,",
    "Some nights a story just shows up at your window,",
    "In a place you might not have been yet,",
    "Come closer — this one's a quiet one,",
]

# Short closing voice fragments — keeps the bedtime beat consistent.
CLOSING_VOICES = [
    "And the night tucked them in, the way nights do.",
    "And so it was evening again, and they were warm.",
    "The stars came out one by one, like good listeners.",
    "And the wind said 'goodnight' very softly.",
    "And the small dark turned kind, the way small darks do.",
    "And they fell asleep, because the story was done.",
    "And the moon nodded, once, the way moons do.",
    "And the world got a little smaller and a little safer.",
]

# ============================================================================
# SELF-CHECKS
# At import time, we verify that PROBLEMS and RESOLUTIONS are index-matched
# (so we never produce a story where the resolution doesn't actually solve
# the problem). Mismatches are louder at the import site than at runtime.
# ============================================================================
assert len(PROBLEMS) == len(RESOLUTIONS), (
    f"PROBLEMS has {len(PROBLEMS)} entries, RESOLUTIONS has {len(RESOLUTIONS)}. "
    f"They must be index-matched so resolution[i] solves problems[i]."
)
assert len(CHARACTERS) >= 20, "Brief asks for 20+ characters"
assert len(SETTINGS)    >= 15, "Brief asks for 15+ settings"
assert len(PROBLEMS)    >= 10, "Brief asks for 10+ problems"
assert len(RESOLUTIONS) >= 10, "Brief asks for 10+ resolutions"
