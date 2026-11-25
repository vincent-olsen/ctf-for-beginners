"""The theme's files: platform/theme/*.css and *.js at /ctf-theme/<file>.

platform/ctfd_admin.py (inject_ai_theme) writes a <link> or <script src> per file
into CTFd's theme_header and theme_footer, each URL with ?v=<the file's hash>.
Inlined, the files would outgrow the 64 KB a config value holds in MariaDB.
platform/ctfd.yml mounts platform/theme read-only at /opt/ctf-theme; only the
.css and .js files at its top level are served, and a browser may keep each
version for a day, since a changed file gets a new URL on the next up.
hosted-fx.css/.js are not linked into CTFd: the hosted AI challenge pages load
them (the AI Slop-o-meter's levels), without a hash, so they keep 5 minutes.
The same goes for first-blood.mp3, the voice first-blood.js plays: the one file
that is neither, also fetched without a hash.

ctf.sh copies this folder into CTFd/plugins/ while the theme is linked (unless
CTF_AI_MODE=off, and always in a preview) and removes it otherwise. Without it the
pages load in CTFd's own look.
"""

import os

THEME_DIR = os.environ.get("CTF_THEME_DIR", "/opt/ctf-theme")  # as in platform/ctfd_admin.py
MAX_AGE = 86400
HOSTED_MAX_AGE = 300  # hosted-fx.css/.js: the AI Slop-o-meter's kit for the hosted AI challenges
SOUNDS = ("first-blood.mp3",)  # the sounds the theme's scripts fetch themselves


def load(app):
    from flask import abort, send_from_directory

    from CTFd.plugins import bypass_csrf_protection

    # Like CTFd's own theme files: no CSRF check, which would also start a session.
    @bypass_csrf_protection
    def theme_file(name):
        if not name.endswith((".css", ".js")) and name not in SOUNDS:
            abort(404)
        # The hosted AI challenge pages load hosted-fx.* from here without a ?v=
        # hash (they can't know it), so a changed kit must reach them sooner.
        # A sound has no hash either.
        unhashed = name.startswith("hosted-fx.") or name in SOUNDS
        max_age = HOSTED_MAX_AGE if unhashed else MAX_AGE
        return send_from_directory(THEME_DIR, name, max_age=max_age)

    app.add_url_rule("/ctf-theme/<name>", endpoint="ctf_theme.file", view_func=theme_file)
