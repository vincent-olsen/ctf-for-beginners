"""The first-blood feed (see __init__.py)."""

import calendar
import datetime

from flask import Blueprint, jsonify

from CTFd.cache import cache
from CTFd.models import Awards, Challenges, Solves, db
from CTFd.utils import get_config
from CTFd.utils.dates import unix_time_to_utc
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.modes import TEAMS_MODE, get_model

AI_PREFIX = "ai-"  # same rule as platform/plugins/ai_brackets and the theme
WINDOW = 900  # seconds an event stays in the feed; the theme announces 5 minutes' worth
CACHE_KEY = "ctf_firstblood:events"
# The events are recomputed when a solve is added or removed. Anything else they
# depend on (an account hidden or banned, a challenge renamed or hidden, the
# freeze, the user mode) shows within this many seconds.
CACHE_TIMEOUT = 15

first_blood = Blueprint("ctf_firstblood", __name__)


def _freeze():
    freeze = get_config("freeze")
    return unix_time_to_utc(freeze) if freeze else None


def _counts(freeze):
    """(count, newest id) of the solves and of the awards that are public."""
    solves = db.session.query(db.func.count(Solves.id), db.func.max(Solves.id))
    awards = db.session.query(db.func.count(Awards.id), db.func.max(Awards.id))
    if freeze is not None:
        solves = solves.filter(Solves.date < freeze)
        awards = awards.filter(Awards.date < freeze)
    return tuple(solves.one()), tuple(awards.one())


def _events(freeze):
    """Every visible challenge's first solve by a visible account, oldest first."""
    Model = get_model()
    account = Solves.team_id if get_config("user_mode") == TEAMS_MODE else Solves.user_id
    first = (
        db.session.query(db.func.min(Solves.id).label("id"))
        .join(Model, account == Model.id)
        .filter(Model.banned == False, Model.hidden == False)  # noqa: E712
    )
    if freeze is not None:
        first = first.filter(Solves.date < freeze)
    first = first.group_by(Solves.challenge_id).subquery()
    rows = (
        db.session.query(
            Solves.id,
            Solves.date,
            Solves.challenge_id,
            Challenges.name,
            Challenges.category,
            Challenges.value,
            Model.id.label("account_id"),
            Model.name.label("account"),
        )
        .join(first, Solves.id == first.c.id)
        .join(Challenges, Solves.challenge_id == Challenges.id)
        .join(Model, account == Model.id)
        .filter(Challenges.state == "visible")
        .order_by(Solves.id)
    )
    return [
        {
            "id": r.id,
            "ts": calendar.timegm(r.date.utctimetuple()),
            "challenge_id": r.challenge_id,
            "challenge": r.name,
            "category": r.category,
            "value": r.value,
            "bracket": "ai" if str(r.category or "").strip().lower().startswith(AI_PREFIX) else "normal",
            "account_id": r.account_id,
            "account": r.account,
        }
        for r in rows
    ]


@first_blood.route("/first-blood/feed")
@check_account_visibility
@check_score_visibility
def feed():
    freeze = _freeze()
    solves, awards = _counts(freeze)
    cached = cache.get(CACHE_KEY)
    if cached and cached.get("solves") == solves:
        events = cached["events"]
    else:
        events = _events(freeze)
        cache.set(CACHE_KEY, {"solves": solves, "events": events}, timeout=CACHE_TIMEOUT)
    now = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
    recent = [dict(e, age=max(0, now - e["ts"])) for e in events if now - e["ts"] <= WINDOW]
    response = jsonify(
        {
            "success": True,
            "data": {
                "rev": ".".join(str(n or 0) for n in solves + awards),
                "events": recent,
            },
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response
