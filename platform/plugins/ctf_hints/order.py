"""Refuse buying a hint whose prerequisites the account lacks (see __init__.py)."""

from flask import jsonify, request

from CTFd.models import Hints, HintUnlocks
from CTFd.utils.user import get_current_user

UNLOCKS_PATH = "/api/v1/unlocks"
# CTFd's own words for opening such a hint (CTFd/api/v1/hints.py), which
# platform/theme/i18n.strings.js translates.
MESSAGE = "You must unlock other hints before accessing this hint"


def before_request():
    # The path first: every other request skips the rest.
    if request.method != "POST" or request.path.rstrip("/") != UNLOCKS_PATH:
        return None
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("type") != "hints":
        return None
    try:
        hint_id = int(data.get("target"))
    except (TypeError, ValueError):
        return None  # CTFd answers a request it can't read
    user = get_current_user()
    if user is None or user.account_id is None:
        return None  # not logged in, or no team yet: CTFd refuses those itself
    hint = Hints.query.filter_by(id=hint_id).first()
    if hint is None or not hint.prerequisites:
        return None
    # As CTFd does when the hint is opened: prerequisites that no longer exist
    # don't count, and the account (the team, in teams mode) holds the unlocks.
    existing = {i for (i,) in Hints.query.with_entities(Hints.id)}
    unlocked = {u.target for u in HintUnlocks.query.filter_by(account_id=user.account_id)}
    if set(hint.prerequisites) & existing <= unlocked:
        return None
    return jsonify({"success": False, "errors": {"requirements": [MESSAGE]}}), 403
