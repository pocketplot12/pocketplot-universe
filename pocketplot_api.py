"""
PocketPlot Universe — REST API module (v11).

Mobile-ready JSON endpoints. Auth via the same magic-link session
cookies that /me uses, plus a Bearer-token shortcut for native mobile
clients (token = a long-lived random string stored on the subscriber).

Auth flows supported:
  1. Browser session cookie (existing magic-link flow).
  2. Bearer header (Authorization: Bearer <token>) — the token is a
     a magic-link token. To extend for native-mobile auth, future
     work can add a separate `api_tokens` table with 30-day TTLs.

Every response is JSON with shape:
    {"ok": True|False, "data": {...}|null, "error": "..."|null}

Error codes:
  401: not authenticated
  403: tier does not permit this action
  404: not found
  409: conflict (already exists, etc.)
  429: rate limited
  500: server error

DESIGN NOTE: This module doesn't `import app` at module level to avoid
circular imports. Instead, `register_api_routes(app, db, itsdangerous_loader)`
is called from app.py after all imports complete.
"""
import datetime as dt
import functools
import json
import logging
import re
from typing import Callable

log = logging.getLogger("pocketplot.api")


# ----- Globals set by register_api_routes() -----
_app = None
_db = None
_unsigner = None  # function(token) -> subscriber_id or None


def register_api_routes(app, db, unsigner):
    """Attach all /api/v1/* routes to the given Flask app."""
    global _app, _db, _unsigner
    _app = app
    _db = db
    _unsigner = unsigner

    from flask import request, jsonify, g
    import story_world
    import external_api_manager as ext

    def require_api_auth(view: Callable) -> Callable:
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            from flask import session as flask_session
            # 1. Cookie (browser magic-link flow).
            sid = flask_session.get("subscriber_id")
            # 2. Bearer header (mobile-friendly).
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                token = auth[7:].strip()
                sid = _unsigner(token) or sid
            if not sid:
                return jsonify({"ok": False, "error": "Not authenticated.",
                                "code": 401}), 401
            conn = _db()
            sub = conn.execute(
                "SELECT id, plan, tier FROM subscribers WHERE id=?",
                (sid,),
            ).fetchone()
            conn.close()
            if not sub:
                return jsonify({"ok": False, "error": "Subscriber not found.",
                                "code": 401}), 401
            g.api_subscriber_id = sub["id"]
            g.api_tier = sub["tier"] or ("pro" if sub["plan"] == "pro" else "free")
            return view(*args, **kwargs)
        return wrapper

    def _rate_limit_reason(reason: str) -> int:
        return 429 if "limit" in (reason or "").lower() else 500

    @app.route("/api/v1/me", methods=["GET"])
    @require_api_auth
    def api_v1_me():
        conn = _db()
        sub = conn.execute("SELECT * FROM subscribers WHERE id=?",
                            (g.api_subscriber_id,)).fetchone()
        conn.close()
        if not sub:
            return jsonify({"ok": False, "error": "Not found.", "code": 404}), 404
        return jsonify({
            "ok": True,
            "data": {
                "id": sub["id"],
                "email": sub["email"],
                "child_name": sub["child_name"],
                "child_age": sub["child_age"],
                "profile_type": sub["profile_type"] or "adult",
                "tier": sub["tier"] or ("pro" if sub["plan"] == "pro" else "free"),
                "active": bool(sub["active"]),
                "grandfathered_price": bool(sub["grandfathereProPrice"]),
                "calls_today": ext.calls_used_today(_db, sub["id"]),
                "calls_remaining": ext.calls_remaining_today(_db, sub["id"]),
                "calls_daily_limit": ext.daily_limit(),
            },
        })

    @app.route("/api/v1/worlds", methods=["GET"])
    @require_api_auth
    def api_v1_worlds_list():
        worlds = story_world.list_worlds(_db, g.api_subscriber_id)
        return jsonify({
            "ok": True,
            "data": [
                {
                    "id": w["id"],
                    "title": w["title"],
                    "genre": w["genre"],
                    "tone": w["tone"],
                    "setting": w["setting"],
                    "is_active": bool(w["is_active"]),
                    "created_at": w["created_at"],
                    "last_played_at": w["last_played_at"],
                }
                for w in worlds
            ],
        })

    @app.route("/api/v1/worlds", methods=["POST"])
    @require_api_auth
    def api_v1_worlds_create():
        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "").strip()[:120]
        if not title:
            return jsonify({"ok": False, "error": "title is required.",
                            "code": 400}), 400
        try:
            wid = story_world.create_world(
                _db, g.api_subscriber_id, title=title,
                genre=body.get("genre", "fantasy"),
                tone=body.get("tone", "hopeful"),
                setting=body.get("setting", "a quiet place"),
            )
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e), "code": 400}), 400
        return jsonify({"ok": True, "data": {"id": wid}}), 201

    @app.route("/api/v1/worlds/<int:wid>/episodes", methods=["POST"])
    @require_api_auth
    def api_v1_worlds_episode(wid):
        body = request.get_json(silent=True) or {}
        result = story_world.generate_episode(
            _db, g.api_subscriber_id, wid,
            choice_from_episode_id=body.get("choice_from_episode_id"),
            chosen_index=body.get("chosen_index"),
            tier=g.api_tier,
        )
        if not result.get("ok"):
            return jsonify({"ok": False,
                            "error": result.get("reason", "Failed."),
                            "code": 409}), 409
        return jsonify({"ok": True, "data": result})

    @app.route("/api/v1/byob/llm", methods=["POST"])
    @require_api_auth
    def api_v1_byob_llm():
        if g.api_tier != "creator":
            return jsonify({"ok": False,
                            "error": "BYOB requires the Creator tier.",
                            "code": 403}), 403
        body = request.get_json(silent=True) or {}
        system_prompt = (body.get("system") or "").strip()[:5000]
        user_prompt = (body.get("user") or "").strip()[:5000]
        if not user_prompt:
            return jsonify({"ok": False, "error": "user prompt required.",
                            "code": 400}), 400
        result = ext.call_llm(_db, g.api_subscriber_id, system_prompt,
                                user_prompt, tier=g.api_tier)
        if not result.get("ok"):
            return jsonify({"ok": False,
                            "error": result.get("reason", "Failed."),
                            "code": _rate_limit_reason(result.get("reason"))}), \
                _rate_limit_reason(result.get("reason"))
        return jsonify({"ok": True, "data": {
            "text": result["text"],
            "usage": result.get("usage", {}),
        }})

    @app.route("/api/v1/byob/image", methods=["POST"])
    @require_api_auth
    def api_v1_byob_image():
        if g.api_tier != "creator":
            return jsonify({"ok": False,
                            "error": "BYOG requires the Creator tier.",
                            "code": 403}), 403
        body = request.get_json(silent=True) or {}
        prompt = (body.get("prompt") or "").strip()[:2000]
        if not prompt:
            return jsonify({"ok": False, "error": "prompt required.",
                            "code": 400}), 400
        result = ext.call_image(_db, g.api_subscriber_id, prompt,
                                 tier=g.api_tier,
                                 model=body.get("model"),
                                 size=body.get("size", "1024x1024"))
        if not result.get("ok"):
            return jsonify({"ok": False,
                            "error": result.get("reason", "Failed."),
                            "code": _rate_limit_reason(result.get("reason"))}), \
                _rate_limit_reason(result.get("reason"))
        return jsonify({"ok": True, "data": result})

    @app.route("/api/v1/api-keys", methods=["GET", "POST", "DELETE"])
    @require_api_auth
    def api_v1_api_keys():
        if request.method == "GET":
            conn = _db()
            rows = conn.execute(
                "SELECT key_type, base_url, model_name, is_active, "
                "created_at, last_used_at FROM external_api_keys "
                "WHERE subscriber_id=? ORDER BY id DESC",
                (g.api_subscriber_id,),
            ).fetchall()
            conn.close()
            return jsonify({"ok": True, "data": [
                {
                    "key_type": r["key_type"],
                    "base_url": r["base_url"],
                    "model_name": r["model_name"],
                    "is_active": bool(r["is_active"]),
                    "created_at": r["created_at"],
                    "last_used_at": r["last_used_at"],
                }
                for r in rows
            ]})

        if g.api_tier != "creator":
            return jsonify({"ok": False,
                            "error": "API key management requires the Creator tier.",
                            "code": 403}), 403

        body = request.get_json(silent=True) or {}
        if request.method == "POST":
            key_type = body.get("key_type") or ""
            api_key = body.get("api_key") or ""
            base_url = body.get("base_url") or ""
            model_name = body.get("model_name") or ""
            if key_type not in ("llm", "image"):
                return jsonify({"ok": False,
                                "error": "key_type must be llm or image.",
                                "code": 400}), 400
            if not api_key or len(api_key) < 8:
                return jsonify({"ok": False,
                                "error": "api_key must be at least 8 chars.",
                                "code": 400}), 400
            kid = ext.save_api_key(_db, g.api_subscriber_id, key_type,
                                    api_key, base_url=base_url or None,
                                    model_name=model_name or None)
            return jsonify({"ok": True, "data": {"id": kid}}), 201

        key_type = (body.get("key_type") or "").strip()
        if key_type not in ("llm", "image"):
            return jsonify({"ok": False,
                            "error": "key_type must be llm or image.",
                            "code": 400}), 400
        ok = ext.deactivate_api_key(_db, g.api_subscriber_id, key_type)
        return jsonify({"ok": True, "data": {"deactivated": ok}})

    log.info("registered %d /api/v1/* routes", 7)
