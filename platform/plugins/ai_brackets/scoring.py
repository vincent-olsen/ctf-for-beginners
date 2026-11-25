"""Per-bracket standings and the read-only endpoints (see __init__.py)."""

import hashlib
import heapq
import re
import time
from collections import defaultdict

from flask import Blueprint, abort, request
from sqlalchemy import or_

from CTFd.cache import cache
from CTFd.models import Awards, Challenges, Hints, Solves, Users, db
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat, unix_time_to_utc
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.humanize.numbers import ordinalize
from CTFd.utils.modes import (
    TEAMS_MODE,
    generate_account_url,
    get_mode_as_word,
    get_model,
)
from CTFd.utils.user import authed, get_current_user, is_admin

try:
    from CTFd.models import Brackets  # CTFd 3.7+
except ImportError:
    Brackets = None

AI_PREFIX = "ai-"  # same rule as platform/theme/ai-mode.js
BRACKETS = ("normal", "ai")
# The scoreboards: one per bracket, and "all", where an account is listed once
# per bracket it plays in.
BOARDS = BRACKETS + ("all",)
HINT_AWARD = re.compile(r"^Hint (\d+)$")
WINNERS_TOP = 3  # places per bracket on the podium page (/ai-brackets/winners)
TOP_MAX = 50  # most accounts /scoreboard/top/<n> returns, as in stock CTFd
CACHE_KEY = "ai_brackets:scores"
CACHE_TIMEOUT = 60

ai_brackets = Blueprint("ai_brackets", __name__)


def bracket_of(category):
    return "ai" if str(category or "").strip().lower().startswith(AI_PREFIX) else "normal"


def _fingerprint():
    """Changes whenever anything the standings depend on changes: a solve or
    award added or removed, a challenge's value or category, a hint's
    challenge, an account banned or hidden, the user mode or the freeze. CTFd
    clears its own scoreboard cache on those events, but not ours, so we
    compare against this on every request instead. Renames and bracket changes
    show within CACHE_TIMEOUT."""
    Model = get_model()
    parts = [
        tuple(db.session.query(db.func.count(Solves.id), db.func.max(Solves.id)).one()),
        tuple(db.session.query(db.func.count(Awards.id), db.func.max(Awards.id)).one()),
        [
            tuple(r)
            for r in db.session.query(Challenges.id, Challenges.value, Challenges.category)
            .order_by(Challenges.id)
        ],
        [tuple(r) for r in db.session.query(Hints.id, Hints.challenge_id).order_by(Hints.id)],
        [
            r.id
            for r in db.session.query(Model.id)
            .filter(or_(Model.banned == True, Model.hidden == True))  # noqa: E712
            .order_by(Model.id)
        ],
        get_config("user_mode"),
        get_config("freeze"),
    ]
    return hashlib.sha1(repr(parts).encode()).hexdigest()


def _scoring_rows(frozen=True):
    """Every solve and award that counts, as dicts tagged with their bracket.
    frozen=False also counts what came after the scoreboard freeze (the final
    result, for the podium page's presenter)."""
    solves = (
        db.session.query(
            Solves.id,
            Solves.user_id,
            Solves.team_id,
            Solves.challenge_id,
            Solves.date,
            Challenges.value,
            Challenges.category,
        )
        .join(Challenges, Solves.challenge_id == Challenges.id)
        .filter(Challenges.value != 0)
    )
    awards = db.session.query(
        Awards.id,
        Awards.user_id,
        Awards.team_id,
        Awards.date,
        Awards.value,
        Awards.category,
        Awards.name,
    ).filter(Awards.value != 0)

    freeze = get_config("freeze") if frozen else None
    if freeze:
        solves = solves.filter(Solves.date < unix_time_to_utc(freeze))
        awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

    hint_category = dict(
        db.session.query(Hints.id, Challenges.category).join(
            Challenges, Hints.challenge_id == Challenges.id
        )
    )

    for s in solves:
        yield {
            "bracket": bracket_of(s.category),
            "hint": False,
            "id": s.id,
            "user_id": s.user_id,
            "team_id": s.team_id,
            "challenge_id": s.challenge_id,
            "value": s.value,
            "date": s.date,
        }
    for a in awards:
        category = a.category
        hint = HINT_AWARD.match(a.name or "") if a.category == "hints" else None
        if hint:
            category = hint_category.get(int(hint.group(1)))
        yield {
            "bracket": bracket_of(category),
            "hint": bool(hint),
            "id": a.id,
            "user_id": a.user_id,
            "team_id": a.team_id,
            "challenge_id": None,
            "value": a.value,
            "date": a.date,
        }


def _accounts(account_ids):
    """Visible (not banned, not hidden) accounts among account_ids."""
    Model = get_model()
    columns = [Model.id, Model.oauth_id, Model.name]
    if Brackets is not None:
        columns += [Model.bracket_id, Brackets.name.label("bracket_name")]
    query = db.session.query(*columns)
    if Brackets is not None:
        query = query.join(Brackets, Model.bracket_id == Brackets.id, isouter=True)
    return {
        a.id: {
            "account_id": a.id,
            "oauth_id": a.oauth_id,
            "name": a.name,
            "bracket_id": getattr(a, "bracket_id", None),
            "bracket_name": getattr(a, "bracket_name", None),
        }
        for a in query.filter(Model.banned == False, Model.hidden == False)  # noqa: E712
        .filter(Model.id.in_(list(account_ids)))
    }


def _compute(frozen=True):
    """Standings, member scores and (for the top accounts) scoring rows of both
    brackets, from one pass over the solves and awards, plus the standings of
    the "all" board.

    Mirrors CTFd.utils.scores.get_standings(admin=False): accounts are ordered
    by score, then the date and id of their latest row. An account is listed in
    a bracket when it has a solve or award there other than a hint unlock, so
    spending combined points on a hint doesn't put a team on a scoreboard it
    hasn't played. Every standing says which bracket it is in (ai_bracket).

    The "all" board lists an account once per bracket it is listed in, with
    that bracket's score, ranked by the same rule: a team that plays both is
    there twice, never with the two scores added together. Its standings are
    the two brackets' merged, so each bracket keeps its own order and the top
    of "all" is always within the top of each bracket, whose rows are kept.

    frozen=False ignores the scoreboard freeze (see _scoring_rows).
    """
    teams = get_config("user_mode") == TEAMS_MODE

    totals = {b: {} for b in BRACKETS}  # account_id -> [score, latest date, latest id]
    played = {b: set() for b in BRACKETS}
    user_scores = {b: defaultdict(int) for b in BRACKETS}
    rows_by_account = {b: defaultdict(list) for b in BRACKETS}
    for r in _scoring_rows(frozen):
        b = r["bracket"]
        account_id = r["team_id"] if teams else r["user_id"]
        if account_id is None:
            continue
        t = totals[b].setdefault(account_id, [0, r["date"], r["id"]])
        t[0] += r["value"]
        t[1] = max(t[1], r["date"])
        t[2] = max(t[2], r["id"])
        if not r["hint"]:
            played[b].add(account_id)
        if r["user_id"] is not None:
            user_scores[b][r["user_id"]] += r["value"]
        rows_by_account[b][account_id].append(r)

    accounts = _accounts(played["normal"] | played["ai"]) if any(played.values()) else {}

    result = {}
    ranked = {}  # bracket -> [(sort key, standing)], best first
    for b in BRACKETS:
        ids = [i for i in played[b] if i in accounts]
        ids.sort(key=lambda i: (-totals[b][i][0], totals[b][i][1], totals[b][i][2]))
        standings = [dict(accounts[i], score=int(totals[b][i][0]), ai_bracket=b) for i in ids]
        ranked[b] = [
            ((-totals[b][i][0], totals[b][i][1], totals[b][i][2]), s)
            for i, s in zip(ids, standings)
        ]

        # The graph only ever needs the rows of the top TOP_MAX accounts, overall
        # or within one CTFd bracket (the bracket_id filter), so keep only those.
        keep, per_group = set(), defaultdict(int)
        for pos, s in enumerate(standings):
            per_group[s["bracket_id"]] += 1
            if pos < TOP_MAX or per_group[s["bracket_id"]] <= TOP_MAX:
                keep.add(s["account_id"])
        # Rows oldest first, shaped like get_scoreboard_detail's "solves".
        rows = {
            account_id: [
                {
                    "challenge_id": r["challenge_id"],
                    "account_id": account_id,
                    "team_id": r["team_id"],
                    "user_id": r["user_id"],
                    "value": r["value"],
                    "date": isoformat(r["date"]),
                }
                for r in sorted(rows_by_account[b][account_id], key=lambda r: r["date"])
            ]
            for account_id in keep
        }
        result[b] = {
            "standings": standings,
            "user_scores": dict(user_scores[b]),
            "rows": rows,
        }
    # heapq.merge keeps each list's order, and on a full tie puts the normal
    # bracket's standing first.
    merged = heapq.merge(*(ranked[b] for b in BRACKETS), key=lambda e: e[0])
    result["all"] = {"standings": [s for _, s in merged]}
    return result


def all_scores():
    """Both brackets' scores and the "all" board, recomputed when the
    fingerprint changes. One cache key, so a solve replaces the entry instead
    of adding one."""
    fingerprint = _fingerprint()
    cached = cache.get(CACHE_KEY)
    if cached and cached.get("fingerprint") == fingerprint:
        return cached["scores"]
    scores = _compute()
    cache.set(CACHE_KEY, {"fingerprint": fingerprint, "scores": scores}, timeout=CACHE_TIMEOUT)
    return scores


def _requested_board():
    board = request.args.get("bracket", "")
    if board not in BOARDS:
        abort(400, description="bracket must be one of: " + ", ".join(BOARDS))
    return board


def _members(team_ids, user_scores):
    """Visible members of the listed teams, like the stock scoreboard's members."""
    members = defaultdict(list)
    if not team_ids:
        return members
    columns = [Users.id, Users.name, Users.oauth_id, Users.team_id]
    if Brackets is not None:
        columns += [Users.bracket_id, Brackets.name.label("bracket_name")]
    users = db.session.query(*columns)
    if Brackets is not None:
        users = users.join(Brackets, Users.bracket_id == Brackets.id, isouter=True)
    users = (
        users.filter(Users.team_id.in_(team_ids))
        .filter(Users.banned == False, Users.hidden == False)  # noqa: E712
        .order_by(Users.id)
    )
    for u in users:
        members[u.team_id].append(
            {
                "id": u.id,
                "oauth_id": u.oauth_id,
                "name": u.name,
                "score": int(user_scores.get(u.id, 0)),
                "bracket_id": getattr(u, "bracket_id", None),
                "bracket_name": getattr(u, "bracket_name", None),
            }
        )
    return members


@ai_brackets.route("/ai-brackets/scoreboard")
@check_account_visibility
@check_score_visibility
def scoreboard_list():
    scores = all_scores()
    standings = scores[_requested_board()]["standings"]
    teams = get_config("user_mode") == TEAMS_MODE
    # Members with their score in the standing's bracket (on "all", a team that
    # plays both brackets lists its members once with each bracket's scores).
    members = {}
    if teams:
        for b in BRACKETS:
            ids = [s["account_id"] for s in standings if s["ai_bracket"] == b]
            if ids:
                members[b] = _members(ids, scores[b]["user_scores"])
    account_type = get_mode_as_word()

    data = []
    for pos, s in enumerate(standings, start=1):
        entry = dict(
            s,
            pos=pos,
            account_url=generate_account_url(account_id=s["account_id"]),
            account_type=account_type,
        )
        if teams:
            entry["members"] = members.get(s["ai_bracket"], {}).get(s["account_id"], [])
        data.append(entry)
    return {"success": True, "data": data}


@ai_brackets.route("/ai-brackets/scoreboard/top/<int:count>")
@check_account_visibility
@check_score_visibility
def scoreboard_top(count):
    scores = all_scores()
    standings = scores[_requested_board()]["standings"]
    bracket_id = request.args.get("bracket_id", type=int)
    if bracket_id is not None:
        standings = [s for s in standings if s["bracket_id"] == bracket_id]

    data = {}
    for pos, s in enumerate(standings[: max(1, min(count, TOP_MAX))], start=1):
        data[pos] = {
            "id": s["account_id"],
            "account_url": generate_account_url(account_id=s["account_id"]),
            "name": s["name"],
            "score": s["score"],
            "bracket_id": s["bracket_id"],
            "bracket_name": s["bracket_name"],
            "ai_bracket": s["ai_bracket"],
            "solves": scores[s["ai_bracket"]]["rows"].get(s["account_id"], []),
        }
    return {"success": True, "data": data}


def _event_state():
    """Where the event is, for the podium page: "sealed" once the scoreboard
    freeze has passed (the standings players see are no longer the result),
    "running" before the end time, else "final"."""
    now = time.time()
    freeze = get_config("freeze")
    end = get_config("end")
    if freeze and now >= int(freeze):
        return "sealed"
    if end and now < int(end):
        return "running"
    return "final"


@ai_brackets.route("/ai-brackets/winners")
@check_account_visibility
@check_score_visibility
def winners():
    """The top WINNERS_TOP of each bracket, for the podium page
    (platform/pages/podium.md). The places are only in the answer when they
    are the result ("final"): while the event runs or the scoreboard is frozen
    it carries the state alone, so the page can be open to everyone before the
    prize-giving. An admin gets them at any time with ?reveal=1, counted
    without the freeze: the presenter reveals the winners on the big screen
    first and lifts the freeze afterwards."""
    state = _event_state()
    presenter = bool(is_admin())
    data = {"state": state, "presenter": presenter}
    if state == "final" or (presenter and request.args.get("reveal") == "1"):
        scores = _compute(frozen=False) if state == "sealed" else all_scores()
        teams = get_config("user_mode") == TEAMS_MODE
        for b in BRACKETS:
            top = scores[b]["standings"][:WINNERS_TOP]
            members = (
                _members([s["account_id"] for s in top], scores[b]["user_scores"])
                if teams
                else {}
            )
            data[b] = [
                {
                    "pos": pos,
                    "name": s["name"],
                    "score": s["score"],
                    "account_url": generate_account_url(account_id=s["account_id"]),
                    "members": [
                        {"id": m["id"], "name": m["name"]}
                        for m in members.get(s["account_id"], [])
                    ],
                }
                for pos, s in enumerate(top, start=1)
            ]
    return {"success": True, "data": data}


def _account_summary(account_id):
    scores = all_scores()
    data = {}
    for bracket in BRACKETS:
        summary = {"score": 0, "place": None}
        for pos, s in enumerate(scores[bracket]["standings"], start=1):
            if s["account_id"] == account_id:
                summary = {"score": s["score"], "place": ordinalize(pos)}
                break
        data[bracket] = summary
    return {"success": True, "data": data}


@ai_brackets.route("/ai-brackets/account/me")
@check_score_visibility
def account_me():
    if not authed():
        abort(403)
    account_id = get_current_user().account_id
    if account_id is None:
        abort(404)
    return _account_summary(account_id)


@ai_brackets.route("/ai-brackets/account/<int:account_id>")
@check_account_visibility
@check_score_visibility
def account_public(account_id):
    # Hidden and banned accounts are never in the standings, so they read as
    # 0 points and no place: nothing about them leaks.
    return _account_summary(account_id)
