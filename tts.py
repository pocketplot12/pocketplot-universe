"""
PocketPlot Universe - text-to-speech (v24).

Two-layer TTS:

1. CLIENT-SIDE (primary): Web Speech API (SpeechSynthesisUtterance).
   Free, works in all modern browsers, no server roundtrip.
   The frontend hits /tts/config to get voice settings, then uses
   window.speechSynthesis to read the scene aloud.

2. SERVER-SIDE (fallback for export): pyttsx3 generates an MP3 per episode
   for inclusion in EPUB/PDF exports. Used only when POCKETPLOT_TTS=1.

This module:
  - get_voices() returns a list of curated voices with their lang tags
  - sanitize(text) strips problematic chars before TTS (em-dashes, etc.)
  - estimate_duration(text) for progress bars
"""
import re


# ====================================================================
# VOICE CATALOG (curated, used by both client config + server pyttsx3)
# ====================================================================

VOICE_CATALOG = [
    {'id': 'female-en-us', 'name': 'Samantha',  'gender': 'female', 'lang': 'en-US', 'pitch': 1.1, 'rate': 1.0, 'note': 'Warm, clear, storybook narrator.'},
    {'id': 'male-en-us',   'name': 'Daniel',    'gender': 'male',   'lang': 'en-US', 'pitch': 0.9, 'rate': 1.0, 'note': 'Deep, resonant, epic narrator.'},
    {'id': 'female-en-gb', 'name': 'Kate',      'gender': 'female', 'lang': 'en-GB', 'pitch': 1.0, 'rate': 0.95, 'note': 'British, refined, mystery narrator.'},
    {'id': 'male-en-gb',   'name': 'Oliver',    'gender': 'male',   'lang': 'en-GB', 'pitch': 0.95, 'rate': 0.95, 'note': 'British, warm, romance narrator.'},
    {'id': 'neutral-en',   'name': 'Narrator',  'gender': 'neutral', 'lang': 'en-US', 'pitch': 1.0, 'rate': 0.9, 'note': 'Neutral, slow, deliberate.'},
]


def get_voices():
    """Return the curated voice catalog."""
    return VOICE_CATALOG


def get_default_voice_id():
    return 'female-en-us'


# ====================================================================
# TEXT SANITIZATION
# ====================================================================

def sanitize(text):
    """Strip characters that TTS engines handle poorly.

    Em-dashes become periods. Smart quotes become straight quotes.
    Curly apostrophes become straight. Multi-line breaks become pauses.
    """
    if not text:
        return ''
    text = text.replace('—', '. ')       # em-dash -> period
    text = text.replace('–', '-')        # en-dash -> hyphen
    text = text.replace('…', '...')      # ellipsis -> three dots
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('“', '"').replace('”', '"')
    text = re.sub(r'\n\n+', '. ', text)   # paragraph break -> period
    text = re.sub(r'\*+', '', text)       # markdown emphasis -> nothing
    text = re.sub(r'#+ ', '', text)        # markdown heading -> nothing
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)  # bullets
    return text.strip()


def estimate_duration(text, wpm=150):
    """Estimate read-aloud duration in seconds at the given words-per-minute."""
    words = len((text or '').split())
    return round(words / wpm * 60, 1)


def split_into_chunks(text, max_chars=400):
    """Split text into chunks suitable for TTS streaming.

    Splits at sentence boundaries (period + space) when possible.
    """
    text = sanitize(text)
    if len(text) <= max_chars:
        return [text]
    chunks = []
    cur = ''
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if len(cur) + len(sentence) + 1 <= max_chars:
            cur += (' ' if cur else '') + sentence
        else:
            if cur:
                chunks.append(cur.strip())
            cur = sentence
    if cur:
        chunks.append(cur.strip())
    return chunks


# ====================================================================
# SERVER-SIDE GENERATION (pyttsx3)
# ====================================================================

def generate_audio_server(text, out_path, voice_id=None):
    """Generate an audio file using pyttsx3. Returns True on success.

    Requires the pyttsx3 system package to be installed.
    """
    import os
    if os.environ.get('POCKETPLOT_TTS') != '1':
        return False
    try:
        import pyttsx3
    except ImportError:
        return False
    try:
        engine = pyttsx3.init()
        # Find voice
        if voice_id:
            voice = next((v for v in VOICE_CATALOG if v['id'] == voice_id), None)
            if voice:
                engine.setProperty('rate', int(200 * voice.get('rate', 1.0)))
                engine.setProperty('pitch', int(50 * voice.get('pitch', 1.0)))
        engine.save_to_file(sanitize(text), out_path)
        engine.runAndWait()
        return os.path.exists(out_path)
    except Exception:
        return False
