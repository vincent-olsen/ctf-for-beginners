"""Configure a running CTFd instance. Runs inside the ctfd container, piped in by ctf.sh:

    docker compose exec -T ctfd python - <command> [options] < platform/ctfd_admin.py

Commands:
    count       print "challenges=<n>" (0 means a new CTFd: nothing imported or set up
                yet), after the last import's error if it failed
    configure   apply settings, and set up a CTFd that has never been set up (a new CTF
                without an export); see --help
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys

from CTFd import create_app
from CTFd.cache import (cache, clear_all_user_sessions, clear_challenges, clear_config, clear_pages,
                        clear_standings)
from CTFd.models import (
    Awards,
    Brackets,
    ChallengeFiles,
    Challenges,
    FieldEntries,
    Fields,
    Files,
    Flags,
    Hints,
    Pages,
    Ratings,
    Solves,
    Submissions,
    Tags,
    Teams,
    Tokens,
    Tracking,
    Unlocks,
    Users,
    db,
)
from CTFd.utils import get_config, set_config
from flask import current_app


def count(_args):
    # CTFd keeps a failed import's error cached for a week; ctf.sh shows it and parses
    # only the "challenges=" line.
    error = cache.get("import_error")
    if error:
        print(f"last import failed: {error}")
    print(f"challenges={Challenges.query.count()}")


def clear_event_dates():
    for key in ("start", "end", "freeze"):
        set_config(key, None)
    print("cleared start, end and freeze time")


# The event's times and team size from ctf.sh up --event-start/--event-end/
# --event-freeze/--team-size. Each is None when not given (CTFd's own stays, so a
# change in the admin panel survives an up) and "" to clear it. A time is ISO 8601
# with its UTC offset, which ctf.sh checked; CTFd keeps it as a Unix timestamp.
EVENT_TIMES = (("start", "event_start"), ("end", "event_end"), ("freeze", "event_freeze"))


def _timestamp(text):
    from datetime import datetime

    moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if moment.tzinfo is None:
        sys.exit(f"error: the time {text} has no UTC offset")
    return int(moment.timestamp())


def set_event_settings(args):
    stamps = {}
    for key, attr in EVENT_TIMES:
        value = getattr(args, attr)
        if value is None:
            continue
        if not value.strip():
            set_config(key, None)
            print(f"{key} time cleared")
            continue
        stamps[key] = _timestamp(value)
        set_config(key, str(stamps[key]))
        print(f"{key} time set to {value}")
    start = stamps.get("start") or _int_config("start")
    end = stamps.get("end") or _int_config("end")
    if start and end and end <= start:
        print("warning: the end time is not after the start time; CTFd will treat the event as over", file=sys.stderr)
    if args.team_size is not None:
        size = args.team_size.strip()
        set_config("team_size", str(int(size)) if size else None)
        print(f"team size set to {size}" if size else "team size cleared (no limit)")


def _int_config(key):
    try:
        return int(get_config(key) or 0)
    except (TypeError, ValueError):
        return 0


def set_admin_password(name, password):
    admin = Users.query.filter_by(name=name, type="admin").first()
    if admin is None:
        admin = Users.query.filter_by(type="admin").order_by(Users.id).first()
    if admin is None:
        sys.exit("no admin user found in the imported backup")
    admin.password = password
    db.session.commit()
    print(f"admin password set for user '{admin.name}'")
    return admin.name


def remove_participants():
    """Keep challenges, pages and admins; drop players, teams and everything they did."""
    admin_ids = [u.id for u in Users.query.filter_by(type="admin").all()]
    db.session.query(Users).update({Users.team_id: None}, synchronize_session=False)
    for model in (Solves, Submissions, Awards, Unlocks, Tracking, FieldEntries, Ratings):
        model.query.delete(synchronize_session=False)
    Tokens.query.filter(Tokens.user_id.notin_(admin_ids)).delete(synchronize_session=False)
    Teams.query.delete(synchronize_session=False)
    removed = Users.query.filter(Users.type != "admin").delete(synchronize_session=False)
    db.session.commit()
    print(f"removed {removed} players, all teams, submissions and solves")


# A new CTF, without an export ------------------------------------------------------
# When ./ctf.sh up has no CTFd export to import, CTFd starts out never set up, and
# configure does what CTFd's setup page would, with the settings the earlier events'
# exports had: teams mode; the challenges, the scoreboard and the accounts for
# logged-in players only; open registration (a --registration-code closes it); no
# email verification. The board lists the categories crypto, misc, web, forensics,
# pwn (an ai-* category next to its classic one) and each category by points. The
# admin account is CTF_ADMIN_NAME with CTF_ADMIN_PASSWORD. The challenges and pages
# then come from the repo, as on every run.
SETUP_SETTINGS = {
    "user_mode": "teams",
    "ctf_theme": "core",
    "challenge_visibility": "private",
    "registration_visibility": "public",
    "score_visibility": "private",
    "account_visibility": "private",
    "verify_emails": "0",
    "social_shares": "0",
    "team_creation": "1",
    "team_disbanding": "inactive_only",
    "name_changes": "1",
    "view_after_ctf": "1",
    "paused": "0",
    "html_sanitization": "0",
}
# CTFd's core theme sorts the board with these (Admin -> Config -> Theme).
SETUP_THEME_SETTINGS = {
    "challenge_category_order": (
        "function compare(a, b) {\n"
        "  const order = {crypto: 1, misc: 2, web: 3, forensics: 4, pwn: 5};\n"
        "  const rank = (c) => order[String(c).replace(/^ai-/, \"\")] || 99;\n"
        "  return rank(a) - rank(b) || (a < b ? -1 : a > b ? 1 : 0);\n"
        "}\n"),
    "challenge_order": "function compare(a, b) {\n  return a.value - b.value;\n}\n",
}


def initial_setup():
    """CTFd's setup, on a CTFd that has none; does nothing once CTFd is set up (an
    imported export brings its own). Returns whether it set CTFd up."""
    if get_config("setup"):
        return False
    from CTFd.models import Admins

    name = os.environ.get("CTF_ADMIN_NAME", "admin")
    password = os.environ.get("CTF_ADMIN_PASSWORD")
    if not password:
        sys.exit("a new CTFd needs its admin password (CTF_ADMIN_PASSWORD)")
    print("new CTF: setting CTFd up from the repo (no export imported)")
    set_config("ctf_name", (os.environ.get("CTF_BRAND_NAME") or "").strip() or "CTF")
    for key, value in SETUP_SETTINGS.items():
        set_config(key, value)
    raw = get_config("theme_settings") or "{}"
    try:
        theme = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except ValueError:
        theme = {}
    for key, value in SETUP_THEME_SETTINGS.items():
        theme.setdefault(key, value)
    set_config("theme_settings", json.dumps(theme, indent=2))
    if Users.query.filter_by(type="admin").first() is None:
        db.session.add(Admins(name=name, email=f"{name}@example.com", password=password,
                              type="admin", hidden=True, verified=True))
        db.session.commit()
        print(f"admin user '{name}' created")
    set_config("setup", "1")
    return True


def remove_backup_brackets_and_fields():
    """After an import: drop the backup's own CTFd brackets and custom registration
    fields. They belong to the event the backup came from (team sizes, skill levels,
    an employer or school field): a bracket adds a required choice to
    the registration and team forms and a tab to the scoreboard, a field a box to the
    registration form. This event's two lanes are the challenge categories, scored by
    the ai_brackets plugin, and have nothing to do with CTFd's brackets. Ones added in
    Admin -> Config afterwards stay until the next import."""
    brackets = Brackets.query.count()
    if brackets:
        for model in (Users, Teams):
            model.query.filter(model.bracket_id.isnot(None)).update(
                {model.bracket_id: None}, synchronize_session=False)
        Brackets.query.delete(synchronize_session=False)
    fields = Fields.query.count()
    if fields:
        FieldEntries.query.delete(synchronize_session=False)
        Fields.query.delete(synchronize_session=False)
    db.session.commit()
    if brackets or fields:
        print(f"removed the backup's {brackets} brackets and {fields} custom registration fields")


def apply_connections(spec):
    """spec: lines of "<challenge name>\t<connection info>"; "@hidden" hides the challenge."""
    for line in spec.splitlines():
        if not line.strip():
            continue
        name, _, value = line.partition("\t")
        challenges = Challenges.query.filter_by(name=name).all()
        if not challenges:
            print(f"  skip  {name}: no challenge with that name")
            continue
        for challenge in challenges:
            if value == "@hidden":
                challenge.state = "hidden"
                challenge.connection_info = None
                shown = "(hidden: no container runs for it)"
            else:
                challenge.connection_info = value
                shown = value
        print(f"  {name:<22} {shown}")
    db.session.commit()


# Languages ----------------------------------------------------------------------
# The event is in Norwegian and English: players switch with NO | EN in the
# navbar (platform/theme/i18n.js), and the default is ctf.sh up --lang. See
# docs/language.md. In metadata.yml, `message` and `hints` are English and
# `message_no` and `hints_no` Norwegian (the same hints, in the same order; the
# cost comes from `hints`). With the theme linked, a text in both languages
# becomes a block per language, <div class="ctf-lang" lang="no">, and
# ai-mode.css shows the one the player picked. Without the theme
# (CTF_AI_MODE=off) there is no switch: CTFd gets the default language's text
# only, and translates its own pages itself (default_locale).
LANGUAGES = ("no", "en")  # as in platform/theme/i18n.strings.js
DEFAULT_LANGUAGE = "en"
SOURCE_LANGUAGE = "en"  # the plain fields (`message`, `hints`), and what CTFd renders under the theme


def _field(name, code):
    return name if code == SOURCE_LANGUAGE else f"{name}_{code}"


def _in_languages(texts, only=None):
    """One description or hint from its text per language ({"no": ..., "en": ...}).
    only: a language code, when there is no switch (no theme): that language's
    text, else English's. Otherwise a block per language, or the text itself
    when it is in one language only."""
    present = [(code, str(texts.get(code) or "").strip()) for code in LANGUAGES]
    present = [(code, text) for code, text in present if text]
    if not present:
        return ""
    if only:
        found = dict(present)
        return found.get(only) or found.get(SOURCE_LANGUAGE) or present[0][1]
    if len(present) == 1:
        return present[0][1]
    # The blank lines let Markdown inside each block render as Markdown. A code
    # fence left open would swallow the </div> and the next language's block.
    return "\n".join(f'<div class="ctf-lang" lang="{code}">\n\n{_close_fences(text)}\n\n</div>' for code, text in present)


def _close_fences(text):
    """text with a ``` fence it leaves open closed at its end."""
    fences = sum(1 for line in text.split("\n") if line.lstrip().startswith("```"))
    return text + "\n```" if fences % 2 else text


def _keep_language(html, code):
    """html without its blocks in other languages: an element with class
    "ctf-lang" whose lang isn't code goes, with everything in it. For a page that
    keeps both languages in one file (the index), when there is no switch."""
    from html.parser import HTMLParser

    cuts = []  # (start, end) offsets in html

    class Blocks(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.starts = [0]
            # getpos() counts lines by "\n" only; splitlines() would also break
            # on \r, \u2028 and the like, and shift every offset after one.
            for line in html.split("\n"):
                self.starts.append(self.starts[-1] + len(line) + 1)
            self.cut = None  # [tag, depth, start] of the block being cut

        def here(self):
            line, col = self.getpos()
            return self.starts[line - 1] + col

        def handle_starttag(self, tag, attrs):
            if self.cut:
                if tag == self.cut[0]:
                    self.cut[1] += 1
                return
            a = dict(attrs)
            if "ctf-lang" in (a.get("class") or "").split() and a.get("lang") and a.get("lang") != code:
                self.cut = [tag, 1, self.here()]

        def handle_endtag(self, tag):
            if self.cut and tag == self.cut[0]:
                self.cut[1] -= 1
                if self.cut[1] == 0:
                    end = html.index(">", self.here()) + 1
                    cuts.append((self.cut[2], end))
                    self.cut = None

    Blocks().feed(html)
    for start, end in reversed(cuts):
        html = html[:start] + html[end:]
    return html


def _description(meta, only=None):
    return _in_languages({code: meta.get(_field("message", code)) for code in LANGUAGES}, only)


def _localized_hints(meta, chname, cdir, only=None):
    """metadata `hints` with each one's text in every language that has it, and
    the files they name ({{file:...}}) after it."""
    hints = _hints(meta.get("hints"))
    for code in LANGUAGES:
        if code == SOURCE_LANGUAGE:
            continue
        key = _field("hints", code)
        other = _hints(meta.get(key))
        if other and len(other) != len(hints):
            print(f"  warning: {chname} has {len(hints)} hints but {len(other)} {key}; they are matched in order")
        for hint, translated in zip(hints, other):
            hint.setdefault("texts", {SOURCE_LANGUAGE: hint["content"]})[code] = translated["content"]
    for hint in hints:
        texts = hint.pop("texts", {SOURCE_LANGUAGE: hint["content"]})
        paths = []
        for code, text in texts.items():
            paths += [p for p in HINT_FILE.findall(text) if p not in paths]
            texts[code] = HINT_FILE.sub("", text)
        files = [block for block in (_hint_file(cdir, path, chname) for path in paths) if block]
        hint["content"] = "\n\n".join([_in_languages(texts, only)] + files).strip()
    return hints


# A hint that hands over a file (the source, as a paid hint of a black-box
# challenge) names it as {{file:challenge/app.py}}, relative to the challenge
# folder; ctf.sh stages the files named so. The sync puts the file's text, as of
# this `up`, after the hint's text in a fenced code block, once for every
# language: code reads the same in both, and the repo keeps one copy of it.
HINT_FILE = re.compile(r"\{\{\s*file:\s*([^}\s]+)\s*\}\}")
FENCE_LANGUAGES = {".c": "c", ".go": "go", ".js": "javascript", ".py": "python", ".sh": "bash"}


def _hint_file(cdir, path, chname):
    """The file at path (relative to the challenge folder cdir) as a fenced code
    block, or "" with a warning when it is missing or outside the folder."""
    root = os.path.realpath(cdir)
    full = os.path.realpath(os.path.join(root, path))
    if not full.startswith(root + os.sep) or not os.path.isfile(full):
        print(f"  warning: {chname}'s hint file {path} is missing or outside its folder; the hint goes without it")
        return ""
    with open(full, encoding="utf-8") as fh:
        text = fh.read().rstrip("\n")
    # A fence longer than any run of backticks in the file, which would close it.
    fence = "`" * max([3] + [len(run) + 1 for run in re.findall(r"`{3,}", text)])
    return f"{fence}{FENCE_LANGUAGES.get(os.path.splitext(path)[1], '')}\n{text}\n{fence}"


def set_default_locale(locale):
    """CTFd's language for its own pages, for a player who hasn't picked one."""
    if get_config("default_locale") != locale:
        set_config("default_locale", locale)
        print(f"default_locale set to {locale}")


def clear_user_languages():
    """Forget the Language players picked in CTFd's Settings. CTFd prefers it to
    default_locale, but the theme needs CTFd's pages in English underneath, and
    hides that field (i18n.js drops the matching cookie)."""
    if not hasattr(Users, "language"):
        return
    cleared = Users.query.filter(Users.language.isnot(None), Users.language != "").update(
        {Users.language: None}, synchronize_session=False)
    db.session.commit()
    if cleared:
        clear_all_user_sessions()
        print(f"language preference cleared for {cleared} players (the theme's switch replaces it)")


# AI-modus challenge sync ------------------------------------------------------
# Create/update the AI-modus challenges in CTFd straight from the repo, so no
# manual admin-panel mirroring is needed. ctf.sh copies every challenge's
# metadata.yml and distfiles/ into the container and passes
# CTF_CHALLENGES_DIR; a challenge counts as AI-modus iff its metadata `category`
# starts with "ai-".
# Adding a new AI challenge later needs nothing here: just create the folder with
# `category: ai-...` in its metadata.yml.
def _parse_metadata(text):
    """Parse a simple metadata.yml. Uses PyYAML when present (CTFd doesn't ship
    it), else a small top-level parser: "key: value" scalars, plus lists written
    either flow style ("key: [a, b]", returned as that string for _builds_on,
    and allowed to run over several lines until its "]") or block style ("key:"
    followed by indented "- item" lines, returned as a list), and literal block
    scalars ("key: |" or "key: |-" followed by indented lines, which keep their
    line breaks: multi-line Markdown messages), also as a list item ("- |", a
    multi-line hint). An unquoted " # comment" at the end of a value or item is
    dropped, as YAML does."""
    try:
        import yaml  # not a guaranteed CTFd dependency, so it's optional

        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    data = {}
    key = None  # the last top-level key, which "- item" lines under it belong to
    flow = None  # a flow list still waiting for its closing "]"
    # A literal block scalar being read: (chomping indicator, its lines, the
    # indent of the line that opened it, whether it is a list item). It takes
    # every line indented further than that one, and blank lines.
    block = None

    def end_block():
        value = _literal_block(block[0], block[1])
        if block[3]:
            data[key].append(value)
        else:
            data[key] = value

    for line in text.splitlines():
        stripped = line.strip()
        if block is not None:
            if not stripped or len(line) - len(line.lstrip()) > block[2]:
                block[1].append(line)
                continue
            end_block()
            block = None
        if flow is not None:
            flow += " " + _strip_comment(stripped)
            if "]" in flow:
                data[key], flow = flow, None
            continue
        if not stripped or stripped[0] == "#":
            continue
        is_item = stripped == "-" or stripped.startswith("- ")
        if is_item and key is not None and (data[key] == "" or isinstance(data[key], list)):
            if not isinstance(data[key], list):
                data[key] = []
            item = _strip_comment(stripped[1:].strip())
            if item in ("|", "|-"):
                block = (item, [], len(line) - len(line.lstrip()), True)
                continue
            data[key].append(_unquote(item))
            continue
        if line[0] in " \t":
            continue  # other nested YAML is not needed by the sync
        if ":" not in line:
            key = None
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = _strip_comment(val.strip())
        if val.startswith("[") and "]" not in val:
            flow = val
            continue
        if val in ("|", "|-"):
            block = (val, [], 0, False)
            continue
        data[key] = _unquote(val)
    if block is not None:
        end_block()
    if flow is not None:
        data[key] = flow  # unterminated: keep what there is
    return data


def _literal_block(chomp, lines):
    """The value of a literal block scalar: its lines without their common indent,
    ending in one newline for "|" and none for "|-" (YAML's clip and strip)."""
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
    text = "\n".join(line[indent:] for line in lines)
    return text + "\n" if chomp == "|" else text


def _strip_comment(val):
    """Drop a trailing " # comment" that isn't inside a quoted scalar."""
    start = 0
    if val and val[0] in "\"'":
        quote, i = val[0], 1
        while i < len(val):
            if quote == '"' and val[i] == "\\":
                i += 2
                continue
            if val[i] == quote:
                if quote == "'" and val[i + 1:i + 2] == "'":
                    i += 2  # '' is an escaped quote
                    continue
                break
            i += 1
        start = i + 1
    if val.startswith("#"):
        return ""
    cut = val.find(" #", start)
    cut_tab = val.find("\t#", start)
    cut = min(c for c in (cut, cut_tab, len(val)) if c != -1)
    return val[:cut].rstrip()


def _unquote(val):
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        quote, val = val[0], val[1:-1]
        val = val.replace('\\"', '"').replace("\\\\", "\\") if quote == '"' else val.replace("''", "'")
    return val


def _sha1_of(path):
    h = hashlib.sha1()  # nosec - file integrity, not security
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _add_static_flag(challenge_id, content):
    """A static, case-insensitive flag. Inserted as a row: CTFd maps no class to the
    "static" flag type, so a Flags object makes SQLAlchemy warn as it is saved."""
    db.session.execute(Flags.__table__.insert().values(
        challenge_id=challenge_id, type="static", content=content, data="case_insensitive"))


def _sync_flag(challenge, flag, exact=True):
    """exact (a new challenge, or after an import): make the challenge's flags exactly
    one static, case-insensitive flag. Otherwise add the flag when it is missing and
    keep the others, such as a variant an admin accepted during the event; every
    static flag is made case-insensitive, as for the normal challenges."""
    if exact:
        Flags.query.filter_by(challenge_id=challenge.id).delete(synchronize_session=False)
        _add_static_flag(challenge.id, flag)
        db.session.commit()
        return
    statics = Flags.query.filter_by(challenge_id=challenge.id, type="static")
    # A bulk UPDATE, as in sync_normal_challenges (loaded Flags rows warn on flush).
    statics.filter(db.or_(Flags.data.is_(None), Flags.data != "case_insensitive")).update(
        {Flags.data: "case_insensitive"}, synchronize_session=False)
    if flag.lower() not in {row.content.strip().lower() for row in statics}:
        _add_static_flag(challenge.id, flag)
    db.session.commit()


def _sync_files(challenge, distdir):
    """Attach distfiles/ (skip .keep); replace a file only when its bytes changed,
    and prune attachments whose distfile was removed or renamed in the repo."""
    from CTFd.utils.uploads import delete_file, upload_file
    from werkzeug.datastructures import FileStorage

    attached = {os.path.basename(cf.location): cf for cf in ChallengeFiles.query.filter_by(challenge_id=challenge.id)}
    if not os.path.isdir(distdir):
        return
    wanted = set()
    for name in sorted(os.listdir(distdir)):
        path = os.path.join(distdir, name)
        if name == ".keep" or not os.path.isfile(path):
            continue
        wanted.add(name)
        existing = attached.get(name)
        if existing is not None:
            if existing.sha1sum == _sha1_of(path):
                continue  # unchanged
            delete_file(existing.id)  # bytes changed -> replace
        with open(path, "rb") as fh:
            upload_file(file=FileStorage(stream=fh, filename=name), challenge_id=challenge.id, type="challenge")
    # Prune orphans so the sync is idempotent for deletions: a distfile that was
    # renamed or removed must not linger as a stale download on the challenge.
    for name, cf in attached.items():
        if name not in wanted:
            delete_file(cf.id)


def _stored_sha1(location):
    """The SHA-1 of an uploaded file as CTFd stores it, or None when it can't be read."""
    from CTFd.utils.uploads import get_uploader

    h = hashlib.sha1()  # nosec - file integrity, not security
    try:
        with get_uploader().open(location) as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except Exception:  # noqa: BLE001 - missing or unreadable: treated as changed
        return None
    return h.hexdigest()


def _update_files(challenge, distdir):
    """A normal challenge's attachments come from the imported backup. Replace each
    one that distfiles/ has a file of the same name for, with other bytes: a fix to a
    distfile in the repo (a rebuilt binary, a corrected script) then reaches the
    players' download, like the container it was rebuilt for. Nothing is added or
    removed: an attachment under another name than the repo's, and a distfile the
    backup doesn't attach, stay as they are. Returns the names replaced."""
    from CTFd.utils.uploads import delete_file, upload_file
    from werkzeug.datastructures import FileStorage

    replaced = []
    if not os.path.isdir(distdir):
        return replaced
    for attached in ChallengeFiles.query.filter_by(challenge_id=challenge.id).order_by(ChallengeFiles.id).all():
        name = os.path.basename(attached.location)
        path = os.path.join(distdir, name)
        if name == ".keep" or not os.path.isfile(path):
            continue
        # Older exports lack the checksum of some files; hash what CTFd stores then.
        if (attached.sha1sum or _stored_sha1(attached.location)) == _sha1_of(path):
            continue
        old_id = attached.id
        try:
            with open(path, "rb") as fh:
                upload_file(file=FileStorage(stream=fh, filename=name), challenge_id=challenge.id, type="challenge")
            delete_file(old_id)  # after the upload, so a failed one leaves the old file
        except Exception as exc:  # noqa: BLE001 - a download that stays as it was must not stop an up
            db.session.rollback()
            print(f"  warning: could not replace {challenge.name}'s file {name}: {exc}", file=sys.stderr)
            continue
        replaced.append(name)
    return replaced


def _hints(value):
    """Parse metadata `hints` into [{"content", "cost"}], in order.

    Accepts a YAML block or flow list of "COST | text" strings — which the
    fallback parser (no PyYAML) reads identically, since each hint is its own
    list item, so commas in the text are safe — or a list of {content, cost}
    mappings. A blank cost (" | text") or none at all (plain text, which may
    hold a "|" of its own, like a shell pipe) means a free hint.
    """
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    hints = []
    for item in items:
        if isinstance(item, dict):
            content = str(item.get("content", "")).strip()
            cost = item.get("cost", 0)
        else:
            prefixed = re.match(r"\s*(\d*)\s*\|(.*)\Z", str(item), re.S)
            cost, content = prefixed.groups() if prefixed else (0, str(item))
            content = content.strip()
        try:
            cost = int(str(cost).strip())
        except (TypeError, ValueError):
            cost = 0
        if content:
            hints.append({"content": content, "cost": max(0, cost)})
    return hints


def _sync_hints(challenge, hints):
    """Make the challenge's hints exactly the metadata list: update in place,
    add new ones, prune extras. Idempotent, so editing a hint's text or cost in
    metadata.yml and re-running `up` keeps CTFd in sync.

    Rows are matched to metadata hints by content first, so a hint keeps its own
    row — and with it any paid CTFd Unlocks, which are keyed by hint id. Reordering
    the list in metadata.yml therefore does not move a player's paid unlock onto a
    different hint's text, and a cost-only edit reuses the row by content. A text
    edit reuses the edited hint's row only when that pairing is unambiguous: the
    list kept its length and exactly one hint and one row are left unmatched.
    Anything else (an edit together with an insert or a removal, or several edits
    at once) gets new rows, so a paid unlock never lands on another hint's text.

    A hint dropped from metadata.yml is deleted only if nobody has unlocked it. A
    purchased one is retired instead: kept, so its buyers can still open it and its
    cost stays attributed to this challenge's own bracket, but made its own
    prerequisite, so nobody who hasn't bought it can open or buy it. Its exact
    text back in metadata.yml brings it back.

    Cheapest first: every hint gets the challenge's strictly cheaper hints as its
    prerequisites, so a player works up the ladder (nudge, then method, then the
    near-answer) and pays for each rung. Hints of the same cost don't depend on
    each other, so two independent tips at one price stay a free choice. CTFd
    itself only checks prerequisites when a hint is opened, not when it is
    bought; platform/plugins/ctf_hints refuses the purchase too.

    Costs are charged in the challenge's own bracket by the ai_brackets plugin,
    so an AI-modus hint's cost lands on the AI-modus score (see docs/ai-mode.md).
    Returns whether anything changed.
    """
    existing = Hints.query.filter_by(challenge_id=challenge.id).order_by(Hints.id).all()
    claimed = [None] * len(hints)  # metadata index -> reused existing row
    taken = set()  # ids of existing rows already claimed

    # Pass 1: exact content match (survives a reorder and a cost-only edit).
    by_content = {}
    for row in existing:
        by_content.setdefault(row.content, []).append(row)
    for i, h in enumerate(hints):
        bucket = by_content.get(h["content"])
        if bucket:
            row = bucket.pop(0)
            claimed[i] = row
            taken.add(row.id)

    # Pass 2: one hint edited in place, nothing added or removed. Retired rows (no
    # longer in metadata.yml) don't count, so they never pair with an edited hint.
    live = [row for row in existing if not _retired_hint(row)]
    unmatched = [i for i in range(len(hints)) if claimed[i] is None]
    leftovers = [row for row in live if row.id not in taken]
    if len(live) == len(hints) and len(unmatched) == 1 and len(leftovers) == 1:
        claimed[unmatched[0]] = leftovers[0]

    changed = False
    rows = []  # the row of each metadata hint, in metadata order
    for i, h in enumerate(hints):
        row = claimed[i]
        if row is None:
            row = Hints(challenge_id=challenge.id, type="standard",
                        content=h["content"], cost=h["cost"])
            db.session.add(row)
            changed = True
        elif (row.type, row.content, row.cost) != ("standard", h["content"], h["cost"]):
            row.type, row.content, row.cost = "standard", h["content"], h["cost"]
            changed = True
        rows.append(row)

    # Cheapest first. A retired hint back in metadata.yml loses its own id here
    # (a hint is never cheaper than itself), which brings it back.
    db.session.flush()  # new rows need their ids
    for row, h in zip(rows, hints):
        cheaper = sorted(other.id for other, o in zip(rows, hints) if o["cost"] < h["cost"])
        if _hint_prerequisites(row) != cheaper:
            row.requirements = {"prerequisites": cheaper} if cheaper else None
            changed = True

    kept = {row.id for row in claimed if row is not None}
    for row in existing:
        if row.id in kept:
            continue
        if Unlocks.query.filter_by(type="hints", target=row.id).first() is not None:
            # Players have paid to unlock this hint. Keep the row even though it is
            # no longer in metadata.yml: deleting it would orphan their "Hint <id>"
            # award, and the ai_brackets plugin, unable to find the hint's challenge,
            # would count the refund/cost in the wrong bracket. Retire it so nobody
            # else can open or buy it.
            if not _retired_hint(row):
                row.requirements = {"prerequisites": [row.id]}
                changed = True
                print(f"  retired purchased hint {row.id} on {challenge.name!r} "
                      "(no longer in metadata.yml; only its buyers can open it)")
            continue
        db.session.delete(row)
        changed = True
    db.session.commit()
    return changed


def _hint_prerequisites(row):
    """The ids of the hints that must be unlocked before this one, sorted."""
    requirements = row.requirements
    return sorted(requirements.get("prerequisites") or []) if isinstance(requirements, dict) else []


def _retired_hint(row):
    """A hint _sync_hints kept for its buyers only: its own sole prerequisite."""
    return _hint_prerequisites(row) == [row.id]


# `builds_on` in an AI challenge's metadata.yml names the normal-bracket
# challenges it levels up. The whole map is kept in one CTFd config value,
# {"<AI challenge name>": ["<normal name>", ...]}, which players never see; the
# ai_brackets plugin serves it (only pairs of visible challenges) at
# /ai-brackets/siblings, and the theme links the pair in the challenge windows
# (a "builds on" link in the AI one, a next-level line in the solved normal one).
SIBLINGS_CONFIG = "ai_brackets_siblings"
# Earlier versions stored the map as player-visible "builds-on:<name>" tags;
# the sync removes any that are left.
OLD_BUILDS_ON_TAG = "builds-on:"

# An AI challenge's metadata.yml `difficulty` (1-5) is the explicit threat rating
# the AI-modus theme shows on the tile/pop-up. Like the siblings map it is kept
# in one config value ({"<name>": 1..5}), off player-visible tags; the
# ai_brackets plugin serves it and the theme's threat meter prefers it over the
# points-derived default.
DIFFICULTY_CONFIG = "ai_brackets_difficulty"

# Maps each managed AI challenge's folder name (its stable identity) to the CTFd
# challenge id the sync created for it, kept in one config value. The sync matches
# on this, so renaming an AI challenge's `name` renames the same CTFd challenge in
# place instead of creating a second, still-playable copy; a folder that is removed
# has its challenge hidden on the next up. Players never see it.
MANAGED_CONFIG = "ai_brackets_managed"


def _builds_on(value):
    """A list from YAML ([a, b]) or the fallback parser (a list, or "[a, b]", "a, b")."""
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value or "").strip().strip("[]").split(",")
    return [str(i).strip().strip("\"'") for i in items if str(i).strip().strip("\"'")]


def _sync_siblings(siblings):
    removed = Tags.query.filter(Tags.value.startswith(OLD_BUILDS_ON_TAG)).delete(synchronize_session=False)
    db.session.commit()
    set_config(SIBLINGS_CONFIG, json.dumps(siblings, sort_keys=True))
    if removed:
        print(f"  removed {removed} old builds-on: tags")


def _difficulty(value):
    """An explicit threat rating 1-5 from metadata `difficulty`, else None."""
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 5 else None


def _sync_difficulty(difficulty):
    set_config(DIFFICULTY_CONFIG, json.dumps(difficulty, sort_keys=True))


def _staged_metadata(base_dir):
    """(folder name, folder path, parsed metadata) for each staged challenge."""
    for name in sorted(os.listdir(base_dir)):
        cdir = os.path.join(base_dir, name)
        meta_path = next((p for p in (os.path.join(cdir, "metadata.yml"), os.path.join(cdir, "metadata.yaml")) if os.path.isfile(p)), None)
        if meta_path:
            with open(meta_path, encoding="utf-8") as fh:
                yield name, cdir, _parse_metadata(fh.read())


def _is_ai(meta):
    return str(meta.get("category") or "").strip().lower().startswith("ai-")


# Normal challenge sync --------------------------------------------------------
# Normal challenges come from the imported backup. Their metadata.yml is the
# source of truth for the player-facing description (`message`, `message_no`),
# the hints when it lists any (`hints`, `hints_no`), and the flag policy (every
# static flag case-insensitive). An optional `state` (visible or hidden) decides
# the challenge's state right after an import of the backup (imported), so the repo
# sets the board a new event starts with; between imports the admin panel's state
# stays. An attached file is replaced when distfiles/ has one of the same name with
# other bytes (_update_files); which files are attached stays as the backup has it.
# Value, category and extra flag variants stay as the backup has them too,
# and so do the hints of a challenge whose metadata lists none. A challenge is
# matched by its metadata `name`, else its folder name. only: see _in_languages.
# A challenge the backup lacks (every one, on a new CTF without an export) is created
# when its metadata has `category`, `value` and `flag`, with its `extra_flags` and its
# distfiles/ attached; from then on it is synced like the others. preview: as in sync_ai_challenges, a new one is
# created hidden; returns the ids of those.
def sync_normal_challenges(base_dir, only=None, imported=False, preview=False):
    updated = flags_fixed = hinted = refiled = 0
    held = []
    for name, cdir, meta in _staged_metadata(base_dir):
        if _is_ai(meta):
            continue
        chname = str(meta.get("name") or name).strip()
        message = _description(meta, only)
        hints = _localized_hints(meta, chname, cdir, only) if meta.get("hints") else None
        flag = str(meta.get("flag") or "").strip()
        state = str(meta.get("state") or "").strip().lower()
        if state and state not in ("visible", "hidden"):
            print(f"  warning: {chname}'s metadata.yml state is {state!r}, not visible or hidden; ignored")
            state = ""
        challenges = Challenges.query.filter_by(name=chname).all()
        if not challenges:
            created = _create_normal(meta, chname, message, flag, cdir, state, preview)
            if created is None:
                if message:
                    print(f"  skip   {chname}: no challenge with that name")
                continue
            if preview:
                held.append(created.id)
            challenges = [created]
        for challenge in challenges:
            if imported and state and challenge.state != state:
                challenge.state = state
                print(f"  update {chname}: {state} (metadata.yml state, after the import)")
            if message and challenge.description != message:
                challenge.description = message
                updated += 1
                print(f"  update {chname}: description")
            if hints is not None and _sync_hints(challenge, hints):
                hinted += 1
                print(f"  update {chname}: {len(hints)} hints")
            for filename in _update_files(challenge, os.path.join(cdir, "distfiles")):
                refiled += 1
                print(f"  update {chname}: file {filename} (replaced with the one in distfiles/)")
            statics = Flags.query.filter_by(challenge_id=challenge.id, type="static")
            # A bulk UPDATE: changing loaded Flags rows makes SQLAlchemy warn about
            # their polymorphic type on flush.
            fixed = statics.filter(db.or_(Flags.data.is_(None), Flags.data != "case_insensitive")).update(
                {Flags.data: "case_insensitive"}, synchronize_session=False)
            if fixed:
                flags_fixed += fixed
                print(f"  update {chname}: flag made case-insensitive")
            contents = {row.content.strip().lower() for row in statics}
            if flag and contents and flag.lower() not in contents:
                print(f"  warning: {chname}'s metadata.yml flag is not one of its CTFd flags")
    db.session.commit()
    print(f"normal challenges synced: {updated} descriptions, {hinted} hint sets, {refiled} files, "
          f"{flags_fixed} flags made case-insensitive")
    return held


def _create_normal(meta, chname, message, flag, cdir, state, preview):
    """A normal challenge the backup lacks, from its metadata.yml; None when that
    has no category, no whole-number value or no flag."""
    category = str(meta.get("category") or "").strip()
    try:
        value = int(str(meta.get("value") or "").strip())
    except ValueError:
        return None
    if not category or not flag:
        return None
    challenge = Challenges(name=chname, description=message, value=value, category=category,
                           state="hidden" if preview else state or "visible", type="standard")
    db.session.add(challenge)
    db.session.commit()
    _sync_flag(challenge, flag)
    for extra in _extra_flags(meta.get("extra_flags")):
        if extra.lower() != flag.lower():
            _add_static_flag(challenge.id, extra)
    db.session.commit()
    _sync_files(challenge, os.path.join(cdir, "distfiles"))
    print(f"  create {chname} [{category}] {value} pts")
    return challenge


def _creatable_normal(meta):
    """Would _create_normal create this challenge (category, a whole-number value and
    a flag in its metadata)?"""
    try:
        int(str(meta.get("value") or "").strip())
    except ValueError:
        return False
    return bool(str(meta.get("category") or "").strip() and str(meta.get("flag") or "").strip())


def _extra_flags(value):
    """metadata.yml `extra_flags`: other spellings accepted as the flag, a list (or
    one string)."""
    items = value if isinstance(value, list) else [value] if isinstance(value, str) else []
    return [str(item).strip() for item in items if str(item).strip()]


# Solve limits -------------------------------------------------------------------
# `max_solves: N` in a challenge's metadata.yml (either bracket): only N accounts
# can solve it, then it locks. Kept as {"<challenge id>": N} in the CTFd config
# SOLVE_LIMIT_CONFIG, which platform/plugins/ctf_solve_limit enforces.
SOLVE_LIMIT_CONFIG = "ctf_solve_limit"


def sync_solve_limits(base_dir):
    wanted = {}
    for name, _cdir, meta in _staged_metadata(base_dir):
        raw = str(meta.get("max_solves") or "").strip()
        if not raw:
            continue
        chname = str(meta.get("name") or name).strip()
        if not raw.isdigit() or int(raw) < 1:
            print(f"  warning: {chname}'s metadata.yml max_solves is {raw!r}, not a number from 1; ignored")
            continue
        for challenge in Challenges.query.filter_by(name=chname).all():
            wanted[str(challenge.id)] = int(raw)
            print(f"  {chname}: locks after {raw} solve" + ("s" if int(raw) > 1 else ""))
    stored = json.dumps(wanted, sort_keys=True)
    if (get_config(SOLVE_LIMIT_CONFIG) or "{}") != stored:
        set_config(SOLVE_LIMIT_CONFIG, stored)


def remove_flagless_duplicates():
    """After an import: delete each hidden challenge that has no flag while a visible
    challenge has its name (a leftover copy in the backup, like a second overflow3), so
    the connection info, the metadata sync and the admin panel see one challenge."""
    from CTFd.plugins.challenges import get_chal_class

    for challenge in Challenges.query.filter_by(state="hidden").order_by(Challenges.id).all():
        if Flags.query.filter_by(challenge_id=challenge.id).first() is not None:
            continue
        twin = Challenges.query.filter(Challenges.name == challenge.name, Challenges.state == "visible",
                                       Challenges.id != challenge.id).first()
        if twin is None:
            continue
        name, cid = challenge.name, challenge.id
        try:
            get_chal_class(challenge.type).delete(challenge)
        except Exception as exc:  # noqa: BLE001 - a leftover hidden copy is harmless
            db.session.rollback()
            print(f"  warning: could not delete the hidden copy of {name} (id {cid}): {exc}", file=sys.stderr)
            continue
        print(f"  delete {name} (id {cid}): a hidden copy without a flag of the visible {name}")


def sync_ai_challenges(base_dir, preview=False, only=None, imported=False):
    """preview: a preview is about to be applied, and its board is public. A new
    challenge is then created hidden and an existing one keeps its state, so none
    shows on that board even for a moment; apply_preview shows the preview's own.
    imported: the backup was imported on this run. Value, state and the exact flag
    come from metadata.yml when a challenge is created and after an import; between
    imports an admin's change in the panel stays (a new value would rescore every
    solve, and an accepted flag variant would vanish). Name, category, description,
    hints and files follow metadata.yml on every up.
    only: see _in_languages. Returns the ids of the challenges created hidden."""
    created = updated = 0
    held = []
    siblings = {}
    difficulty = {}
    try:
        managed = json.loads(get_config(MANAGED_CONFIG) or "{}")
        if not isinstance(managed, dict):
            managed = {}
    except (TypeError, ValueError):
        managed = {}
    seen = set()
    for name, cdir, meta in _staged_metadata(base_dir):
        if not _is_ai(meta):
            continue  # safety: this tool only manages ai-* challenges
        seen.add(name)
        category = str(meta.get("category")).strip()
        chname = str(meta.get("name") or name).strip()
        flag = str(meta.get("flag") or "").strip()
        description = _description(meta, only)
        try:
            value = int(str(meta.get("value") or 300).strip())
        except (TypeError, ValueError):
            value = 300

        # Match on the folder name (stable identity) via the managed map, so a
        # changed `name` renames in place. Fall back to a by-name lookup the first
        # time, to adopt challenges created before the map existed.
        challenge = None
        if name in managed:
            challenge = Challenges.query.filter_by(id=managed[name]).first()
        if challenge is None:
            challenge = Challenges.query.filter_by(name=chname).first()
        if challenge is None:
            challenge = Challenges(name=chname, description=description, value=value, category=category,
                                   state="hidden" if preview else "visible", type="standard")
            db.session.add(challenge)
            db.session.commit()
            if preview:
                held.append(challenge.id)
            created += 1
            action = "create"
        else:
            challenge.name, challenge.description, challenge.category = chname, description, category
            if imported:
                challenge.value = value
                if not preview:
                    challenge.state = "visible"
            db.session.commit()
            updated += 1
            action = "update"
        managed[name] = challenge.id

        if flag:
            _sync_flag(challenge, flag, exact=imported or action == "create")
        _sync_files(challenge, os.path.join(cdir, "distfiles"))
        hints = _localized_hints(meta, chname, cdir, only)
        _sync_hints(challenge, hints)
        n_hints = len(hints)
        builds_on = _builds_on(meta.get("builds_on"))
        if builds_on:
            siblings[chname] = builds_on
        for base in builds_on:
            if Challenges.query.filter_by(name=base).first() is None:
                # the plugin skips unknown names, so say so here instead of
                # silently losing the link (a typo, or a misparsed line)
                print(f"  warning: {chname} builds_on {base!r}, but no challenge has that name")
        threat = _difficulty(meta.get("difficulty"))
        if threat:
            difficulty[chname] = threat
        print(f"  {action:<6} {chname:<16} [{category}] {challenge.value} pts, flag {'set' if flag else 'MISSING'}"
              + (f", threat {threat}/5" if threat else "")
              + (f", {n_hints} hints" if n_hints else "")
              + (f", builds on {', '.join(builds_on)}" if builds_on else ""))
    # Hide challenges whose folder is gone from the repo: the repo is the source of
    # truth, so a removed AI challenge must not stay visible and playable.
    hidden = 0
    for folder in [f for f in managed if f not in seen]:
        orphan = Challenges.query.filter_by(id=managed[folder]).first()
        if orphan is not None and orphan.state != "hidden":
            orphan.state = "hidden"
            hidden += 1
            print(f"  hide   {orphan.name:<16} (folder {folder} removed from the repo)")
    if hidden:
        db.session.commit()
    set_config(MANAGED_CONFIG, json.dumps(managed, sort_keys=True))
    _sync_siblings(siblings)
    _sync_difficulty(difficulty)
    print(f"AI-modus challenges synced: {created} created, {updated} updated"
          + (f", {hidden} hidden" if hidden else ""))
    return held


# Pages ---------------------------------------------------------------------------
# The pages kept in the repo, platform/pages/: <route>.md is the page in English,
# <route>.<code>.md in another language (info.no.md). ctf.sh copies the folder
# into the container (CTF_PAGES_DIR), and on every up each route's files replace
# the content of the CTFd page with that route, as a block per language like a
# challenge's description (only: see _in_languages). A page whose text sits in
# one file (index.md: its script must run once) carries its own blocks
# (class="ctf-lang"); without the theme only the default language's stay. A page keeps its title,
# visibility and place in the navbar as CTFd has them, except the index, which takes
# the event's name (CTF_BRAND_NAME; CTFd shows a page's title in the browser tab, and
# the backup's index is titled after its own event); a route CTFd lacks is
# created, titled after the route. Pages without files here stay as the
# imported backup has them; the index and the Info page have files, so edits to
# them in Admin -> Pages are overwritten on the next up. See docs/language.md.
# Routes created hidden: served at their address, but not in the navbar until
# shown in Admin -> Pages (the break page during the break, the winners and the
# podium at the prize-giving). A created page is titled from its route, or as here.
PAGES_CREATED_HIDDEN = {"pause1", "winners", "podium"}
PAGE_TITLES = {"pause1": "Pause"}


def sync_pages(base_dir, only=None):
    texts = {}
    for name in sorted(os.listdir(base_dir)):
        path = os.path.join(base_dir, name)
        if not name.endswith(".md") or not os.path.isfile(path):
            continue
        route, _, code = name[:-3].rpartition(".")
        if not route or code not in LANGUAGES:
            route, code = name[:-3], SOURCE_LANGUAGE
        with open(path, encoding="utf-8") as fh:
            texts.setdefault(route, {})[code] = fh.read()
    changed = 0
    for route, by_language in sorted(texts.items()):
        content = _in_languages(by_language, only)
        if only:
            content = _keep_language(content, only)
        page = Pages.query.filter_by(route=route).first()
        title = (os.environ.get("CTF_BRAND_NAME") or "").strip() if route == "index" else ""
        if page is None:
            db.session.add(Pages(title=title or PAGE_TITLES.get(route) or route.replace("-", " ").capitalize(),
                                 route=route, content=content,
                                 format="markdown", draft=False, hidden=route in PAGES_CREATED_HIDDEN,
                                 auth_required=False))
            action = "create"
        else:
            action = ""
            if page.content != content or page.format != "markdown":
                page.content, page.format = content, "markdown"
                action = "update"
            if title and page.title != title:
                page.title = title
                print(f"  title  /{route}: {title}")
            if not action:
                continue
        changed += 1
        files = [code for code in LANGUAGES if code in by_language]
        own = len(files) == 1 and 'class="ctf-lang"' in by_language[files[0]]
        print(f"  {action} /{route} ({'its own blocks per language' if own else ', '.join(files)})")
    db.session.commit()
    print(f"pages synced: {changed} of {len(texts)} changed")


# Preview mode -------------------------------------------------------------------
# `ctf.sh up --preview julius,meow1` shows only those challenges, to visitors
# without an account: every other visible challenge is hidden, the pages (the
# Info page) become drafts, which CTFd neither lists nor serves, and the board,
# registration and the account and score pages get PREVIEW_SETTINGS. What the
# preview changed is kept in the config value PREVIEW_CONFIG, so ending it
# (`--preview ""`) puts back exactly that and nothing else. The ctf_preview
# plugin (platform/plugins/) reads the same value to check the preview's flags
# for visitors without an account.
PREVIEW_CONFIG = "ctf_preview"
PREVIEW_REJECTED = 3  # configure's exit code for preview names CTFd doesn't know (ctf.sh)
PREVIEW_SETTINGS = {
    "challenge_visibility": "public",  # the board without logging in
    "registration_visibility": "private",  # nobody needs an account
    "account_visibility": "admins",  # no Users, Teams or Scoreboard pages
    "score_visibility": "admins",
}


def _preview_names(value):
    return [n for n in re.split(r"[,\s]+", value or "") if n]


def _preview_state():
    """The running preview's state, or None when there is no preview."""
    try:
        state = json.loads(get_config(PREVIEW_CONFIG) or "null")
    except (TypeError, ValueError):
        return None
    if not isinstance(state, dict):
        return None
    state.setdefault("hidden", [])  # ids the preview hid: visible again afterwards
    state.setdefault("shown", [])  # ids it made visible: hidden again afterwards
    state.setdefault("config", {})  # each PREVIEW_SETTINGS key's value before
    state.setdefault("pages", {})  # {"<page id>": its draft flag before}
    return state


def _preview_challenges(names, base_dir, ai_sync=False):
    """The CTFd challenges for the folders `names`, and the names that have none.
    A folder's CTFd name is its metadata `name`, else the folder name. A normal
    folder the sync creates counts as found, and so does an AI-modus one with
    ai_sync."""
    metas = {}
    if base_dir and os.path.isdir(base_dir):
        metas = {folder: meta for folder, _cdir, meta in _staged_metadata(base_dir)}
    wanted = []
    missing = []
    for folder in names:
        meta = metas.get(folder, {})
        chname = str(meta.get("name") or folder).strip()
        rows = Challenges.query.filter_by(name=chname).all()
        creatable = (ai_sync and _is_ai(meta)) or (not _is_ai(meta) and _creatable_normal(meta))
        if not rows and not creatable:
            missing.append(chname if chname == folder else f"{chname} ({folder})")
        wanted.extend(rows)
    return wanted, missing


def _preview_error(missing):
    print(f"error: no CTFd challenge named {', '.join(missing)}; the board is left as it was", file=sys.stderr)


def apply_preview(names, base_dir, held=()):
    """Show only the challenges in folders `names`; an empty list ends the preview.
    held: ids of challenges the sync created hidden, to be visible after it.
    False, with nothing changed, when a name matches no CTFd challenge."""
    state = _preview_state()
    if not names:
        if state is not None:
            end_preview(state)
        return True

    wanted, missing = _preview_challenges(names, base_dir)
    # All or nothing: a typo or an unmatched name must not leave a board with
    # fewer challenges than asked for, or none at all.
    if missing:
        _preview_error(missing)
        return False
    state = state or {"hidden": [], "shown": [], "config": {}, "pages": {}}
    wanted_ids = {c.id for c in wanted}

    # A challenge keeps the list it was first put on: both lists hold what it was
    # before the preview, whatever later runs do to it.
    def remember(key, cid):
        if cid not in state["hidden"] and cid not in state["shown"]:
            state[key].append(cid)

    for cid in held:
        remember("hidden", cid)
    for c in wanted:
        if c.state != "visible":
            c.state = "visible"
            remember("shown", c.id)
    for c in Challenges.query.filter(Challenges.state == "visible").all():
        if c.id not in wanted_ids:
            c.state = "hidden"
            remember("hidden", c.id)
    # The index page stays: the plugin sends visitors from it to the board.
    for page in Pages.query.filter(Pages.route != "index", Pages.draft.isnot(True)).all():
        state["pages"].setdefault(str(page.id), page.draft)
        page.draft = True
    for key in PREVIEW_SETTINGS:
        if key not in state["config"]:
            state["config"][key] = get_config(key)
    state["challenges"] = sorted(wanted_ids)
    # set_config commits the pending challenge-state changes together with the
    # preview record, so a crash can't leave challenges hidden with nothing recorded
    # to restore them from.
    set_config(PREVIEW_CONFIG, json.dumps(state, sort_keys=True))
    # Clear the challenge-list cache before the board goes public, so an anonymous
    # visitor can't be served the pre-preview list from CTFd's 60s memoization.
    clear_challenges()
    # Only now, with everything else hidden and the cache cleared, does it go public.
    for key, value in PREVIEW_SETTINGS.items():
        set_config(key, value)
    shown = ", ".join(sorted(c.name for c in wanted))
    print(f"preview: {shown}, without an account; every other challenge and page hidden")
    return True


def end_preview(state):
    # The board stops being public before anything on it turns visible again.
    for key, value in state["config"].items():
        set_config(key, value)
    restored = 0
    for cid in state["hidden"]:
        c = Challenges.query.filter_by(id=cid).first()
        if c is not None and c.state == "hidden":
            c.state = "visible"
            restored += 1
    for cid in state["shown"]:
        c = Challenges.query.filter_by(id=cid).first()
        if c is not None and c.state == "visible":
            c.state = "hidden"
    for pid, draft in state["pages"].items():
        page = Pages.query.filter_by(id=int(pid)).first()
        if page is not None:
            page.draft = draft
    db.session.commit()
    set_config(PREVIEW_CONFIG, None)
    print(f"preview ended: {restored} challenges visible again, settings restored")


# AI-modus theme injection ----------------------------------------------------
# The looks in platform/theme/ are linked from CTFd's theme_header/theme_footer: a
# <link> or <script src> per file, which the ctf_theme plugin serves from
# platform/theme (mounted at THEME_DIR by platform/ctfd.yml). Inlined, the files
# would outgrow the 64 KB a config value holds in MariaDB. The tags sit between
# these markers, so they can be replaced idempotently and the backup's own
# theme_header is preserved. Each URL carries the file's hash, so a changed file
# gets a new URL on the next up.
AI_START = "<!-- >>> ai-modus (managed by ctf.sh) >>> -->"
AI_END = "<!-- <<< ai-modus <<< -->"
THEME_DIR = os.environ.get("CTF_THEME_DIR", "/opt/ctf-theme")
THEME_URL = "/ctf-theme/"  # platform/plugins/ctf_theme


def _strip_managed(text):
    if not text:
        return ""
    pattern = re.compile(re.escape(AI_START) + r".*?" + re.escape(AI_END), re.DOTALL)
    return pattern.sub("", text).rstrip()


def strip_ai_theme():
    header = _strip_managed(get_config("theme_header") or "")
    footer = _strip_managed(get_config("theme_footer") or "")
    set_config("theme_header", header + ("\n" if header else ""))
    set_config("theme_footer", footer + ("\n" if footer else ""))
    print("AI-modus theme removed from theme_header/theme_footer")


def _theme_tag(name):
    """The tag for platform/theme/<name>, or None (with a warning) when it is missing."""
    try:
        version = _sha1_of(os.path.join(THEME_DIR, name))[:12]
    except OSError:
        print(f"warning: {name} is missing from {THEME_DIR}; the theme goes without it", file=sys.stderr)
        return None
    root = (current_app.config.get("APPLICATION_ROOT") or "/").rstrip("/")
    url = f"{root}{THEME_URL}{name}?v={version}"
    if name.endswith(".css"):
        return f'<link rel="stylesheet" href="{url}">'
    return f'<script src="{url}"></script>'


# window.ctfI18n until i18n.js replaces it, so the other theme scripts can call
# it without checking: should i18n.js fail to load, they show the keys instead of
# breaking. The same calls as i18n.js's.
I18N_STANDIN = (
    "window.ctfI18n = {lang: function () { return \"en\"; }, languages: [],"
    " t: function (k) { return k; }, set: function () {}, apply: function () {},"
    " bind: function (e, k) { if (e.textContent !== k) e.textContent = k; return e; },"
    " bindAttr: function (e, a, k) { e.setAttribute(a, k); return e; },"
    " sourceText: function (e) { return e.textContent; }};"
)


def inject_ai_theme(preview=False, lang=DEFAULT_LANGUAGE):
    """preview: a preview runs. The page then has the Classic lane only (no lane
    control, no AI-modus) in the preview's terminal look. lang: the language a
    player sees until they pick one. Both are attributes on <html>, set before
    i18n.js and ai-mode.head.js run."""
    if not os.path.isdir(THEME_DIR):
        print(f"warning: {THEME_DIR} is not mounted; the theme is left as it was", file=sys.stderr)
        return
    base_header = _strip_managed(get_config("theme_header") or "")
    base_footer = _strip_managed(get_config("theme_footer") or "")
    head = [_theme_tag("ai-mode.css")]
    foot = [_theme_tag("ai-mode.js")]
    if preview:
        head.append(_theme_tag("preview.css"))
    marks = [f'document.documentElement.setAttribute("data-ctf-lang-default", "{lang}");']
    if preview:
        marks.append('document.documentElement.setAttribute("data-ctf-preview", "");')
    marks.append(I18N_STANDIN)
    head.append("<script>" + " ".join(marks) + "</script>")
    # The words, then the language runtime, before anything that shows text.
    head += [_theme_tag("i18n.strings.js"), _theme_tag("i18n.js"), _theme_tag("ai-mode.head.js")]
    if preview:
        head.append(_theme_tag("preview.head.js"))
        foot.append(_theme_tag("preview.js"))
    else:
        # First blood (platform/plugins/ctf_firstblood): a preview saves no solve.
        head.append(_theme_tag("first-blood.css"))
        foot.append(_theme_tag("first-blood.js"))
        # Solve limits (platform/plugins/ctf_solve_limit): the lock on the board.
        foot.append(_theme_tag("solve-limit.js"))
    head_block = "\n".join([AI_START, *filter(None, head), AI_END])
    foot_block = "\n".join([AI_START, *filter(None, foot), AI_END])
    header = (base_header + "\n\n" if base_header else "") + head_block + "\n"
    footer = (base_footer + "\n\n" if base_footer else "") + foot_block + "\n"
    set_config("theme_header", header)
    set_config("theme_footer", footer)
    look = ", with the preview's terminal look" if preview else ""
    print(f"AI-modus theme linked{look} (from {THEME_URL}), language {lang} unless a player picks another")


# The backups set challenge_window_size to "sm" (Bootstrap's fixed 300px
# modal-sm), which is too narrow: the flag input squeezes the Submit button
# until its label overflows. "lg" is 800px and still shrinks on phones.
CHALLENGE_WINDOW_SIZE = "lg"


def set_challenge_window_size(size):
    raw = get_config("theme_settings") or "{}"
    try:
        settings = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except ValueError:
        settings = {}
    if settings.get("challenge_window_size") == size:
        return
    settings["challenge_window_size"] = size
    set_config("theme_settings", json.dumps(settings, indent=2))
    print(f"challenge window size set to {size}")


# The event's name, the navbar logo and the favicon (Admin -> Config -> General /
# Logo / Small Icon) come from the brand folder ctf.sh is set to (--brand, by
# default platform/theme/brand), not from the imported backup. ctf.sh copies the
# folder into the container (CTF_BRAND_DIR) and passes the event name in
# CTF_BRAND_NAME and each file's path in the folder (as brand.conf names it) in
# CTF_BRAND_LOGO / CTF_BRAND_ICON; an empty value leaves CTFd's own. A path that
# leads out of the folder is refused. (The bytes are read from the folder, not passed as a
# base64 env var, so a logo of any size works.) The name is the page title, the
# logo's alt text and the start of an export's file name. A file is uploaded only
# when its bytes differ from the file CTFd serves now, so a rerun adds nothing, and
# the file it replaces is deleted (after a --reimport, the backup's own logo) unless
# something else still uses it.
BRAND_FILES = (("ctf_logo", "CTF_BRAND_LOGO"), ("ctf_small_icon", "CTF_BRAND_ICON"))


def sync_brand():
    """Cosmetic, so a failure (an upload that can't be written) only warns."""
    try:
        _sync_brand()
    except Exception as exc:  # noqa: BLE001 - never stop configure for a logo
        db.session.rollback()
        print(f"warning: could not set the event's name, logo or icon: {exc}", file=sys.stderr)


def _sync_brand():
    from CTFd.utils.uploads import delete_file, upload_file
    from werkzeug.datastructures import FileStorage

    name = (os.environ.get("CTF_BRAND_NAME") or "").strip()
    if name and get_config("ctf_name") != name:
        set_config("ctf_name", name)
        print(f"ctf_name set to {name}")
    brand_dir = os.environ.get("CTF_BRAND_DIR") or ""
    root = os.path.realpath(brand_dir) if brand_dir else ""
    for key, env in BRAND_FILES:
        relpath = (os.environ.get(env) or "").strip()
        if not relpath or not root:
            continue
        path = os.path.realpath(os.path.join(root, relpath))
        if os.path.commonpath([root, path]) != root:
            print(f"{key}: {relpath} is outside the brand folder, left as it is", file=sys.stderr)
            continue
        filename = os.path.basename(path)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            print(f"{key}: {relpath} not found in the brand folder, left as it is", file=sys.stderr)
            continue
        current = Files.query.filter_by(location=get_config(key) or "").first()
        if current is not None and current.sha1sum == hashlib.sha1(data).hexdigest():  # nosec - not security
            continue
        row = upload_file(file=FileStorage(stream=io.BytesIO(data), filename=filename), type="standard")
        set_config(key, row.location)
        print(f"{key} set to {filename}")
        # The file it replaces goes, if it is a standard upload no other brand key uses.
        if current is not None and current.type == "standard" and not any(
                get_config(other) == current.location for other, _env in BRAND_FILES):
            try:
                delete_file(current.id)
            except Exception as exc:  # noqa: BLE001 - a leftover file is harmless
                db.session.rollback()
                print(f"  could not delete the replaced {current.location}: {exc}", file=sys.stderr)


# Players don't rate or review challenges: "disabled" removes CTFd's "Rate this
# challenge" box and review field from every challenge window, and the like counts.
def disable_challenge_ratings():
    if get_config("challenge_ratings") != "disabled":
        set_config("challenge_ratings", "disabled")
        print("challenge ratings turned off")


def configure(args):
    if getattr(args, "connections_only", False):
        # ./ctf.sh connections: refresh connection info and touch nothing else.
        connections = os.environ.get("CTF_CONNECTIONS")
        if connections:
            print("connection info:")
            apply_connections(connections)
        return

    challenges_dir = os.environ.get("CTF_CHALLENGES_DIR")
    if challenges_dir and not os.path.isdir(challenges_dir):
        challenges_dir = None
    ai_sync = bool(challenges_dir) and not args.no_ai_challenges
    # Check a preview's names before anything changes, so a bad one leaves CTFd as
    # it was.
    names = _preview_names(args.preview)
    if names:
        _wanted, missing = _preview_challenges(names, challenges_dir, ai_sync=ai_sync)
        if missing:
            _preview_error(missing)
            sys.exit(PREVIEW_REJECTED)
    elif args.preview is not None:
        # Ended before the sync makes the AI-modus challenges visible, so the board
        # is no longer public by then.
        apply_preview([], challenges_dir)

    initial_setup()

    if args.clear_dates:
        clear_event_dates()
    set_event_settings(args)

    set_challenge_window_size(CHALLENGE_WINDOW_SIZE)
    disable_challenge_ratings()

    if args.registration_code is not None:
        set_config("registration_code", args.registration_code or None)
        print("registration code " + ("set" if args.registration_code else "cleared (open registration)"))

    password = os.environ.get("CTF_ADMIN_PASSWORD")
    if password:
        set_admin_password(os.environ.get("CTF_ADMIN_NAME", "admin"), password)

    if args.remove_participants:
        remove_participants()

    # Sync challenges from the repo before connections, so a hosted AI-modus one
    # (e.g. robot-ai) exists when its connection info is written. In a preview the
    # sync makes none of them visible; apply_preview shows the preview's own.
    # The theme's language switch needs CTFd's own pages in English underneath
    # and every text in all languages; stock CTFd gets the default language only.
    only = args.lang if args.no_ai_theme else None
    set_default_locale(args.lang if args.no_ai_theme else SOURCE_LANGUAGE)
    if not args.no_ai_theme:
        clear_user_languages()

    held = []
    if args.imported:
        remove_backup_brackets_and_fields()
        remove_flagless_duplicates()
    if challenges_dir:
        print("normal challenges (description, hints and flag case from metadata.yml, changed files from distfiles/):")
        held = sync_normal_challenges(challenges_dir, only=only, imported=args.imported, preview=bool(names))
        if ai_sync:
            print("AI-modus challenges:")
            held += sync_ai_challenges(challenges_dir, preview=bool(names), only=only, imported=args.imported)
        sync_solve_limits(challenges_dir)

    # Before a preview, which then hides them like every other page.
    pages_dir = os.environ.get("CTF_PAGES_DIR")
    if pages_dir and os.path.isdir(pages_dir):
        print("pages (platform/pages):")
        sync_pages(pages_dir, only=only)

    connections = os.environ.get("CTF_CONNECTIONS")
    if connections:
        print("connection info:")
        apply_connections(connections)

    preview_failed = bool(names) and not apply_preview(names, challenges_dir, held=held)

    if args.no_ai_theme:
        strip_ai_theme()
    else:
        inject_ai_theme(preview=_preview_state() is not None, lang=args.lang)

    sync_brand()

    if args.remove_participants:
        # Also drops sessions of the removed players.
        cache.clear()
    else:
        clear_challenges()
        clear_config()
        clear_pages()
        clear_standings()

    print(f"theme: {get_config('ctf_theme')}")
    if preview_failed:
        sys.exit(PREVIEW_REJECTED)


def main():
    parser = argparse.ArgumentParser(prog="ctfd_admin.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("count")
    conf = sub.add_parser("configure")
    conf.add_argument("--clear-dates", action="store_true", help="remove start/end/freeze time")
    conf.add_argument("--imported", action="store_true",
                      help="the backup was imported on this run: the repo sets state, value and exact flags")
    conf.add_argument("--event-start", help="start time, ISO 8601 with its UTC offset; empty clears it")
    conf.add_argument("--event-end", help="end time, the same way")
    conf.add_argument("--event-freeze", help="scoreboard freeze time, the same way")
    conf.add_argument("--team-size", help="most players in a team; empty clears it")
    conf.add_argument("--registration-code", help="empty string clears it")
    conf.add_argument("--remove-participants", action="store_true", help="delete non-admin users, teams, submissions")
    conf.add_argument("--connections-only", action="store_true",
                      help="write only the connection info (CTF_CONNECTIONS); change nothing else")
    conf.add_argument("--ai-theme", action="store_true", help="(default) link the AI-modus theme from platform/theme")
    conf.add_argument("--no-ai-theme", action="store_true", help="remove the AI-modus theme block from theme_header/footer")
    conf.add_argument("--no-ai-challenges", action="store_true", help="leave the ai-* challenges as they are in CTFd")
    conf.add_argument("--preview", help="challenge folders (comma-separated) shown without an account; empty ends the preview")
    conf.add_argument("--lang", choices=LANGUAGES, default=DEFAULT_LANGUAGE,
                      help="the language players see until they pick one (NO | EN in the navbar)")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        {"count": count, "configure": configure}[args.command](args)


main()
