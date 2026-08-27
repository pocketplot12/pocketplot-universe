"""
PocketPlot Universe — FAQ Assistant (v13).

A deterministic, scripted FAQ bot. NOT an LLM. Zero external dependencies,
zero hallucination risk, instant responses, fully private.

How it works:
  1. User types a question (or picks from suggested prompts).
  2. We normalise it (lowercase, strip punctuation, tokenise).
  3. We score each FAQ entry by token overlap + a small set of synonyms.
  4. We return the best match (or the closest 3 for "did you mean?").

Source-citation: every answer includes a pointer to the FAQ section it
came from, so users can verify. No "I made it up" risk.

HONEST LIMITS:
  - It only knows what's in the FAQ. If a user asks something outside
    the FAQ corpus, it returns the closest 3 matches + a "don't see your
    question? Email support" link.
  - It doesn't remember past conversations (stateless).
  - It's NOT a reasoning engine. It matches tokens; it doesn't think.
  - Upgrading it to a real LLM-backed assistant is a separate decision;
    would require BYOB wiring through external_api_manager.
"""
import html as _html_lib
import re
from typing import List, Tuple


# ----- FAQ corpus (titles + answers + URL anchors) -----
# Each entry is (id, section_anchor, question, answer, [keywords]).
# The keywords are the "match surface" — common ways a user might ask.
CORPUS = [
    {
        "id": "what-is",
        "anchor": "what-is",
        "question": "What is PocketPlot Universe?",
        "answer": (
            "PocketPlot Universe is a tiered, interactive storytelling platform where you can "
            "create, roleplay, and experience unique branching narratives — from short "
            "procedural stories to long, branching worlds with choices that change the plot. "
            "The same procedural engine powers every tier; the higher tiers add longer "
            "stories, custom themes, and the freedom to bring your own AI services."
        ),
        "keywords": ["what", "is", "pocketplot", "universe", "platform", "about", "describe"],
    },
    {
        "id": "adults-only",
        "anchor": "adults-only",
        "question": "Is this safe for kids?",
        "answer": (
            "No — PocketPlot Universe is an adults-only (18+) platform. We confirm your age at "
            "signup. The original PocketPlot (a separate product for children) is unchanged and "
            "lives elsewhere; we don't merge the brands."
        ),
        "keywords": ["kids", "child", "children", "minor", "safe", "age", "appropriate"],
    },
    {
        "id": "how-generate",
        "anchor": "how-it-works",
        "question": "How do you generate stories?",
        "answer": (
            "Every story is composed from in-house word pools by a deterministic procedural "
            "engine — the same seed produces the same story. It's not an LLM, so there's no "
            "chance of it reproducing copyrighted material. At Creator tier you can route "
            "generation through your own LLM via BYOB; those responses still pass through "
            "our content filter."
        ),
        "keywords": ["how", "generate", "story", "engine", "procedural", "ai", "model", "llm"],
    },
    {
        "id": "byob",
        "anchor": "byob",
        "question": "What is BYOB?",
        "answer": (
            "BYOB = Bring Your Own Brain. Creator-tier users can plug in their own OpenAI-"
            "compatible LLM endpoint (OpenAI, OpenRouter, LiteLLM, Together, Mistral, Groq, "
            "or any local model with an OpenAI shim). You bring your API key and base URL; "
            "we route the request. We never see or store your prompts beyond what the content "
            "filter requires."
        ),
        "keywords": ["byob", "bring", "your", "own", "brain", "llm", "openai", "openrouter"],
    },
    {
        "id": "byog",
        "anchor": "byob",
        "question": "What is BYOG?",
        "answer": (
            "BYOG = Bring Your Own Graphics. Same idea as BYOB but for image generation: plug "
            "in any OpenAI-compatible image endpoint (OpenAI DALL-E, Together, OpenRouter "
            "image models, custom Stable Diffusion deployments). Generated images come back "
            "as URLs or base64."
        ),
        "keywords": ["byog", "bring", "your", "own", "graphics", "image", "dalle", "stable", "diffusion"],
    },
    {
        "id": "api-key-storage",
        "anchor": "byob",
        "question": "Where are my API keys stored?",
        "answer": (
            "Encrypted at rest using PBKDF2 + HMAC-based authenticated encryption (a stdlib-"
            "only implementation — no third-party crypto libraries required). The encryption "
            "key is derived from the POCKETPLOT_API_ENCRYPTION_KEY environment variable. We log "
            "only the first 7 characters of any key, never the full key."
        ),
        "keywords": ["key", "api", "encrypted", "storage", "secure", "stored", "where"],
    },
    {
        "id": "limits",
        "anchor": "byob",
        "question": "Are there usage limits?",
        "answer": (
            "Yes — 100 external-API calls per Creator subscriber per day. The limit is "
            "configurable via POCKETPLOT_CREATOR_DAILY_LIMIT. We describe it as 'generous' "
            "rather than 'unlimited' because 'unlimited' is a hosting-cost bomb and a "
            "marketing claim we won't make."
        ),
        "keywords": ["limit", "usage", "cap", "rate", "calls", "day", "unlimited", "restrict"],
    },
    {
        "id": "content-policy",
        "anchor": "content-policy",
        "question": "What's allowed on PocketPlot Universe?",
        "answer": (
            "Allowed: light violence (action scenes, mild conflict, combat); light romance "
            "(flirting, romantic tension, kissing between consenting adults); mature themes "
            "(grief, betrayal, moral ambiguity, addiction, recovery); strong language in "
            "moderation; drug/alcohol use depicted in fiction.\n\n"
            "Not allowed: explicit sexual content (NSFW); graphic gore or violence-for-arousal; "
            "anything depicting minors in any sexual context (zero tolerance); hate speech "
            "targeting specific protected classes; content that would get Stripe, Apple, or "
            "Google to ban us."
        ),
        "keywords": ["allowed", "content", "policy", "rules", "guidelines", "violence", "romance", "nsfw", "explicit"],
    },
    {
        "id": "guardrail",
        "anchor": "content-policy",
        "question": "How does the content filter work?",
        "answer": (
            "Two layers: a pre-generation prompt check (rejects obviously-bad inputs before "
            "they cost anything) and a post-generation sanitizer (rewrites banned phrases to "
            "neutral placeholders). Both layers are logged to validation_log so the admin can "
            "review rejections. The filter is a safety net, not a guarantee — adversarial "
            "prompts can still get through. That's a known limitation, not a hidden one."
        ),
        "keywords": ["filter", "guardrail", "validation", "moderation", "block", "refuse", "safety"],
    },
    {
        "id": "tiers",
        "anchor": "tiers",
        "question": "What's the difference between Pro and Creator?",
        "answer": (
            "Pro ($7.99/month or $79.99/year) gives you unlimited stories up to 3000 words, "
            "full theme/tone/world control, Story Worlds (branching narratives), and PDF + "
            "shareable URL export. Creator ($19.99/month or $199.99/year) adds the ability to "
            "bring your own LLM and image APIs (BYOB/BYOG), raises the word ceiling to 5000, "
            "and grants API access for mobile clients."
        ),
        "keywords": ["pro", "creator", "difference", "tier", "compare", "which", "should", "choose"],
    },
    {
        "id": "pricing",
        "anchor": "pricing",
        "question": "Do you support annual billing?",
        "answer": (
            "Yes — Pro annual is $79.99 (save ~16%) and Creator annual is $199.99 (save ~16%). "
            "Existing Pro subscribers grandfathered at $4.99/month keep that rate for the "
            "life of their subscription."
        ),
        "keywords": ["annual", "yearly", "billing", "discount", "save"],
    },
    {
        "id": "refund",
        "anchor": "refunds",
        "question": "How do refunds work?",
        "answer": (
            "We offer a 14-day money-back guarantee for first-time subscribers. Reply to the "
            "receipt email or use the contact form within 14 days of an initial charge and "
            "we'll refund. No questions, no friction. For partially-used periods we may prorate."
        ),
        "keywords": ["refund", "money", "back", "cancel", "guarantee", "return"],
    },
    {
        "id": "cancel",
        "anchor": "tiers",
        "question": "How do I cancel?",
        "answer": (
            "From your dashboard, click 'Cancel Pro' (or 'Cancel Creator'). You'll keep access "
            "until the end of the paid period, then automatically revert to the Free tier. "
            "Or use Stripe's customer portal to manage the subscription directly."
        ),
        "keywords": ["cancel", "stop", "subscription", "end", "downgrade"],
    },
    {
        "id": "stripe",
        "anchor": "tiers",
        "question": "How does payment work?",
        "answer": (
            "We use Stripe for payment processing. Cards never touch our servers — Stripe "
            "handles the secure form. We store only Stripe's customer ID and subscription ID. "
            "Receipts come from Stripe, not us. Refunds are processed through Stripe's "
            "refund API."
        ),
        "keywords": ["payment", "stripe", "card", "credit", "billing", "charge", "pay"],
    },
    {
        "id": "privacy",
        "anchor": "privacy",
        "question": "What data do you collect?",
        "answer": (
            "Email, display name, age (to verify 18+), your story preferences, and — for Creator "
            "tier — your encrypted API keys. We don't collect photos, biometrics, real names, "
            "addresses, or any data we don't need to run the service."
        ),
        "keywords": ["privacy", "data", "collect", "information", "what", "store"],
    },
    {
        "id": "selling-data",
        "anchor": "privacy",
        "question": "Do you sell my data?",
        "answer": (
            "No. We don't sell your writing, your prompts, your API keys, or your email. The "
            "only party that sees your API keys is PocketPlot, and only when your request "
            "actually goes out."
        ),
        "keywords": ["sell", "data", "third", "party", "share", "privacy"],
    },
    {
        "id": "export",
        "anchor": "privacy",
        "question": "Can I export my data?",
        "answer": (
            "Yes. Stories can be exported as plain text (every tier), PDF (Pro and Creator), "
            "or a shareable URL (Pro and Creator). Worlds can be exported as a single markdown "
            "document. Account data deletion is on the roadmap."
        ),
        "keywords": ["export", "download", "data", "my", "stories", "backup"],
    },
    {
        "id": "original-pocketplot",
        "anchor": "original-pocketplot",
        "question": "What about the original PocketPlot?",
        "answer": (
            "The original PocketPlot is a separate product: a kids' bedtime-story app with "
            "parental controls and educational layers. PocketPlot Universe is the adults-only "
            "sibling, with a different brand, different content rules, and a different codebase. "
            "If you had an account on the original PocketPlot, it's still there; that product "
            "hasn't changed."
        ),
        "keywords": ["original", "old", "kids", "pocketplot", "archive", "difference", "brand"],
    },
    {
        "id": "mobile",
        "anchor": "tiers",
        "question": "Is there a mobile app?",
        "answer": (
            "Not yet. The platform is API-first today — every critical function is exposed "
            "under /api/v1/* with cookie or Bearer-token auth. Mobile clients can hit that "
            "surface without touching the web UI. A native app is on the roadmap."
        ),
        "keywords": ["mobile", "app", "ios", "android", "iphone", "phone"],
    },
    {
        "id": "self-host",
        "anchor": "self-host",
        "question": "Can I self-host?",
        "answer": (
            "Yes. PocketPlot is a single-file Flask app. The README has setup instructions; "
            "the Dockerfile has a one-line build. SQLite is the database; no Redis, no "
            "separate worker, no surprise infrastructure. Stripe mode degrades to mock if no "
            "key is set."
        ),
        "keywords": ["self", "host", "docker", "own", "deploy", "install", "local"],
    },
    {
        "id": "shut-down",
        "anchor": "self-host",
        "question": "What happens if PocketPlot shuts down?",
        "answer": (
            "You keep your stories (they're exportable). If you've configured your own API keys "
            "via BYOB, they're stored encrypted in your local SQLite database — they don't go "
            "anywhere unless you send them somewhere."
        ),
        "keywords": ["shut", "down", "close", "end", "shutdown", "shutdown"],
    },
    {
        "id": "worlds",
        "anchor": "worlds",
        "question": "What are Story Worlds?",
        "answer": (
            "A World is a living story with branching choices. Each episode opens with a "
            "400-word beat and three doors; the door you pick changes the state of the world "
            "(location, stance, antagonist). Up to ten episodes per world before the story "
            "concludes. Pro and Creator tiers can create unlimited worlds."
        ),
        "keywords": ["world", "worlds", "branching", "branch", "episode", "storyworld"],
    },
    {
        "id": "login",
        "anchor": "auth",
        "question": "How do I sign in?",
        "answer": (
            "We use magic-link sign-in. Enter your email at /login and we'll send you a one-"
            "time link valid for an hour. No passwords to remember or reset. For mobile apps, "
            "the same magic-link token works as a Bearer token against /api/v1/*."
        ),
        "keywords": ["login", "sign", "in", "password", "magic", "link", "authenticate", "access"],
    },
]


# ----- Small synonym map for better matching -----
SYNONYMS = {
    "nsfw": ["explicit", "porn", "sexual"],
    "ai": ["model", "llm", "gpt"],
    "language model": ["llm", "ai", "model"],
    "kids": ["child", "children", "minor"],
    "child": ["kids", "minor"],
    "byob": ["brain", "model", "llm"],
    "byog": ["image", "graphic", "picture"],
    "sub": ["subscription", "plan"],
    "price": ["cost", "pricing", "fee"],
    "how much": ["price", "pricing", "cost"],
    "cheap": ["price", "pricing", "cost"],
    "secret": ["api", "key", "password"],
    "openai": ["llm", "model", "byob"],
    "openrouter": ["llm", "model", "byob"],
    "stable diffusion": ["image", "graphic", "byog"],
}


# ----- Tokenise + normalise -----

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenise(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())


def _expand_with_synonyms(tokens: List[str]) -> List[str]:
    """For each token, add known synonyms."""
    out = list(tokens)
    for tok in tokens:
        if tok in SYNONYMS:
            out.extend(SYNONYMS[tok])
    return out


# ----- Scoring -----

def _score_entry(entry: dict, query_tokens: List[str]) -> Tuple[float, List[str]]:
    """Score one FAQ entry against the query. Returns (score, hits).
    Score = sum of overlap weight (entry's keyword list, not the question).
    """
    if not query_tokens:
        return 0.0, []
    kw_set = set(_tokenise(" ".join(entry["keywords"])))
    q_set = set(_expand_with_synonyms(query_tokens))
    overlap = kw_set & q_set
    if not overlap:
        return 0.0, []
    # Normalise by query length so "what is" doesn't always win over a longer question.
    return len(overlap) / max(1, len(q_set)), list(overlap)


def _top_matches(query: str, limit: int = 3) -> List[Tuple[dict, float]]:
    """Return up to `limit` corpus entries ranked by score."""
    tokens = _tokenise(query)
    if not tokens:
        return []
    scored = []
    for entry in CORPUS:
        score, _ = _score_entry(entry, tokens)
        if score > 0:
            scored.append((entry, score))
    scored.sort(key=lambda x: -x[1])
    return scored[:limit]


# ----- Public API -----

def best_answer(query: str) -> dict:
    """Return the best matching FAQ entry for a query.

    Returns:
        {"ok": True, "answer": str, "matched": "Question text", "id": "..."}
        or
        {"ok": False, "suggestions": [{"id": "...", "question": "..."}, ...]}
    """
    top = _top_matches(query, limit=3)
    if not top:
        return {"ok": False, "suggestions": [], "reason": "no_match"}
    best, score = top[0]
    if score < 0.15:  # weak match — don't pretend
        return {
            "ok": False,
            "suggestions": [
                {"id": e["id"], "question": e["question"]}
                for e, _ in top[:3]
            ],
            "reason": "weak_match",
        }
    return {
        "ok": True,
        "answer": best["answer"],
        "matched": best["question"],
        "id": best["id"],
        "anchor": best["anchor"],
        "score": round(score, 2),
    }


# Suggested prompts shown in the widget before the user types anything.
SUGGESTED_PROMPTS = [
    "What is PocketPlot Universe?",
    "How do refunds work?",
    "Is this safe for kids?",
    "What's the difference between Pro and Creator?",
    "What is BYOB?",
    "Are there usage limits?",
]


def all_corpus_for_listing() -> List[dict]:
    """Return the corpus in display order (no scores), for showing the
    user a search-results page."""
    return [
        {"id": e["id"], "anchor": e["anchor"], "question": e["question"]}
        for e in CORPUS
    ]
