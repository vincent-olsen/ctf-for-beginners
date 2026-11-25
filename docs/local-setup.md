# Running the CTF locally

One command starts everything on your machine: CTFd with every challenge from the
repo, and every challenge container, with CTFd's connection info already pointing at
them.

```bash
./ctf.sh up
```

Then open <http://localhost> and log in as `admin`. The password is in
`.ctf/admin-password`. The first run takes a while (it downloads CTFd and builds
every challenge); later runs only rebuild what changed.

To play one challenge without CTFd, `./local.sh <challenge>` is enough (see the
[README](../README.md#how-to-run-a-single-challenge-locally)); the static
challenges are just the files in their `distfiles/`.

## Where CTFd's content comes from

Everything comes from the repo. On the first run CTFd is set up the way its own
setup page would do it: teams mode; the challenges, the scoreboard and the accounts
for logged-in players only; open registration (`--registration-code` closes it); no
email verification; the board ordered by category and points. Then every run syncs
from the repo:

| What | From |
|---|---|
| every challenge: name, category, points, flag (case-insensitive), the other spellings it accepts, description and hints in both languages, files | its `metadata.yml` and `distfiles/` (see [challenges/README.md](../challenges/README.md)) |
| the front page, the Info page, and the break, winners and podium pages (those three hidden until you show them) | [`platform/pages/`](../platform/pages/) |
| the event's name, logo and favicon | [`platform/theme/brand/`](../platform/theme/brand/) |
| the Classic / AI-MODUS theme and the plugins | [`platform/theme/`](../platform/theme/), [`platform/plugins/`](../platform/plugins/) |
| each hosted challenge's connection info | [`platform/connections.txt`](../platform/connections.txt) and `compose.yml` |
| the admin password | `.ctf/admin-password` (or `ADMIN_PASSWORD=...`) |

### Starting from a CTFd export instead

If `ctfd-backup/` holds a CTFd export (`<Name>.<YYYY-MM-DD_HH_MM_SS>.zip`, from
Admin → Config → Backup → Export, or `./ctf.sh backup`'s `local.…` renamed), the first run imports the
newest one instead of setting CTFd up; `--backup FILE` picks another. The export
then brings its own settings, pages and challenges: for a Classic challenge it
already has, its points, category, state, extra flags and files stay as the export
has them, and the repo writes the description, hints and a file of the same name.
Use it to carry an event's CTFd over to another machine. An export holds its
participants' names, emails and password hashes, so git ignores the folder
([ctfd-backup/README.md](../ctfd-backup/README.md)), and `--fresh` removes them on
import.

## Prerequisites

- **Docker Desktop** (or Docker Engine with the compose plugin) and **git**.
- **Apple Silicon only:** Docker Desktop → Settings → General → enable
  *Use Rosetta for x86_64/amd64 emulation on Apple Silicon*. The pwn binaries are
  x86-64, and viking builds with an x86_64 toolchain.
- Free ports: `80` (CTFd) plus the challenge ports in the table below.

## What `./ctf.sh up` does

1. Downloads CTFd 3.8.6 into `.ctf/CTFd/` (first run only).
2. Starts CTFd (CTFd, MariaDB, Redis) with a generated secret key.
3. Builds and starts every challenge in [`compose.yml`](../compose.yml). The first
   build takes several minutes; viking alone compiles Go under amd64 emulation.
4. On the first run, sets CTFd up and creates the admin account (or imports the
   newest export in `ctfd-backup/`, if there is one), with no start or end time and
   open registration unless you give `--event-start`, `--event-end`,
   `--registration-code`.
5. Sets the `admin` password, widens the challenge window to "Large" (CTFd's
   "Small" is too narrow for the flag field), sets the event's name,
   logo and favicon from `platform/theme/brand/` (`--brand` picks another
   folder, `--brand ""` none), writes each challenge's connection info from
   [`platform/connections.txt`](../platform/connections.txt), creates the
   challenges CTFd doesn't have yet and syncs every challenge's description and
   hints, and the pages
   ([`platform/pages/`](../platform/pages/)) in Norwegian and English (see
   [language.md](language.md)).
6. Starts nginx in front of CTFd, so CTFd is only reachable once it's configured,
   and the status page on <http://localhost:8081> (CTFd and every running challenge,
   checked once a minute; `--status off` leaves it out).

Running it again is safe. It rebuilds changed challenges, keeps CTFd's data, and
rewrites the connection info. It doesn't change a challenge's state, an AI-modus
challenge's points or the flags an admin added, so fixes made in the admin panel stay.
If CTFd is empty after it has been configured, it stops instead of starting a new
CTF over it (see `restore-db` below).

## Challenges and ports

Connection info is filled in automatically; this table is for reference.

Repo folders are under `challenges/normal/` (and `challenges/ai/` for AI-modus).

| CTFd challenge | Repo folder | Player connects with |
|---|---|---|
| meow1 – meow4 | `meow1` – `meow4` | `nc localhost 4441` – `4444` |
| overflow1 – overflow3 | `overflow1` – `overflow3` | `nc localhost 1241` – `1243` |
| binary *(hidden, not started)* | `overflow5` | `nc localhost 1245` |
| binary1, binary2 *(hidden, not started)* | `binary1`, `binary2` | `nc localhost 1231`, `1232` |
| overflow4(deprecated) *(hidden, not started)* | `overflow4` | `nc localhost 1244` |
| noter1 – noter4 | `noter1` – `noter4` | <http://localhost:5001> – `5004` |
| noter5 *(hidden, not started)* | `noter5` + `noter5-backend` | <http://localhost:1024> |
| marvin *(hidden, not started)* | `marvin` | <http://localhost:5005> |
| api1 – api3 | `api1` – `api3` | <http://localhost:5011> – `5013` |
| viking | `viking` | <http://localhost:8080> |
| meow-ai, pwn-ai | `meow-ai`, `pwn-ai` | `nc localhost 4446`, `1246` (effects level 2, the default; levels −1, 3 and 1 on `4447`–`4449` and `1247`–`1249`, same container) |
| robot-ai, noter-ai, api-ai | `robot-ai`, `noter-ai`, `api-ai` | <http://localhost:5006> – `5008` |
| viking-ai, marvin-llm | `viking-ai`, `marvin-llm` | <http://localhost:5009>, `5010` |

`platform/connections.txt` also hides `overflow4`, an older challenge that only
exists in exports from past events (its binary and flag aren't in this repo). The challenges marked
*not started* are in the `extra` profile in `compose.yml`: `ctf.sh up` neither starts
them nor shows them, and stops them if they still run. Run one with `./local.sh marvin`,
or `docker compose --profile extra up -d noter5`.

Challenges without a container (art, birds, decode1–3, email, flagception, git,
image, julius, mono, operator, pdfcrypt, qrcode, unk) only need their files, which
`ctf.sh` attaches from their `distfiles/`. `paper` needs a printout: its card is
`challenges/normal/paper/challenge/paper-flag.pdf`.

## Everyday commands

| Command | What it does |
|---|---|
| `./ctf.sh up` | start or update everything |
| `./ctf.sh status` | list running containers |
| `./ctf.sh down` | stop everything; CTFd data stays in `.ctf/CTFd/.data` |
| `./ctf.sh up --reimport` | wipe CTFd and start over: a new CTF from the repo (or the export again, if there is one) |
| `./ctf.sh backup` | export the running CTFd to `ctfd-backup/local.<timestamp>.zip` (git-ignored) |
| `./ctf.sh backup --db` | dump CTFd's database to `ctfd-backup/db/` (git-ignored; dumps older than 7 days are deleted) |
| `./ctf.sh restore-db [FILE]` | put such a dump back (the database as it is now is dumped first); without FILE it lists the dumps, newest first, and asks which one |
| `./ctf.sh logs noter4` | follow one service's logs (`ctfd`, `nginx`, `status`, or any challenge) |
| `./ctf.sh reset meow3` | recreate a challenge from its image, dropping whatever players changed in it |

## Options

| Option | Use it when |
|---|---|
| `--port 8000` | port 80 is taken on your machine (CTFd moves to <http://localhost:8000>) |
| `--backup "ctfd-backup/My CTF 2024.2024-05-16_19_31_12.zip"` | you start from a CTFd export, and not the newest in `ctfd-backup/` |
| `--host 192.168.1.20` | people on your network play too (see below) |
| `--fresh` | you import an export and want it without its players and solves (on the first run, or with `--reimport`) |
| `--registration-code CODE` | registration should require a code |
| `--preview julius,meow1` | only those challenges, playable without an account (flags checked, nothing saved), plus the containers they depend on (`noter5-backend` for `noter5`); a name CTFd doesn't know stops `up` with the board, the running challenges and the saved `--preview` unchanged; `--preview ""` brings everything back |
| `--lang no` | players should see Norwegian until they switch (the default is `en`, English; everyone can switch with NO \| EN in the navbar, see [language.md](language.md)) |
| `--event-start 2026-11-18T16:00+01:00 --event-end 2026-11-18T19:00+01:00` | CTFd should know the event's window (with the UTC offset; `--event-freeze` freezes the scoreboard, `""` clears one) |
| `--team-size 2` | teams have at most that many players |
| `--status off` | you don't want the status page |
| `ADMIN_PASSWORD=... ./ctf.sh up` | you want to choose the admin password |

`ctf.sh` remembers `--host`, `--port`, `--bind`, `--domain`, `--preview`, `--lang`,
the event's times and team size, `--status`, `CTF_AI_MODE` and the sign-in options in
`.ctf/settings.env`, so later runs reuse them. Microsoft sign-in
(`--sso-tenant`, `--sso-client-id`) works in hosted mode only; see
[azure.md](azure.md#a-preview-before-the-event).

### Letting others on your network play

By default, everything listens on `127.0.0.1` only. That keeps intentionally
vulnerable services off whatever Wi-Fi you're on. To open it up:

```bash
./ctf.sh up --host "$(ipconfig getifaddr en0)"
```

This publishes the ports on all interfaces and writes your current IP into the
connection info. When your IP changes, run the same command again. To go back to
local only, run `./ctf.sh up --host localhost`.

The meow challenges give every player a shell, and from that shell
`host.docker.internal` reaches the services running on your Mac. Only open it up
on a network whose people you trust.

## Troubleshooting

- **`Docker is not responding` / `500 Internal Server Error`**: Docker Desktop's VM
  has died. Run `docker desktop restart`.
- **`port is already allocated`**: something else holds that port. For CTFd, use
  `--port`. For a challenge, stop whatever uses it, or change the host port in
  `compose.yml`; the connection info follows automatically.
- **`exec format error` from a pwn challenge**: Rosetta emulation is off (see
  prerequisites).
- **`image ... does not provide the specified platform (linux/amd64)`**: your shell
  exports `DOCKER_DEFAULT_PLATFORM`. `ctf.sh` ignores it, since platforms are set
  per service in `compose.yml`; a plain `docker compose` in that shell still uses it.
- **Import failed** (starting from an export): rerun with `./ctf.sh up --reimport`
  and read the import output. Only exports from CTFd 3.x are supported.
- **Wrong challenge on a port after editing `compose.yml`**: run `./ctf.sh up`
  again so the connection info is rewritten.

## Moving over from a manual setup

If you started challenges by hand (`ctf-<name>` containers) or run CTFd from
another folder, stop those first so the ports are free:

The name filter below matches only the hand-started `ctf-<challenge>` containers,
not the `ctf-platform-*` and `ctf-challenges-*` containers that `ctf.sh` creates:

```bash
docker ps -aq --filter name='^/?ctf-(meow[1-4]|binary[12]|overflow[1-5]|noter[1-5]|noter5-backend|marvin|api[1-3]|viking)$' | xargs docker rm -f
```

```bash
docker network rm ctf-noter5
```

```bash
docker compose -f /path/to/your/CTFd/docker-compose.yml down
```

If you edited `challenges/normal/noter5/challenge/app.py` or `init.py` to point at a local backend,
discard those edits. Both read `BACKEND_URL` / `PROXY_URL` from the environment and
default to the Compose setup:

```bash
git checkout -- challenges/normal/noter5/challenge/app.py challenges/normal/noter5/challenge/init.py
```

## Files

| Path | Purpose |
|---|---|
| `ctf.sh` | the orchestrator |
| `challenges/normal/`, `challenges/ai/` | one folder per challenge, see [challenges/README.md](../challenges/README.md) |
| `compose.yml` | all challenge containers and their host ports |
| `.env` | written by `ctf.sh`: the bind address, so plain `docker compose` uses it too (git-ignored) |
| `platform/connections.txt` | CTFd challenge name → service, port and connection template |
| `platform/ctfd.yml` | CTFd override: secret key, bind address, HTTP port |
| `platform/ctfd.hosted.yml`, `platform/Caddyfile` | hosted mode, see [hosting.md](hosting.md) |
| `platform/ctfd_admin.py` | configures CTFd from inside its container |
| `.ctf/` | local state: CTFd source and data, secret key, admin password (git-ignored) |
