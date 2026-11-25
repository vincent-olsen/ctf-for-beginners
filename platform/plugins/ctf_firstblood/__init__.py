"""First blood: who solved each challenge first, for the theme's show.

The first account to solve a challenge draws first blood. The theme
(platform/theme/first-blood.js) asks this plugin every few seconds and plays a
full-screen moment on the Scoreboard page (with sound and a voice, when the
viewer has turned them on) and a small banner on every other page:

    GET /first-blood/feed
        {"rev": "...", "events": [{"id", "ts", "age", "challenge_id", "challenge",
          "category", "value", "bracket", "account_id", "account"}, ...]}

- An event is a challenge's first solve by a visible account, oldest first. A
  hidden or banned account (the admin is hidden) never draws first blood: its
  solve is skipped and the first visible account after it gets the moment.
- Only events of the last quarter of an hour are listed; the theme announces
  nothing older, so the answer stays small however long the event runs.
- "age" is the seconds since the solve by this server's clock, so a viewer's
  clock doesn't matter. "account" is the team in teams mode, else the user.
  "bracket" is "ai" for an `ai-` category, else "normal" (docs/ai-mode.md).
- "rev" changes whenever a solve or an award is added or removed. The Scoreboard
  page fetches its table and graph again when it does, so the board on the big
  screen follows within seconds instead of CTFd's five minutes.
- Whoever may see the scoreboard may see the feed (the same two visibility
  settings), which always includes the admin: an admin account on the projector
  gets the show without playing. After the freeze nothing new is listed and
  "rev" stands still, for the admin too, since the projector is public.

The implementation is in feed.py, which is imported only in load(): CTFd
doesn't catch a plugin's errors, so if it doesn't fit this CTFd version the
plugin switches itself off instead of stopping CTFd from starting. The theme
then announces nothing.

ctf.sh copies this folder into CTFd/plugins/ while the theme is linked (unless
CTF_AI_MODE=off) and no preview runs, and removes it otherwise.
"""


def load(app):
    try:
        from .feed import first_blood

        app.register_blueprint(first_blood)
    except Exception as e:  # noqa: BLE001 - never take CTFd down with us
        print(" * ctf_firstblood disabled, first blood is not announced: %r" % (e,))
