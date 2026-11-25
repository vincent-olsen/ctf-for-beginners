# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of self-contained CTF challenges (run at several company and
conference CTFs since 2024) plus the tooling to run them locally and ship them to a
hosted **CTFd** instance. The repository is **public**: see "Public repository"
below before committing anything. It is the content for a beginner-oriented "intro to ethical hacking"
CTF. Each directory under `challenges/normal/` (`meow1/`, `viking/`,
`overflow3/`, ...) or `challenges/ai/` (`robot-ai/`, `rsa-ai/`, ...) is one
challenge; challenges are independent and share no application code. The folder
name is the challenge's identity everywhere (compose service, `local.sh`
argument), so names must be unique across both groups;
`tools/challenge.sh` (the lookup shared by `ctf.sh`, `local.sh`, `azure.sh`)
refuses duplicates.

Top level: `challenges/` (see `challenges/README.md` for the index), `platform/`
(CTFd config + AI theme + `plugins/ai_brackets` + `pages/`, the front and Info pages in
English and Norwegian, synced into CTFd + `azure/`: the Bicep template and VM bootstrap), `docs/`, `writeup/` (the players' writeup of every challenge, `writeup.md` built into `writeup.pdf` by `build.sh` with pandoc + pdflatex), `ctfd-backup/` (the organiser's CTFd exports and database dumps, git-ignored apart from its README), `tools/pwn/` (scratch),
`tools/challenge.sh` (shared challenge lookup), and the
entrypoints `ctf.sh`, `compose.yml`, `local.sh`, `azure.sh`. Challenge names below
are bare folder names; resolve them under `challenges/normal/` or `challenges/ai/`.

## Challenge layout contract

Every challenge directory follows the same structure (the comment header is
duplicated in each `metadata.yml`):

- `challenge/` — everything needed to build the challenge asset. For hosted
  challenges this contains a `Dockerfile`; the real flag lives here (`flag.txt`,
  an `ENV FLAG=...`, or embedded in source). For a challenge whose asset is a
  static file, `challenge/` may hold a `.keep` placeholder while the artifact
  sits in `distfiles/` (`unk`, `pdfcrypt`). Every challenge has a `challenge/`
  directory (`git`'s holds the source `flag.txt` its scratch repo is built around).
- `distfiles/` — the files handed to the player in CTFd. When nothing is
  attached, a `.keep` placeholder holds the directory. Distfiles are often a
  *subset* of `challenge/` (e.g. source without the real flag), so keep them in
  sync deliberately, not by copying the whole challenge.
- `solution/` — a working exploit and/or a `README.md`/`writeup.md` explaining
  the intended solve. The writeup has a `## Debrief: what you learn and how to
  protect against it` section (what you learn, the solve in short, the defence);
  in an AI-modus writeup it sits right before `## How hard it is for an AI`.
- `metadata.yml` (`binary1`/`binary2` use `metadata.yaml`) — the source of truth
  for the challenge. `ctf.sh up` creates a normal challenge CTFd lacks (on a new CTF,
  every one; `_create_normal`) from its `category`, `value`, `state`, `flag` plus
  `extra_flags` and `distfiles/` (matched by `name`, else the folder name). On every
  run it syncs the `message` / `message_no` into the CTFd description, the `hints` /
  `hints_no` into its hints when metadata lists any, makes its static flags
  case-insensitive, and replaces an attached file when `distfiles/` has one of the
  same name with other bytes; value, category, extra flags and which files are
  attached are set only at creation (or come from an imported CTFd export, for a
  challenge it has), and so is the state, except that `state:` is applied again
  right after an import (between imports the admin panel decides). AI-modus
  challenges are synced in full, except that value, state and the exact flag also
  follow metadata only on create and import.

`metadata.yml` fields: `flag`, `category`, `value` (points), `message` (player-facing description in English,
which `ctf.sh up` writes into CTFd. Setup help, such as which tool to connect with, is fine; never add
solution hints, that's what CTFd hints are for), `message_no` (the same in
Norwegian; see "Language"), `hints` / `hints_no` (paid hints, `"COST | text"`,
English and Norwegian in the same order; a multi-line one is a `- |` block;
cheapest first: `_sync_hints` makes a challenge's strictly cheaper hints each
hint's CTFd prerequisites, so a player buys up the ladder and hints of equal cost
stay a free choice, and `platform/plugins/ctf_hints`, always installed, refuses a
purchase out of order, which CTFd's own unlock endpoint does not check),
`notes` (internal
category/technique), and for networked challenges
`connection` / `port` / `protocol`. Optional `name`, `credits`, `extra_flags` (a
list of other spellings accepted as the flag, added when the challenge is created),
`max_solves`, `state` (normal challenges: `visible` or `hidden`, applied at creation
and right after an import). Flags are
`flag{...}` and configured **case-insensitive** in CTFd. `connection`/`port` are
event-specific (CTFd assigns the external host/port per deploy), so committed
values use a `<port>` placeholder that is filled in from the CTFd service after
deployment. AI-modus challenges add `category` (an `ai-…` value), `value`
(points) and `builds_on` (the normal challenges they level up), read by the auto-sync (see "AI-modus (two brackets)").

Category (`category`, the CTFd category) vocabulary in use: `misc`, `web`, `crypto`,
`forensics`, `code`, `sponsor`, plus binary/pwn.

## Three deployment archetypes

Recognise which one a challenge is before editing it:

1. **Static distfile (not hosted)** — no `Dockerfile`. The player downloads the
   `distfiles/` and solves offline; in CTFd it is just attachment(s) + a flag,
   with no Service. This is the largest group: `decode1`–`decode3`, `julius`,
   `birds`, `mono`, `operator`, `flagception`, `art`, `image`, `qrcode`,
   `email`, `git`, `unk`, `pdfcrypt`. `local.sh` does **not** apply here.
2. **Terminal / pwn** — `socat TCP-LISTEN:<port>,reuseaddr,fork EXEC:...,pty,...`.
   Either wraps an interactive `/bin/bash -li` with a custom `bashrc` that prints
   the intro and drops the player in a locked-down home dir (`meow*`), or wraps a
   compiled vulnerable binary (`overflow*`, `binary*`). Runs as an unprivileged
   `ctf` user; the flag is `chmod 0400` and readable only via the intended bug.
3. **Web** — a long-running server. Patterns in use: Flask + `gunicorn`
   (`noter1`–`noter4`, `marvin`), FastAPI via `uv run fastapi` (`api1`–`api3`),
   Go + gin compiled to a static binary (`viking`). Web challenges `EXPOSE` an
   HTTP port (usually 5000/8080).

`paper` is a fourth kind, physical: its flag is printed on an A5 card
(`challenge/paper-flag.pdf`, built by `challenge/make-card.py` from `flag.txt`) that
the organiser hides in the venue; nothing is hosted or attached. Like every
challenge it is created from its metadata. Its `max_solves: 1` (any challenge may set
`max_solves: N`) is kept in the CTFd config `ctf_solve_limit` and enforced by
`platform/plugins/ctf_solve_limit`, always installed: after N solves by visible accounts
later flags are refused, and `platform/theme/solve-limit.js` (linked with the theme, not
in a preview) marks the tile and names the finder in the challenge window.

`noter5` is multi-service: it depends on `noter5-backend` being deployed first.
The proxy reaches the backend via the `BACKEND_URL` env var (default backend host
`app:5000`) and its `init.py` seeds the flag through the proxy via `PROXY_URL`
(default `127.0.0.1:1024`); `start.sh` runs `init.py` in the background alongside
gunicorn, and `init.py` retries until both answer. Treat cross-challenge
dependencies as real deploy ordering. `noter5-backend` has no player-facing
flag/message — it is infrastructure for `noter5`. For the last event `noter5`,
`noter5-backend`, `marvin`, `binary1`, `binary2`, `overflow4` and `overflow5` (CTFd
name `binary`) sit in the `extra` profile in `compose.yml` (`x-extra`) and are
`hidden` in `platform/connections.txt`: `ctf.sh up` neither starts nor shows them,
and stops them if they still run. The published pwn track is `overflow1`–`overflow3`;
`binary1`/`binary2` are retired (the overflows supersede them) and `overflow5` is
kept ready to release mid-event. All four hidden pwn challenges also carry
`state: hidden` in their `metadata.yml`.

## Binary / pwn challenge specifics

Only `overflow1`–`overflow3` and the AI-modus `pwn-ai` build from a `Makefile`;
it deliberately disables
hardening so the intended exploit works:

```
gcc -O0 -g -fno-stack-protector -U_FORTIFY_SOURCE -no-pie
```

Do **not** "fix" these flags — removing `-fno-stack-protector` or `-no-pie`
breaks the challenge. (Exception: `pwn-ai` builds **stripped** — no `-g`, with
`-s` — on purpose: its named `win`/`gadget` symbols made the ret2win trivial for
an AI to read off `nm`. Stripping removes only the symbol table; the no-PIE
addresses are unchanged, so it does not affect exploitability. The `overflow*`
challenges keep `-g`.) `pwn-ai`'s `win()` also *uses* the `rdi` argument as the
flag's decryption key: the flag ships only encrypted (`flag.enc`), so returning
past the `0xc0ffee` check prints only static and the argument is unavoidable (the
earlier "return to the inner flag-printer" shortcut is closed). Its `Makefile`
therefore has two steps — `mkenc` (which shares the stream cipher `cipher.h` with
the binary) regenerates `flag.enc` from `flag.txt`, then the binary is built; the
plaintext `flag.txt` stays in the repo (source of truth + `tools/check-flags.py`)
but is **not** copied into the container. The committed `bin` / `binary` files are
the exact artifacts players receive. `overflow4`, `overflow5`, `binary1`, `binary2` ship a
prebuilt `binary` (+ `binary.c`) with no `Makefile`, so there is no `make`
target for them — rebuild by matching the same hardening-off `gcc` flags if you
change the source.

`tools/pwn/` is a scratch exploit-development directory (loose `.c`/compiled files, no
`metadata.yml` and no `challenge/distfiles/solution` triad). It is **not** a
packaged challenge.

## Commands

Run the whole CTF — CTFd plus every hosted challenge, with CTFd connection info
filled in. No CTFd export is needed: on a CTFd that was never set up (no export in
`ctfd-backup/`), `ctf.sh` `new_ctf` writes the import marker and `ctfd_admin.py`
`initial_setup` does CTFd's setup (admin account, teams mode, the earlier events'
visibility settings, `SETUP_SETTINGS`), after which every challenge and page is
created from the repo. If `ctfd-backup/` holds an export, the newest is imported
instead. `--reimport` wipes CTFd (without an export: drops and recreates its MariaDB
database, then sets it up again). `--domain <name>` switches to
hosted mode (Caddy/HTTPS). See `docs/local-setup.md` and `docs/hosting.md`:

```bash
./ctf.sh up        # also: down, status, logs <svc>, reset <svc>, connections --host <h>, backup [--db], restore-db [FILE]
```

`up` also takes `--event-start/--event-end/--event-freeze TIME` (ISO 8601 with its UTC
offset) and `--team-size N`, saved and set in CTFd on that run and after every import,
and `--status on|off` for the public status page (Gatus, `platform/ctfd.status.yml`,
`status.<domain>` through Caddy, `localhost:8081`; `ctf.sh` writes its config to
`.ctf/status/` from `compose.yml` + `connections.txt`). `backup --db` dumps CTFd's
database to the git-ignored `ctfd-backup/db/` (`--if-event`: only within the event's
window, for a timer); `restore-db` loads one back (without FILE it lists them, newest
first, and asks which; `azure.sh restore` runs that on the VM). An `up` that finds CTFd empty after
it was configured stops instead of starting a new CTF over it. An import also drops
the backup's own CTFd brackets and custom registration fields (an earlier event's
team sizes, skill levels, employer/school field), so the registration and team forms ask for nothing
from an earlier event; ones added in the admin panel afterwards stay until the next import.

`compose.yml` declares every hosted challenge with a unique host port;
`platform/connections.txt` maps CTFd challenge names to a compose service and a
connection template (`nc {host} {port}`, `http://{host}:{port}`). State lives in
the git-ignored `.ctf/`.

Host it on Azure (`docs/azure.md`): one short-lived deployment per environment
(`tst`, `prd`; each on the domain its first `up` gets with `--domain`, kept in the
group's `domain` tag) in resource group `rsg-<env>-ctf`, a VM that runs `ctf.sh up --domain`. A Logic App in the group deletes it
the night after its `expires-on` tag, which `azure.sh` keeps at most 31 days ahead; another
(opt-in, `--start HHMM`) starts the VM on weekday mornings. Each runs as its own
system-assigned identity, which an Owner grants a role once (`up` prints the commands):
Contributor on the group for the expiry, Virtual Machine Contributor on the VM for the
start, only while `--start` is on:

```bash
./azure.sh up [--env prd]   # also: deploy, open, close, allow-me, status, extend, stop/start, ssh, backup, restore, down
```

`azure.sh` reads the challenge host ports from `compose.yml` for the NSG, and
`platform/azure/bootstrap.sh` firewalls every Docker bridge named `ctf-*` (no IMDS, VM
agent, host or, by default, outbound internet from a player's shell). A new Docker
network in `compose.yml` needs a `com.docker.network.bridge.name` starting with `ctf-`.
The VM deliberately has no managed identity; keep it that way. `bootstrap.sh` also
installs `ctf-backup.timer` (`ctf.sh backup --db --if-event` every 10 minutes) and keeps
security updates from restarting Docker (needrestart override, no automatic reboot);
`azure.sh` passes the event options through (they're `--event-*`, since `--start` is the
VM's morning start), writes the `status.<domain>` DNS record, and its rsync leaves the
VM's `ctfd-backup/db/` alone.

Preview mode (`docs/azure.md`, "A preview before the event"): `--preview julius,meow1`
(on `ctf.sh up`, `azure.sh up`/`deploy`) shows only those challenges, to visitors
without a CTFd account. On Azure it runs on the tst deployment, on a domain of its
own (`azure.sh up --domain <preview domain>`). `ctf.sh` starts only their containers and installs the
`platform/plugins/ctf_preview` plugin, which checks their flags without saving
anything; `ctfd_admin.py` hides the rest, sets four visibility settings, and records
what it changed in the CTFd config `ctf_preview`, so `--preview ""` restores exactly
that. A preview also gets its own look, injected only then: `platform/theme/preview.css`
(a green-phosphor terminal) and `preview.head.js`/`preview.js` (a 5-second boot screen
once per browser session, and a countdown to the event's start, `CTF_PREVIEW_EVENT_START`
at the top of `preview.js`, under the page title). Its solves are kept in the browser
only (`localStorage` `ctf-preview-solved`) and marked on the board. A correct flag gets
a short celebration in every look: Classic confetti, AI-modus fire (`ai-mode.js`
`celebrate`), the preview's `ACCESS GRANTED` terminal (`preview.js`). The event's name, navbar logo and favicon, in both looks, come
from a brand folder (`ctf.sh up --brand DIR`, saved; default `platform/theme/brand`,
whose `brand.conf` says `CTF for n00bs`, with a neutral flag logo; `--brand ""` leaves CTFd's own):
`ctfd_admin.py sync_brand` sets CTFd's `ctf_name`, `ctf_logo` and `ctf_small_icon`
from it on every `up`. `--sso-client-id` (with `--sso-tenant` on `ctf.sh`) adds Microsoft sign-in in
front of CTFd: oauth2-proxy in `platform/ctfd.sso.yml`, selected by `CTF_AUTH=sso` in
the Caddyfile, hosted mode only. `azure.sh --player-ip` opens the challenge ports, not
SSH, to fixed addresses (an office, say, whose VPN is full-tunnel) through the NSG rule
`allow-challenges-players`.

Run a single hosted challenge locally. Takes a single argument: a bare name,
which must match exactly one `challenges/*/<name>`, or a path to a challenge
folder, used as given. The host→container port comes from the challenge's
`compose.yml` service; without one, the Dockerfile's `EXPOSE` port is mapped 1:1:

```bash
./local.sh <challenge>
```

Rebuild a `Makefile`-based binary challenge (`overflow1`–`overflow3` in
`challenges/normal/`, `pwn-ai` in `challenges/ai/`):

```bash
make -C challenges/*/<challenge>/challenge    # e.g. challenges/ai/pwn-ai/challenge
```

Deploying is not a registry push or a manual admin-panel workflow: `ctf.sh up`
builds every challenge from `compose.yml`, runs the container, and syncs it into
CTFd (description/hints/flag case for normal challenges; full create for AI-modus
ones), then writes the connection info. On Azure, `azure.sh` copies the repo to the
VM and runs `ctf.sh` there. Adding a challenge is covered in [README.md](README.md)
and the "When adding a challenge" section below.

## When adding a challenge

Put it in `challenges/normal/` (or `challenges/ai/` for an AI-modus one) and
replicate the directory contract exactly: a correctly spelled `challenge/`, a
`distfiles/` (with a `.keep` when otherwise empty), a `solution/` (its writeup
with the Debrief section), and a
`metadata.yml` (the description in English `message` and Norwegian `message_no`,
hints likewise). For a hosted challenge give the `Dockerfile` an `EXPOSE` line,
since both `local.sh` and the CTFd port setup rely on it, then add a service with
an unused host port to `compose.yml` and a line to `platform/connections.txt` so
`ctf.sh` runs it and writes its connection info (on Azure, `./azure.sh up` then opens
the port in the NSG). Keep the real flag out
of `distfiles/` — ship only what the player needs to solve, never the answer.

## Language (Norwegian and English)

Players see English by default and switch with a small **NO | EN** at the far
end of the navbar (instant, no reload, remembered per browser); `ctf.sh up --lang
no` (or `azure.sh up`/`deploy --lang no`) changes the default (saved). Full guide:
[docs/language.md](docs/language.md).

- Every platform word is in `platform/theme/i18n.strings.js`: the theme's own
  (`strings`, both languages side by side; `css.` keys become `--ctf-t-*` CSS
  variables for `content:`) and CTFd's (`ctfd`/`ctfdPatterns`: CTFd's exact
  English and its replacement). `i18n.js` (linked before `ai-mode.head.js`) sets
  `html[data-ctf-lang]`/`lang` before paint, exposes `window.ctfI18n` (`t`, `bind`,
  `bindAttr`, `set`, `sourceText`; `ctfd_admin.py` writes a stand-in before it, so
  other scripts call it unchecked), translates CTFd's unlock `confirm`/`alert`, replaces CTFd's English text nodes as they
  render (never challenge content, names, or Admin → Pages content), and builds the
  switch. Theme code never hardcodes player-facing text: use `t(key)`, or `bind`
  for text that stays on the page, and add the key in both languages.
- With the theme linked, `ctfd_admin.py` pins CTFd's `default_locale` to `en` (the
  translation layer matches English), clears players' saved CTFd Language (`i18n.js`
  drops CTFd's `language` cookie), and writes descriptions and hints as a block
  per language (`<div class="ctf-lang" lang="no">`); `ai-mode.css` shows the
  page's language. With `CTF_AI_MODE=off` it writes the default language only and
  sets `default_locale` to it (CTFd's own translation, its own language menu).
- New challenges need `message_no` (and `hints_no` with `hints`). CTFd's admin
  panel and graph titles (drawn on canvas) stay English.
- Pages: `platform/pages/<route>.md` (English) and `<route>.no.md` replace the
  content of the CTFd page with that route on every `up` (`ctf.sh` copies the folder
  in as `CTF_PAGES_DIR`; `ctfd_admin.py sync_pages`), title and visibility kept.
  `info` is there as two files; `index` (the front page) as one file with its own
  `class="ctf-lang"` blocks, since its countdown script must run once (without the
  theme `_keep_language` drops the other language's). A page CTFd lacks is created;
  `pause1`, `winners` and `podium` are created hidden (`PAGES_CREATED_HIDDEN`), to be
  shown in Admin → Pages when it's time.
  `podium` shows each bracket's top 3 from
  the plugin's `/ai-brackets/winners`, which withholds them while the CTF runs or the
  scoreboard is frozen (an admin's `?reveal=1` gets the unfrozen result, for the
  page's full-screen presenter mode, `/podium#present`); see docs/ai-mode.md, "The
  podium page". Keep its markup free of blank lines and the blank line before `<script>`.
  The Info page is generic: it says the registration code is handed out on the day
  (never commit the code) and points to the organisers for help; an event fills in
  its own details (time, agenda, contact) before it starts.

## AI-modus (two brackets)

The event runs two brackets in one CTFd, split purely by **challenge category**:
normal categories (`web`, `crypto`, …) vs. AI-modus categories prefixed `ai-`
(`ai-crypto`, `ai-web`, `ai-pwn`, …). A navbar lane control (Classic | AI-MODUS) filters the board to one
bracket; Classic is a calm blue skin, AI-modus a burning "fun mode" (boot
sequence, flames, matrix rain, a random flicker that spaces out over the session).
In AI-modus the **AI Slop-o-meter** (bottom left, `ai-mode.js`) picks how much:
−1 WEB 1.0 (a 2003 homepage), 1 CALM (no moving effects), 2 BURN (the default) or
3 AI HORROR (maximum slop), kept in `localStorage` `ctf-ai-fx` and set on `<html>`
as `data-ai-fx` before paint; Classic has none of it.

- Lane control + skin source live in `platform/theme/` (`ai-mode.css`,
  `ai-mode.head.js`, `ai-mode.js`). `platform/ctfd.yml` mounts that folder in the
  ctfd container, the `platform/plugins/ctf_theme` plugin serves it at
  `/ctf-theme/<file>`, and `platform/ctfd_admin.py` appends a `<link>`/`<script src>`
  per file (with `?v=<hash>`) to CTFd's `theme_header`/`theme_footer` inside
  `<!-- ai-modus -->` markers (idempotent; the backup's own `theme_header` is
  preserved). The files are not inlined: together they are over the 64 KB a config
  value holds in MariaDB. Disable with `CTF_AI_MODE=off ./ctf.sh up`.
- The AI challenges follow the meter's level (`platform/theme/README.md`, "The AI
  Slop-o-meter"): the challenge window adds `#fx=<level>` to a web challenge's link
  and puts the level's port in a terminal challenge's `nc` command
  (`TERMINAL_PORTS` in `ai-mode.js`). noter-ai, robot-ai, api-ai and viking-ai
  load one shared kit, `platform/theme/hosted-fx.css`/`.js` (served by `ctf_theme`,
  not linked into CTFd), from a small identical bootstrap at the top of each page's
  `<head>`; marvin-llm keeps its levels in its own templates (its MARVIN-GPT design
  is level 2); meow-ai and pwn-ai run one socat listener per level in the same
  container (`listen.sh`, `AI_FX=<level>`). A level never changes a challenge's
  responses, cookies or solve path, and pwn-ai's banner prints at once and never
  says "enter" (its exploit waits for that word).
- Two scoreboards: the CTFd plugin `platform/plugins/ai_brackets/` scores every
  team once per bracket (same rules as CTFd's `get_standings`; hint costs go to
  the hint's challenge's bracket) and serves `/ai-brackets/...` JSON endpoints;
  the stock scoreboard API is untouched. The Scoreboard page has All | Classic |
  AI-MODUS tabs (`ai-mode.js`; it opens on the selected lane's, `?board=all|normal|ai`
  picks one): `ai-mode.head.js` redirects the page's `/api/v1/scoreboard*` fetches to
  the plugin for the picked board. All (`bracket=all`) lists every team once per
  bracket it plays in, with that bracket's score and the lane after its name
  ("Team C (Klassisk)", "Team C (AI-MODUS)"), never the two added together.
  `ctf.sh up` copies the plugin into `.ctf/CTFd/CTFd/plugins/` (part of CTFd's
  build context, so `up -d --build` recreates CTFd when it changed) and removes
  it with `CTF_AI_MODE=off`. `__init__.py` only imports `scoring.py` and
  `siblings.py` inside `load()`, so an incompatible CTFd disables the plugin instead of failing to
  boot; the theme then shows the combined scoreboard, labelled as such. The big place/points
  on team pages, the admin panel and exports still show the combined total.
- First blood: the `platform/plugins/ctf_firstblood` plugin serves
  `/first-blood/feed` (each challenge's first solve by a visible account in the
  last 15 minutes, never after the freeze, plus a revision of the standings) and
  `platform/theme/first-blood.js`/`.css` announce it: a full-screen show on the
  Scoreboard page (sound and the voice `first-blood.mp3` only there, off until
  turned on in the control under the title, `localStorage` `ctf-fb-sound`), a
  banner on other pages, a stamp on the solver's own solve moment, and a refetch
  of the Scoreboard's table and graph when the revision changes
  (`ctfAiModus.refreshBoard`). Installed and linked with the theme, not in a
  preview; `ctf_theme` serves the mp3. Team and challenge names go in as
  `textContent` only. `tools/first-blood-voice.py` rebuilds the voice;
  `window.ctfFirstBlood.demo()` plays the show.
- AI challenges live in `challenges/ai/` and are harder siblings of originals
  following the normal contract:
  `julius-ai`, `mono-ai`, `operator-ai`, `rsa-ai`, `decode-ai`, `flagception-ai`,
  `git-ai` (static), and the hosted `robot-ai` + `noter-ai` + `api-ai` +
  `viking-ai` + `marvin-llm` (web, ports 5006/5007/5008/5009/5010) plus `pwn-ai`
  (nc 1246; 1247–1249 for the other meter levels) and `meow-ai` (nc 4446;
  4447–4449) — hosted ones have a `compose.yml` service +
  `platform/connections.txt` line. Categories in use: `ai-crypto`,
  `ai-forensics`, `ai-web`, `ai-pwn`, `ai-llm` (the marquee "attack the AI",
  `marvin-llm`). Their `metadata.yml` carries extra fields the auto-sync reads:
  `category:` (an `ai-…` value), `value:` (points), `builds_on:` (the CTFd names
  of the normal challenges whose technique it levels up, `[]` when none really
  does; kept in the CTFd config `ai_brackets_siblings` and served by the plugin
  at `/ai-brackets/siblings`, never as player-visible tags; the theme links each
  pair in the challenge windows only, the board shows nothing, and nothing is
  locked), `difficulty:` (1–5, the theme's threat
  rating, config `ai_brackets_difficulty`, served alongside the siblings), and
  `hints:` (a list of `"COST | text"` strings synced as paid CTFd hints; the
  plugin charges each cost in the challenge's own bracket).
- Like the normal challenges, they are **created automatically**:
  `ctf.sh` `apply_config` stages every challenge (it scans `challenges/*/*/`)
  whose `metadata.yml` `category` starts with `ai-`, copies it into the ctfd container, and
  `ctfd_admin.py sync_ai_challenges` creates/updates the CTFd challenge (name,
  category, description=`message`/`message_no`, `value`, a static case-insensitive `flag`,
  the sibling map, and `distfiles/` as attachments). Idempotent; repo is the source of truth (UI edits
  to these fields are overwritten on `up`), except value, state and extra flags, which
  follow metadata only when the challenge is created and after an import, so admin
  fixes made during the event survive an `up`. Full details in
  [docs/ai-mode.md](docs/ai-mode.md).

Adding another AI challenge needs no code change: create the folder in
`challenges/ai/` with a
`category: ai-…` in `metadata.yml` (plus `name`, `flag`, `message`, `message_no`,
`value`, `builds_on`, and optionally `difficulty` and `hints`/`hints_no`); it is auto-created in
CTFd and the lane control picks it up. For a hosted one, also add a
`compose.yml` service and a `platform/connections.txt` line.

## Content notes for the course

Current design considerations worth knowing when preparing the event:

- `overflow3` needs a subtle step (the terminating newline supplies a required
  `0x0A` byte); its `solution/README.md` explains it. It is noticeably harder
  than the overflows around it — consider hinting at it live.
- `marvin` and `noter2` both teach the `robots.txt` lesson and share the same flag
  string. CTFd scores each challenge separately (solving one does not mark the
  other), but the shared flag means a player who has the answer can submit it on
  either; marvin is `state: hidden` (and not started, profile `extra`), so
  normally only `noter2` is in play.
- `art` and `email` are OSINT tasks that depend on live third-party state (a news
  article; a GitHub account) with no local fallback — re-verify them before each
  event.
- `pdfcrypt` ships an AES-128 encrypted PDF; confirm the cracking path handles
  AES (not just RC4) before relying on the solution writeup.

## Notes

- `ctfd-backup/` holds the organiser's own CTFd exports and `backup --db` dumps,
  all optional. Everything in it but `README.md` is git-ignored: they hold
  participants' names, emails and password hashes. Without an export, `ctf.sh up`
  sets a new CTF up from the repo; with one, a new CTF imports the newest
  (`docs/local-setup.md`, "Starting from a CTFd export instead").

## Public repository

The repository is public, with its full contents (flags and writeups included).
Before committing, make sure a change adds no personal data (GDPR):

- no real people's names, usernames, emails or home-directory paths, in text, in
  file metadata (PDF/Office/EXIF) or in compiled binaries (a `-g` build records its
  build directory: build in a neutral path such as `/home/ctf/...`);
- no CTFd exports, database dumps or anything else with participants' data;
- nothing of a specific employer's or event's infrastructure: real hostnames,
  domains, IP addresses, tenant/subscription/app IDs, registration codes. Use
  `ctf.example.com` and `<placeholders>` in docs;
- fictional identities in challenge content (`Careless Dev <dev@corp.local>`,
  `dev@example.com`) and upstream credits to public CTF archives are fine.
- one deliberate exception: the `art` OSINT challenge's flag is the name of the
  street artist and the address a public magazine article credits them with; the
  owner chose to keep it.
