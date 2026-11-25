"""Sibling links between the brackets (see __init__.py).

Each AI challenge's metadata.yml `builds_on` names the normal challenges it
levels up. platform/ctfd_admin.py keeps the whole map in one CTFd config value,
{"<AI challenge name>": ["<normal name>", ...]}, which players never see. This
endpoint turns it into challenge ids, keeping only pairs where both challenges
are visible, so a hidden challenge's name doesn't leak and the theme needs no
further filtering.
"""

import json

from flask import Blueprint

from CTFd.models import Challenges
from CTFd.utils import get_config
from CTFd.utils.decorators import during_ctf_time_only, require_verified_emails
from CTFd.utils.decorators.visibility import check_challenge_visibility

from .scoring import bracket_of

SIBLINGS_CONFIG = "ai_brackets_siblings"  # same key as platform/ctfd_admin.py
DIFFICULTY_CONFIG = "ai_brackets_difficulty"  # {"<AI challenge name>": 1..5}

siblings = Blueprint("ai_brackets_siblings", __name__)


def _sibling_map():
    try:
        raw = json.loads(get_config(SIBLINGS_CONFIG) or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    names = set(raw)
    for bases in raw.values():
        if isinstance(bases, list):
            names.update(str(b) for b in bases)
    rows = Challenges.query.filter(Challenges.name.in_(names), Challenges.state == "visible").all()
    by_name = {}
    for c in rows:
        by_name.setdefault(c.name, c)

    data = {}
    for ai_name, bases in raw.items():
        ai = by_name.get(ai_name)
        if ai is None or bracket_of(ai.category) != "ai" or not isinstance(bases, list):
            continue
        ids = []
        for name in bases:
            base = by_name.get(str(name))
            if base is not None and bracket_of(base.category) == "normal" and base.id not in ids:
                ids.append(base.id)
        data[str(ai.id)] = ids
    return data


def _difficulty_map():
    """{"<visible AI challenge id>": 1..5} from the config the sync writes.

    Keyed by id (like the sibling map) so the theme can match it to a challenge
    without a name round-trip, and limited to visible AI-modus challenges."""
    try:
        raw = json.loads(get_config(DIFFICULTY_CONFIG) or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    rows = Challenges.query.filter(Challenges.name.in_(list(raw)), Challenges.state == "visible").all()
    data = {}
    for c in rows:
        if bracket_of(c.category) != "ai":
            continue
        try:
            n = int(raw.get(c.name))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 5:
            data[str(c.id)] = n
    return data


@siblings.route("/ai-brackets/siblings")
@check_challenge_visibility
@during_ctf_time_only
@require_verified_emails
def sibling_list():
    return {"success": True, "data": _sibling_map(), "difficulty": _difficulty_map()}
