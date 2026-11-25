"""AI-modus brackets: one scoreboard per bracket, in one CTFd.

The two brackets are split by challenge category (see docs/ai-mode.md): an
`ai-` prefix is the AI-modus bracket, anything else the normal bracket. Stock
CTFd has a single score per account, so this plugin scores every account twice,
once per bracket, with the same rules as CTFd's own get_standings: solves and
awards of value 0 are skipped, frozen at the freeze time, hidden and banned
accounts left out, and ties broken by who got there first. A team whose members
play different brackets gets a score, and a place, in each.

Awards count in the bracket of their category, except hint unlocks (category
"hints", name "Hint <id>"), which cost points in the bracket of the hint's
challenge. Hint costs alone don't put an account on a bracket's scoreboard.

The stock scoreboard API is left untouched. The theme (platform/theme/) points
the scoreboard page at these endpoints for the board its All | Classic |
AI-MODUS tabs pick, adds the per-bracket scores to the team and user pages, and
links each AI challenge to the normal ones it levels up:

    GET /ai-brackets/scoreboard?bracket=normal|ai|all            like /api/v1/scoreboard
    GET /ai-brackets/scoreboard/top/<n>?bracket=normal|ai|all    like /api/v1/scoreboard/top/<n>
    GET /ai-brackets/account/<id>|me                             {normal: {score, place}, ai: {...}}
    GET /ai-brackets/winners[?reveal=1]                          the podium page: state + each bracket's top 3
    GET /ai-brackets/siblings                                    {"<AI challenge id>": [<normal id>, ...]}

bracket=all ranks every account once per bracket it plays in, each with that
bracket's score: a team that plays both is listed twice, never with the two
added together (that is the stock scoreboard). Every scoreboard entry says
which bracket it is in, as ai_bracket ("normal" or "ai"); the theme puts the
bracket after the name on the All board.

The sibling map comes from each AI challenge's metadata.yml `builds_on`, which
platform/ctfd_admin.py stores in a CTFd config value (siblings.py), so it never
shows up as a tag or anywhere else players can see.

The implementation is in scoring.py and siblings.py, which are imported only in
load(): CTFd doesn't catch a plugin's errors, so if they don't fit this CTFd
version the plugin switches itself off instead of stopping CTFd from starting.
The theme then shows the stock, combined scoreboard and no sibling links.

ctf.sh copies this folder into CTFd/plugins/ on `./ctf.sh up` and removes it
again with CTF_AI_MODE=off.
"""


def load(app):
    try:
        from .scoring import ai_brackets

        app.register_blueprint(ai_brackets)
    except Exception as e:  # noqa: BLE001 - never take CTFd down with us
        print(" * ai_brackets disabled, per-bracket scoreboards are off: %r" % (e,))
        return
    try:
        from .siblings import siblings

        app.register_blueprint(siblings)
    except Exception as e:  # noqa: BLE001
        print(" * ai_brackets: sibling links are off: %r" % (e,))
