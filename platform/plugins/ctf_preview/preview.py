"""Anonymous flag checks while a preview is set (see __init__.py)."""

import json
import time

from flask import jsonify, redirect, request, url_for

from CTFd.cache import cache
from CTFd.models import Challenges
from CTFd.plugins.challenges import get_chal_class
from CTFd.utils import config, get_config
from CTFd.utils.dates import ctf_paused, ctftime
from CTFd.utils.user import authed, get_ip, is_admin

PREVIEW_CONFIG = "ctf_preview"  # same key as platform/ctfd_admin.py
ATTEMPT_PATH = "/api/v1/challenges/attempt"
# Wrong flags per minute from one IP address. CTFd allows 10 per account, but a
# preview's visitors share addresses: everyone at the office, and on its VPN,
# comes from the same one. Counted per clock minute, so the count starts over every
# minute however busy the address is.
WRONG_PER_MINUTE = 60


def preview_ids():
    """The preview's challenge ids, or None while no preview is set."""
    try:
        state = json.loads(get_config(PREVIEW_CONFIG) or "null")
    except (TypeError, ValueError):
        return None
    if not isinstance(state, dict):
        return None
    return {int(i) for i in state.get("challenges") or []}


def _answer(status, message, code=200):
    """CTFd's own attempt response, which the challenge window renders."""
    return jsonify({"success": True, "data": {"status": status, "message": message}}), code


def _refuse(code, message):
    """A refused attempt, in the same shape: the window shows the message."""
    return _answer("error", message, code)


def before_request():
    # The path first: only these two need the preview's state, and every other
    # request (each stylesheet, script and API call) skips the lookup.
    if request.method == "GET" and request.path == "/":
        if preview_ids() is None or is_admin():
            return None
        return redirect(url_for("challenges.listing"))
    if request.method != "POST" or request.path != ATTEMPT_PATH or authed():
        return None
    ids = preview_ids()
    if ids is None:
        return None
    if not ctftime():
        return None  # CTFd answers that the CTF hasn't started, or has ended
    if ctf_paused():
        return _answer("paused", "{} is paused".format(config.ctf_name()), 403)
    return _attempt(ids)


def _attempt(ids):
    data = request.get_json(silent=True) or request.form
    try:
        challenge_id = int(data.get("challenge_id"))
    except (TypeError, ValueError):
        return _refuse(400, "challenge_id is missing")
    challenge = Challenges.query.filter_by(id=challenge_id).first()
    if challenge is None or challenge.id not in ids or challenge.state != "visible":
        return _refuse(404, "No such challenge")
    if (challenge.requirements or {}).get("prerequisites"):
        return _refuse(403, "This challenge needs another one solved first")

    key = "ctf_preview_wrong:{}:{}".format(get_ip(), int(time.time() // 60))
    if int(cache.get(key) or 0) >= WRONG_PER_MINUTE:
        return _answer("ratelimited", "You're submitting flags too fast. Slow down.", 429)

    try:
        result = get_chal_class(challenge.type).attempt(challenge, request)
    except Exception:  # noqa: BLE001 - no submission, or a type that needs an account
        return _refuse(400, "Could not check that flag")
    # CTFd 3.8 returns a ChallengeResponse; older challenge types a (bool, message) tuple.
    if isinstance(result, tuple):
        status, message = ("correct" if result[0] else "incorrect"), result[1]
    else:
        status, message = result.status, result.message
    if status != "correct":
        # inc() is an atomic INCR in Redis, so wrong flags sent at the same time
        # each count, then the key gets its expiry, as CTFd's own attempt
        # counter does. Never add() a starting 0: cachelib pickles it, and
        # Redis then refuses to INCR the value (a 500 on every wrong flag).
        cache.inc(key)
        cache.expire(key, 120)
    return _answer(status, message)
