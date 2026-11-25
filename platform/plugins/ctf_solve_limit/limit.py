"""Lock a challenge once its max_solves is reached (see __init__.py)."""

import json

from flask import Blueprint, jsonify, request

from CTFd.models import Challenges, Solves, db
from CTFd.utils import get_config
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_challenge_visibility,
)
from CTFd.utils.modes import TEAMS_MODE, get_model
from CTFd.utils.user import authed, get_current_user, is_admin

LIMIT_CONFIG = "ctf_solve_limit"  # same key as platform/ctfd_admin.py
ATTEMPT_PATH = "/api/v1/challenges/attempt"
# platform/theme/i18n.strings.js translates it (ctfd).
MESSAGE = "Too late: this flag has already been found"

solve_limit = Blueprint("ctf_solve_limit", __name__)


def limits():
    """{challenge id: max solves}, empty when no challenge has a limit."""
    try:
        stored = json.loads(get_config(LIMIT_CONFIG) or "{}")
        return {int(cid): int(n) for cid, n in stored.items() if int(n) > 0}
    except (AttributeError, TypeError, ValueError):
        return {}


def _account_column():
    return Solves.team_id if get_config("user_mode") == TEAMS_MODE else Solves.user_id


def solvers(challenge_id):
    """(account id, name) of the visible accounts that solved it, first one first."""
    Model = get_model()
    return (
        db.session.query(Model.id, Model.name)
        .join(Solves, _account_column() == Model.id)
        .filter(Solves.challenge_id == challenge_id)
        .filter(Model.banned == False, Model.hidden == False)  # noqa: E712
        .order_by(Solves.id)
        .all()
    )


def before_request():
    # The path first: every other request skips the rest.
    if request.method != "POST" or request.path.rstrip("/") != ATTEMPT_PATH:
        return None
    if not authed() or is_admin():
        return None  # CTFd refuses the first; an admin tests the flag as usual
    data = request.get_json(silent=True) or request.form
    try:
        challenge_id = int(data.get("challenge_id"))
    except (AttributeError, TypeError, ValueError):
        return None  # CTFd answers a request it can't read
    limit = limits().get(challenge_id)
    if limit is None:
        return None
    user = get_current_user()
    found = solvers(challenge_id)
    if user is None or len(found) < limit or user.account_id in {i for i, _name in found}:
        return None
    # The shape and code of CTFd's "paused" answer, which the challenge window
    # shows as a warning without counting a wrong flag.
    return jsonify({"success": True, "data": {"status": "paused", "message": MESSAGE}}), 403


@solve_limit.route("/solve-limit/status")
@check_challenge_visibility
@check_account_visibility
def status():
    data = {}
    wanted = limits()
    if wanted:
        rows = Challenges.query.filter(Challenges.id.in_(wanted), Challenges.state == "visible").all()
        for challenge in rows:
            names = [name for _id, name in solvers(challenge.id)]
            limit = wanted[challenge.id]
            data[str(challenge.id)] = {
                "name": challenge.name,
                "limit": limit,
                "locked": len(names) >= limit,
                "by": names[:limit],
            }
    response = jsonify({"success": True, "data": data})
    response.headers["Cache-Control"] = "no-store"
    return response
