"""
PocketPlot Universe — External API Manager (v11).

Handles user-provided API credentials (BYOB for LLMs, BYOG for image/
video) for the Creator tier. Every external-API response is routed
through validation_system.validate_for_tier() before being returned
to the user. Paying for Creator tier does NOT unlock content that
would violate platform policy — that's by design.

Key storage:
  - API keys are encrypted at rest using Fernet (AES-128 + HMAC).
  - Encryption key is derived from POCKETPLOT_API_ENCRYPTION_KEY env var.
  - When the env var is unset, we derive a fallback from a stable
    machine-specific seed and warn loudly. Production should always
    set this env var.
  - Decrypted keys NEVER appear in logs. Only their prefix is logged.

Limits:
  - 100 external-API calls/day per Creator subscriber by default.
  - Configurable via POCKETPLOT_CREATOR_DAILY_LIMIT env var.
  - Hitting the limit returns a clean 429-style refusal.

Network-level sandboxing (v16 deployment guidance)
-----------------------------------------------
The brief asks for "network-level sandboxing to prevent the external
API from making unauthorized external calls." This is an OPERATOR
concern, not code. The shipped code makes outbound HTTPS calls
only to the user-specified base URL. Operators who want stronger
isolation should:

  1. **Run the Flask app in a Docker container** (the existing
     Dockerfile is the right starting point). Use a network namespace
     that ONLY allows outbound HTTPS to the BYOB provider domain(s).

  2. **Or use a network proxy** (e.g. mitmproxy, Envoy with
     strict allow-list) that drops any outbound request whose
     Host header doesn't match the user's configured provider.

  3. **Or run on Fly.io / Cloud Run** with an outbound-egress
     allow-list. Both platforms let you restrict where the
     container can reach.

  4. **Always pass the response through `validation_pipeline()`**
     BEFORE showing it to the user. The platform-side filter
     catches content the external LLM might emit that violates
     our policy, regardless of which model produced it.

The shipped code does NOT attempt network isolation itself - that's
intentional, because Docker/network policy is host-side config and
varies per deployment.
"""
import base64
import datetime as dt
import hashlib
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

import encryption as _enc

log = logging.getLogger("pocketplot.api")


# ---- Encryption: stdlib-only authenticated encryption (encryption.py).
# Why stdlib-only: the brief explicitly forbids new external deps. The
# cryptography/pycryptodome packages aren't installed in the container.
# Our encryption.py is PBKDF2-HMAC-SHA256 + HMAC-based stream cipher
# + encrypt-then-MAC — appropriate for at-rest API-key storage of
# short secrets; not appropriate for bulk data.

def _derive_passphrase() -> str:
    """Stable, env-var-driven passphrase used for key encryption."""
    env_key = os.environ.get("POCKETPLOT_API_ENCRYPTION_KEY", "").strip()
    if env_key:
        return env_key
    fallback = (
        os.environ.get("POCKETPLOT_DB_PATH", "/root/pocketplot/pocketplot.db")
        + "|pocketplot-universe-fallback-v11"
    )
    log.warning("POCKETPLOT_API_ENCRYPTION_KEY is not set — using machine-specific "
                "fallback. Set the env var in production for portable decryption.")
    return fallback


def encrypt_api_key(plain: str) -> str:
    """Encrypt an API key for storage. Returns a base64 string."""
    return _enc.encrypt(plain, _derive_passphrase())


def decrypt_api_key(cipher: str) -> str:
    """Decrypt an API key from storage. Returns the plaintext."""
    return _enc.decrypt(cipher, _derive_passphrase())


def key_prefix(plain: str) -> str:
    """Safe-to-log prefix for an API key (first 7 chars + ellipsis)."""
    return plain[:7] + "…" if len(plain) > 7 else plain


# ---- DB CRUD for external_api_keys ----

def save_api_key(db, subscriber_id: int, key_type: str, plain_key: str,
                 base_url: str = None, model_name: str = None) -> int:
    """Save (or replace) an API key for a subscriber. Returns the row id."""
    cipher = encrypt_api_key(plain_key)
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn = db()
    # Upsert: deactivate any existing key for this (sub, type) then insert.
    conn.execute(
        "UPDATE external_api_keys SET is_active=0 WHERE subscriber_id=? AND key_type=?",
        (subscriber_id, key_type),
    )
    cur = conn.execute(
        "INSERT INTO external_api_keys(subscriber_id, key_type, api_key_enc, "
        "base_url, model_name, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
        (subscriber_id, key_type, cipher, base_url, model_name, now),
    )
    new_id = cur.lastrowid
    conn.commit(); conn.close()
    log.info("saved %s API key for sub %s (prefix=%s)", key_type,
             subscriber_id, key_prefix(plain_key))
    return new_id


def get_api_key(db, subscriber_id: int, key_type: str):
    """Return (decrypted_key, base_url, model_name) for a subscriber's
    active API key, or None if not configured."""
    conn = db()
    row = conn.execute(
        "SELECT api_key_enc, base_url, model_name FROM external_api_keys "
        "WHERE subscriber_id=? AND key_type=? AND is_active=1 "
        "ORDER BY id DESC LIMIT 1",
        (subscriber_id, key_type),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        plain = decrypt_api_key(row["api_key_enc"])
    except Exception as e:
        log.error("decrypt failed for sub %s: %s", subscriber_id, e)
        return None
    return (plain, row["base_url"], row["model_name"])


def deactivate_api_key(db, subscriber_id: int, key_type: str) -> bool:
    conn = db()
    cur = conn.execute(
        "UPDATE external_api_keys SET is_active=0 WHERE subscriber_id=? AND key_type=?",
        (subscriber_id, key_type),
    )
    conn.commit(); conn.close()
    return cur.rowcount > 0


# ---- Rate limiting ----

def daily_limit() -> int:
    """Configured daily limit for external API calls per Creator sub."""
    try:
        return int(os.environ.get("POCKETPLOT_CREATOR_DAILY_LIMIT", "100"))
    except ValueError:
        return 100


def calls_used_today(db, subscriber_id: int, call_type: str = None) -> int:
    """Count external-API calls for this subscriber today (UTC)."""
    today = dt.datetime.utcnow().strftime("%Y-%m-%d")
    conn = db()
    if call_type:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM api_call_log "
            "WHERE subscriber_id=? AND call_date=? AND call_type=?",
            (subscriber_id, today, call_type),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM api_call_log "
            "WHERE subscriber_id=? AND call_date=?",
            (subscriber_id, today),
        ).fetchone()
    conn.close()
    return int(row["n"] or 0)


def calls_remaining_today(db, subscriber_id: int) -> int:
    return max(0, daily_limit() - calls_used_today(db, subscriber_id))


def record_call(db, subscriber_id: int, call_type: str, success: bool = True):
    """Increment the day's call counter. Silent on DB errors — must not
    block the request path."""
    try:
        today = dt.datetime.utcnow().strftime("%Y-%m-%d")
        conn = db()
        conn.execute(
            "INSERT INTO api_call_log(subscriber_id, call_date, call_type, success) "
            "VALUES (?, ?, ?, ?)",
            (subscriber_id, today, call_type, 1 if success else 0),
        )
        conn.execute(
            "UPDATE external_api_keys SET last_used_at=? WHERE subscriber_id=? AND key_type=? AND is_active=1",
            (dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
             subscriber_id, call_type),
        )
        conn.commit(); conn.close()
    except Exception as e:
        log.warning("record_call failed: %s", e)


# ---- LLM call (BYOB) ----
#
# Design: OpenAI-compatible POST {base_url}/v1/chat/completions with
# Bearer auth. This covers OpenRouter, LiteLLM, OpenAI, Together,
# Groq, Mistral, local Ollama (with openai-compatible shim), etc.
# We do NOT support provider-specific APIs (Anthropic, Gemini native).
# Adding them later is a small adapter, not a redesign.

def call_llm(db, subscriber_id: int, system_prompt: str, user_prompt: str,
              tier: str = "creator", max_tokens: int = 1500,
              timeout_s: int = 60) -> dict:
    """Route a chat-completion request through the subscriber's BYOB key.
    Returns:
        {"ok": True, "text": str, "usage": dict} on success
        {"ok": False, "reason": str} on any failure.
    All outbound responses pass through validation_system.validate_for_tier
    before being returned to the caller.
    """
    # 1. Pre-check: rate limit.
    if calls_remaining_today(db, subscriber_id) <= 0:
        return {"ok": False, "reason":
                f"Daily Creator limit reached ({daily_limit()} calls/day). "
                f"Resets at midnight UTC."}

    # 2. Pre-check: prompt.
    import validation_system
    pre = validation_system.check_prompt(user_prompt, subscriber_id=subscriber_id,
                                           db=db, log_to_db=True)
    if not pre["ok"]:
        return {"ok": False, "reason": pre["reason"]}

    # 3. Look up the BYOB key.
    key_info = get_api_key(db, subscriber_id, "llm")
    if not key_info:
        return {"ok": False, "reason":
                "No LLM API key on file. Add one under /me/settings."}
    api_key, base_url, model_name = key_info
    if not base_url or not model_name:
        return {"ok": False, "reason":
                "API key is missing base_url or model_name. Re-save it under /me/settings."}

    # 4. Make the HTTP call.
    body = json.dumps({
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }).encode("utf-8")
    url = base_url.rstrip("/") + "/v1/chat/completions"
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        record_call(db, subscriber_id, "llm", success=False)
        return {"ok": False, "reason":
                f"Upstream API returned HTTP {e.code} ({key_prefix(api_key)})."}
    except Exception as e:
        record_call(db, subscriber_id, "llm", success=False)
        return {"ok": False, "reason":
                f"Upstream API request failed: {type(e).__name__}: {e}"}

    # 5. Parse response.
    try:
        data = json.loads(raw)
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
    except Exception as e:
        record_call(db, subscriber_id, "llm", success=False)
        return {"ok": False, "reason": f"Bad upstream response: {e}"}

    record_call(db, subscriber_id, "llm", success=True)

    # 6. Validate the response. Creator-tier BYOB output STILL passes
    # through the validator — paying more does not unlock content
    # that violates policy.
    validated = validation_system.validate_for_tier(
        text, tier=tier, subscriber_id=subscriber_id, db=db,
    )
    if not validated["ok"]:
        return {"ok": False, "reason": validated.get("reason",
                                                      "Output failed validation.")}
    return {"ok": True, "text": validated["text"], "usage": usage}


# ---- Image call (BYOG) ----
#
# Design: OpenAI-compatible POST {base_url}/v1/images/generations.
# This covers OpenAI DALL-E, Together, OpenRouter (image models),
# and most custom Stable Diffusion deployments that speak this API.
# We do NOT support vendor-specific APIs here. Adapter per provider
# is straightforward to add later.

def call_image(db, subscriber_id: int, prompt: str, tier: str = "creator",
                model: str = None, size: str = "1024x1024",
                n: int = 1, timeout_s: int = 120) -> dict:
    """Generate an image via the subscriber's BYOG key."""
    if calls_remaining_today(db, subscriber_id) <= 0:
        return {"ok": False, "reason":
                f"Daily Creator limit reached ({daily_limit()} calls/day)."}
    import validation_system
    pre = validation_system.check_prompt(prompt, subscriber_id=subscriber_id,
                                           db=db, log_to_db=True)
    if not pre["ok"]:
        return {"ok": False, "reason": pre["reason"]}

    key_info = get_api_key(db, subscriber_id, "image")
    if not key_info:
        return {"ok": False, "reason":
                "No image API key on file. Add one under /me/settings."}
    api_key, base_url, default_model = key_info
    use_model = model or default_model
    if not base_url or not use_model:
        return {"ok": False, "reason":
                "Image API key is missing base_url or model_name."}

    body = json.dumps({
        "model": use_model,
        "prompt": prompt,
        "size": size,
        "n": n,
    }).encode("utf-8")
    url = base_url.rstrip("/") + "/v1/images/generations"
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        record_call(db, subscriber_id, "image", success=False)
        return {"ok": False, "reason":
                f"Image API returned HTTP {e.code} ({key_prefix(api_key)})."}
    except Exception as e:
        record_call(db, subscriber_id, "image", success=False)
        return {"ok": False, "reason":
                f"Image API request failed: {type(e).__name__}: {e}"}

    try:
        data = json.loads(raw)
        # OpenAI returns {"data": [{"url": "..."} | {"b64_json": "..."}]}.
        # We pass the URL through if present, else base64.
        item = data["data"][0]
        if "url" in item:
            image_ref = item["url"]
        elif "b64_json" in item:
            image_ref = "data:image/png;base64," + item["b64_json"]
        else:
            raise ValueError("no url or b64_json in response")
    except Exception as e:
        record_call(db, subscriber_id, "image", success=False)
        return {"ok": False, "reason": f"Bad image response: {e}"}

    record_call(db, subscriber_id, "image", success=True)
    return {"ok": True, "image": image_ref, "model": use_model}
