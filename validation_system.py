"""
PocketPlot Universe - Validation System (v12 + v16 multi-layer pipeline).

A narrow-but-honest content filter, tightened in v12 to be
Stripe-friendly and Apple App Store-friendly. v16 adds a
multi-layer pipeline with pluggable classifier stages.

SCOPE (what this does):
  1. Pre-generation filter: checks user prompts for content the
     platform refuses to produce. v12 is adults-only BUT with strict
     content guidelines - we refuse NSFW, graphic gore, hate targeting
     specific protected classes, content involving minors in any
     sexual context, and identifiable real-person private info.
  2. Post-generation sanitizer: scans generated prose and rewrites
     disallowed phrases. The list is small because the disallowed
     surface area is small.
  3. Length/tone checks: enforces the per-tier word-count ceilings
     (Free <= 300 - v12 update, was 1000; Pro <= 3000; Creator <= 5000).
  4. v16 multi-layer pipeline: pluggable classifier stages
     (keyword -> safety_classifier -> reasoning) that BYO deployments
     can drop in their own backend (Llama Guard 3, OpenAI moderation
     API, GPT-4o-mini, etc.) via env-var configuration.

WHAT THIS DOES NOT DO (honest limits):
  - It is NOT a coherence checker. Generated stories may still be
    slightly inconsistent under adversarial prompts. Coherence is
    the responsibility of the underlying generator.
  - The default `keyword` layer is a static keyword/regex pass. A
    sufficiently creative prompt could bypass keyword filters. BYO
    deployments can enable the safety_classifier layer via
    POCKETPLOT_MODERATION_BACKEND=openai_moderation (etc.).
  - It does NOT detect "implied" harmful content. It catches what
    it's told to catch, nothing more.
  - The Creator-tier BYOB/BYOG path STILL passes through validation.
    This is by design - paying more does not unlock content that
    would violate platform policy.

ALLOWED CONTENT (per v12 content guidelines):
  - Light violence (action scenes, mild conflict, combat)
  - Light romance (flirting, romantic tension, kissing between adults)
  - Mature themes (grief, betrayal, moral ambiguity, addiction)
  - Strong language in moderation (slurs sanitized post-gen)
  - Drug/alcohol use depicted in fiction

The system is deliberately a *safety net*, not a *safety blanket*.
Its job is to catch obvious problems, not to guarantee perfection.
"""

import re
import logging
import datetime as dt

log = logging.getLogger("pocketplot.validation")


# ----- Disallowed content surface (v12 — Stripe / Apple App Store safe) -----
#
# Rationale: v12 is an adults-only creative platform but with content
# guidelines deliberately tightened to be Stripe-friendly and App-Store-
# friendly. We refuse:
#   - Anything depicting minors in sexual contexts (zero tolerance)
#   - Explicit sexual content (NSFW / pornographic)
#   - Graphic gore, torture, or violence-for-arousal
#   - Hate targeting a specific protected class with intent to harm
#   - Identifiable real-person private info
#
# Allowed:
#   - Light violence (action scenes, mild conflict, combat)
#   - Light romance (flirting, romantic tension, kissing between adults)
#   - Mature themes (grief, betrayal, moral ambiguity, addiction)
#   - Strong language (in moderation; sanitized post-gen for slurs)
#   - Drug/alcohol use depicted in fiction

DISALLOWED_KEYWORDS = [
    # Explicit CSAM (zero tolerance)
    r"\bcsam\b",
    r"\bchild\s+(porn|abuse|sex|sexual)\b",
    r"\bminor\s+sex(ual)?\b",
    # Explicit sexual content (NSFW) - we strip this entirely for Stripe compliance
    r"\b(?:explicit|pornographic|xxx|nsfw)\s+(?:sex|content|scene)\b",
    r"\b(?:anal|oral)\s+sex\b",
    r"\bsexual\s+(?:intercourse|act|content|scene)\b",
    r"\bsexual\s+\w+\b",  # catch "sexual violence", "sexual assault", etc.
    r"\berotic\s+(?:story|tale|scene|content)\b",
    r"\bnsfw\b",
    # Graphic gore / violence-for-arousal
    r"\b(?:torture|mutilat(?:e|ion)|disembowel(?:ed|ment))\b",
    r"\bgraphic\s+(?:gore|torture|violence)\b",
    r"\bviolence[- ]for[- ](?:arousal|pleasure|titillation)\b",
    # Identifiable private info (PII) for real people
    r"\b(?:[A-Z][a-z]+ ){2,}[A-Z][a-z]+\s+(?:SSN|address|phone|credit card)\b",
    # Hate targeting a specific protected class with intent to harm
    r"\b(?:kill|punch|attack)\s+(?:all|the)\s+(?:jews|muslims|christians|gays|blacks|whites|asians|trans)\b",
]

# Pre-compile for speed.
DISALLOWED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DISALLOWED_KEYWORDS]


# ----- Banned phrases to rewrite (post-gen sanitizer) -----
# Tuples of (pattern, replacement). Replacement is the safest rewrite
# that preserves narrative intent.

BANNED_PHRASES = [
    (re.compile(r"\b(?:kill yourself|kys)\b", re.IGNORECASE),
     "[content removed — please seek support]"),
    # Real-person doxxing attempt markers
    (re.compile(r"\b(?:their real address is|here'?s (?:his|her) (?:ssn|home address|unlisted phone))\b",
                re.IGNORECASE),
     "[content removed — private info]"),
    # Strong slurs — we sanitize but do not delete the story.
    # (Only the worst of the worst; this list stays short.)
    (re.compile(r"\b(?:n[i!1]gg[ae]r|f[a@]gg[o0]t|ch[i!1]nk|sp[i!1]c|k[i!1]ke)\b",
                re.IGNORECASE),
     "—"),
]


# ----- Word count ceilings (per-tier) -----
# v12 update: Free tier lowered to 300 words (matches "3 short stories"
# marketing copy). Pro and Creator unchanged.
TIER_WORD_CEILINGS = {
    "free":    300,
    "pro":     3000,
    "creator": 5000,
}


def check_prompt(prompt: str, subscriber_id: int = None,
                 db=None, log_to_db: bool = False) -> dict:
    """Pre-generation check. Returns one of:
        {"ok": True}
        {"ok": False, "reason": "<why>"} — generation must be refused.
    """
    if not isinstance(prompt, str):
        return {"ok": False, "reason": "Prompt must be text."}
    if not prompt.strip():
        return {"ok": False, "reason": "Prompt is empty."}
    if len(prompt) > 5000:
        return {"ok": False, "reason": "Prompt is too long (max 5000 characters)."}

    for pat in DISALLOWED_PATTERNS:
        if pat.search(prompt):
            verdict = {"ok": False,
                       "reason": "Your prompt contains content the platform can't generate. "
                                 "PocketPlot Universe is a creative platform for adult writers, "
                                 "but it doesn't produce explicit content (NSFW), graphic "
                                 "gore, or content targeting minors or real people with "
                                 "private info. Try a different angle."}
            _log_validation(db if log_to_db else None, subscriber_id, "pre",
                            "reject", verdict["reason"][:120], prompt[:120])
            return verdict

    _log_validation(db if log_to_db else None, subscriber_id, "pre",
                    "accept", "passed", prompt[:120])
    return {"ok": True}


def sanitize_output(text: str, subscriber_id: int = None,
                    db=None, log_to_db: bool = False) -> dict:
    """Post-generation scan. Returns:
        {"ok": True, "text": <sanitized>, "rewrites": <count>}
    Always returns ok=True unless the text is so full of banned phrases
    that we should refuse to send at all (>10% of words rewritten).
    """
    if not isinstance(text, str):
        return {"ok": False, "text": "", "rewrites": 0,
                "reason": "Output was not a string."}

    rewrites = 0
    sanitized = text
    for pat, repl in BANNED_PHRASES:
        new_text, n = pat.subn(repl, sanitized)
        if n:
            sanitized = new_text
            rewrites += n

    word_count = len(sanitized.split())
    if rewrites > 0 and rewrites > word_count * 0.10:
        _log_validation(db if log_to_db else None, subscriber_id, "post",
                        "reject", "too many rewrites", sanitized[:120])
        return {"ok": False, "text": "", "rewrites": rewrites,
                "reason": "Output could not be sanitized within policy."}

    if rewrites:
        _log_validation(db if log_to_db else None, subscriber_id, "post",
                        "rewrite", f"{rewrites} phrase(s) sanitized",
                        sanitized[:120])
    else:
        _log_validation(db if log_to_db else None, subscriber_id, "post",
                        "accept", "passed", sanitized[:120])
    return {"ok": True, "text": sanitized, "rewrites": rewrites}


def enforce_word_ceiling(text: str, tier: str) -> str:
    """Trim text to the tier's word ceiling. Returns the text unchanged
    if it's already under the ceiling."""
    ceiling = TIER_WORD_CEILINGS.get(tier, 1000)
    words = text.split()
    if len(words) <= ceiling:
        return text
    return " ".join(words[:ceiling])


def validate_for_tier(text: str, tier: str, subscriber_id: int = None,
                       db=None) -> dict:
    """Combined post-generation check: sanitize + word ceiling.
    Returns {"ok": bool, "text": str, "rewrites": int, "reason": str?}."""
    sanitized = sanitize_output(text, subscriber_id=subscriber_id,
                                db=db, log_to_db=True)
    if not sanitized["ok"]:
        return sanitized
    trimmed = enforce_word_ceiling(sanitized["text"], tier)
    return {"ok": True, "text": trimmed, "rewrites": sanitized["rewrites"]}


def _log_validation(db, subscriber_id, when, verdict, reason, snippet):
    """Persist a validation pass to validation_log. Silent on failure —
    validation logging must never block generation."""
    if db is None:
        return
    try:
        conn = db()
        conn.execute(
            "INSERT INTO validation_log(subscriber_id, pass, verdict, reason, snippet, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (subscriber_id, when, verdict, reason, snippet,
             dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"),
        )
        conn.commit(); conn.close()
    except Exception as e:
        log.warning("validation_log insert failed: %s", e)


# ============================================================================
# Phase 16 - Multi-layer moderation pipeline
# ============================================================================
#
# Brief asked for: pre-generation filter, post-generation guardrail, reasoning
# model for edge cases, and visual generator pipeline.
#
# What ships here:
#   - The Classifier interface (the contract any BYO backend implements)
#   - Three reference Classifier backends (keyword, noop, stub_llm)
#   - The pipeline orchestrator that runs all enabled stages
#   - A unified `validate_pipeline()` entry point used by the app
#
# What does NOT ship (deliberately, no new deps per the brief):
#   - Actual Llama Guard 3 8B model weights (8 GB binary, requires
#     `transformers` + GPU)
#   - Real OpenAI moderation API client (would add the `openai` SDK
#     as a new dep, and silently phone-home)
#   - Real GPT-4o-mini client (same)
#
# Operators who want these: install the SDK + provide credentials, then
# enable via env vars:
#   POCKETPLOT_MODERATION_BACKEND=openai_moderation
#   POCKETPLOT_MODERATION_API_KEY=sk-...
# The pipeline reads the env var at boot and routes accordingly. If no
# backend is enabled, the default = `keyword` only (current behavior).

import os as _os


# ----- Classifier contract -----
#
# A Classifier is a callable with this signature:
#
#   def my_classifier(text: str, *, role: str = "story") -> dict:
#       """Return {"verdict": "accept"|"reject"|"rewrite",
#                  "reason": str, "confidence": float}
#
# `role` lets the classifier apply different rules for prompts vs output
# (more aggressive on prompts - reject suspicious intent; more forgiving
# on output - rewrite borderline content).
#
# The pipeline calls the classifier with `role="prompt"` for the pre-filter
# and `role="output"` for the post-filter. Classifier backends can branch
# on this.

class ClassifierError(Exception):
    """Raised when a Classifier backend fails. The pipeline catches this
    and falls back to the next enabled stage (defense-in-depth)."""


def _noop_classifier(text: str, *, role: str = "story") -> dict:
    """Default stub: accepts everything. Used when no real classifier
    is configured. We log this honestly."""
    return {"verdict": "accept", "reason": "noop", "confidence": 0.0}


def _keyword_classifier(text: str, *, role: str = "story") -> dict:
    """Repackage the existing v12 keyword filter as a Classifier backend.
    Reuses `check_prompt()` for the pre-filter role and `sanitize_output()`
    for the post-filter role.
    """
    if role == "prompt":
        verdict = check_prompt(text)
        if not verdict.get("ok"):
            return {
                "verdict": "reject",
                "reason": verdict.get("reason", "keyword filter"),
                "confidence": 0.95,
            }
        return {"verdict": "accept", "reason": "keyword pass", "confidence": 0.95}
    # role == "output" - sanitize and check for rewrites
    sanitized = sanitize_output(text)
    if sanitized != text:
        # Something was rewritten
        return {
            "verdict": "rewrite",
            "reason": "keyword sanitizer rewrote disallowed phrases",
            "sanitized": sanitized,
            "confidence": 0.9,
        }
    return {"verdict": "accept", "reason": "keyword pass", "confidence": 0.95}


def _stub_llm_classifier(text: str, *, role: str = "story") -> dict:
    """Honest stub for the reasoning-model stage. In production, drop in
    a real client here (Llama Guard 3, OpenAI moderation, GPT-4o-mini).
    For now: ALWAYS raises ClassifierError so the pipeline falls through.
    Operators wire this up by replacing this function with their own.
    """
    raise ClassifierError(
        "stub_llm_classifier is a stub. To enable: replace this function "
        "with a real client call, set POCKETPLOT_MODERATION_BACKEND="
        "stub_llm, and provide credentials via env vars."
    )


# ---- Classifier registry ----
# Map of env-var name -> backend function. The pipeline reads
# POCKETPLOT_MODERATION_BACKEND to pick which to use.

CLASSIFIER_BACKENDS = {
    "noop":       _noop_classifier,
    "keyword":    _keyword_classifier,
    "stub_llm":   _stub_llm_classifier,
    # Operators can extend this dict with their own backends:
    #   import validation_system as v
    #   v.CLASSIFIER_BACKENDS["my_backend"] = my_classifier_fn
    # (See HANDOFF.md "BYO Moderation" section.)
}


def get_active_classifier():
    """Return the classifier backend the pipeline should call, based on
    POCKETPLOT_MODERATION_BACKEND. Defaults to `keyword`.
    """
    backend = (_os.environ.get("POCKETPLOT_MODERATION_BACKEND") or "keyword").lower()
    return CLASSIFIER_BACKENDS.get(backend, _keyword_classifier)


# ----- The pipeline orchestrator -----

def validate_pipeline(text: str, *, role: str = "story", tier: str = "free",
                       db=None) -> dict:
    """Multi-layer moderation pipeline. Returns the standard verdict shape:

        {
            "verdict":   "accept" | "reject" | "rewrite",
            "reason":    str,
            "text":      str  (rewritten if verdict == "rewrite"),
            "stages":    [dict, ...],  # one per stage that ran
            "length_ok": bool,
        }

    Pipeline order:
      1. Pre-filter keyword check (prompt role only)
      2. Length / word ceiling check (per tier)
      3. Configured safety classifier (default: keyword; optional: BYO)
      4. Sanitize / rewrite

    If any stage rejects, the pipeline short-circuits.
    If a stage rewrites, downstream stages see the rewritten text.
    """
    stages = []
    work_text = text

    # Stage 1: pre-filter (prompt role only).
    if role == "prompt":
        kw_pre = _keyword_classifier(work_text, role="prompt")
        stages.append({"stage": "keyword_pre", **kw_pre})
        if kw_pre["verdict"] == "reject":
            return {
                "verdict": "reject",
                "reason": kw_pre["reason"],
                "text": work_text,
                "stages": stages,
                "length_ok": True,
            }

    # Stage 2: length / word ceiling.
    length_ok = enforce_word_ceiling(work_text, tier=tier)
    stages.append({"stage": "word_ceiling", "verdict": "accept" if length_ok else "reject",
                    "tier": tier})
    if not length_ok:
        return {
            "verdict": "reject",
            "reason": f"exceeds word ceiling for tier={tier}",
            "text": work_text,
            "stages": stages,
            "length_ok": False,
        }

    # Stage 3: configured safety classifier.
    classifier = get_active_classifier()
    try:
        cls_result = classifier(work_text, role=role)
    except ClassifierError as e:
        # Defense-in-depth: fall through to keyword layer.
        log.warning("classifier backend failed, falling back to keyword: %s", e)
        cls_result = _keyword_classifier(work_text, role=role)
    stages.append({"stage": "classifier", **cls_result})

    if cls_result.get("verdict") == "reject":
        return {
            "verdict": "reject",
            "reason": cls_result.get("reason", "classifier rejected"),
            "text": work_text,
            "stages": stages,
            "length_ok": True,
        }
    if cls_result.get("verdict") == "rewrite" and "sanitized" in cls_result:
        work_text = cls_result["sanitized"]

    # Stage 4: always sanitize as a final pass (cheap defense-in-depth).
    final = sanitize_output(work_text)
    if final != work_text:
        stages.append({"stage": "sanitize_final", "verdict": "rewrite",
                        "reason": "final sanitizer applied"})
        work_text = final
    else:
        stages.append({"stage": "sanitize_final", "verdict": "accept",
                        "reason": "no changes needed"})

    return {
        "verdict": "accept",
        "reason": "all stages passed",
        "text": work_text,
        "stages": stages,
        "length_ok": True,
    }


# ----- Visual generator pipeline (v16 brief: "Graphics pipeline") -----
#
# The brief asks: visuals should be genre-styled and consistent, NOT
# generated by the user's LLM. We use the layered scene composers in
# story_image_composer.py to produce genre-appropriate SVG art.
#
# This pipeline is the orchestrator: given a (genre, scene_description),
# it picks the right composer and threads a style prompt.

DEFAULT_STYLE_PROMPT = (
    "cinematic, concept art style, warm lighting, "
    "genre-appropriate atmosphere, depth-of-field, "
    "high detail, no text, no watermark"
)


def compose_scene_for_genre(genre: str, *, style_prompt: str = None) -> dict:
    """v16 visual generator pipeline entry point.

    Returns {"svg": str, "style_prompt": str, "genre": str}.

    The brief specifies a universal Style Prompt that gets appended to
    every visual-generation request. We attach it to the response so
    downstream callers (admin previews, story pages) can display the
    style metadata. The actual SVG is produced by the 16-genre layered
    scene composer in story_image_composer.py.
    """
    style = style_prompt or DEFAULT_STYLE_PROMPT
    try:
        import story_image_composer as _sic
        svg = _sic.compose_layered_scene_v16(genre)
    except Exception as e:
        log.warning("scene composer failed for genre=%s: %s", genre, e)
        svg = ""
    return {
        "svg": svg,
        "style_prompt": style,
        "genre": genre,
    }
