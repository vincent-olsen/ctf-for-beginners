# CTF for n00bs

A beginner-friendly Capture The Flag: about 50 small hacking challenges for an
"intro to ethical hacking" afternoon, with a writeup for every one of them, and the
tooling to run the whole event on [CTFd](https://ctfd.io/) with one command.

It has two brackets in one CTF. **Classic** teaches one idea per challenge (no AI,
honour system); **AI-modus** repeats those ideas at a much harder level and expects
players to bring an AI assistant.

> **Spoilers.** The flags and the solutions are in this repository. Try a challenge
> before you read its `solution/`.

## Quick start: the whole CTF

You need **Docker** (Docker Desktop, or Docker Engine with the compose plugin) and
**git**. On Apple Silicon, also turn on Docker Desktop → Settings → General →
*Use Rosetta for x86_64/amd64 emulation*: the pwn challenges are x86-64.

```bash
git clone https://github.com/vincent-olsen/ctf-for-beginners.git
```

```bash
cd ctf-for-beginners && ./ctf.sh up
```

The first run takes a while: it downloads CTFd and builds every challenge. Then open
<http://localhost>, and log in as `admin` with the password in `.ctf/admin-password`.
Every challenge, page and setting comes from the repo; nothing to click together in
the admin panel. Players register on the site and play in teams.

| | |
|---|---|
| `./ctf.sh up` | start, or update after a change (safe to rerun; keeps CTFd's data) |
| `./ctf.sh down` | stop everything (the data stays in `.ctf/`) |
| `./ctf.sh status` | what's running |
| `./ctf.sh up --reimport` | wipe CTFd and start a new CTF |
| `./ctf.sh up --port 8000` | port 80 is taken |
| `./ctf.sh --help` | everything else: registration code, event times, team size, language, preview |

More in [docs/local-setup.md](docs/local-setup.md): the ports, letting others on
your network play, troubleshooting.

## Play a single challenge

No CTFd needed: one challenge in a container.

```bash
./local.sh meow1
```

A bare name (e.g. `meow1`, `robot-ai`) is looked up in `challenges/normal/` and
`challenges/ai/`; a path to a challenge folder is used as given. The port is the one
`compose.yml` gives the challenge (meow1 on 4441, so `nc localhost 4441`), and the
challenge's `metadata.yml` has its description. The static challenges (julius,
mono, git, ...) need no container: their files are in `distfiles/`. On Apple
Silicon, prefix it with `DOCKER_DEFAULT_PLATFORM=linux/amd64` for the pwn
challenges and viking.

## Writeups

- [writeup/writeup.pdf](writeup/writeup.pdf): every challenge, step by step, with
  what you learn and how to defend against it. Built from
  [writeup.md](writeup/writeup.md) with `writeup/build.sh` (pandoc and LaTeX).
- `challenges/*/<name>/solution/`: each challenge's own writeup and working
  exploit, with a *Debrief* section.

## Repo layout

```
challenges/
  normal/      the Classic challenges (meow1, noter1, overflow1, julius, ...)
  ai/          the AI-modus bracket (*-ai siblings)
writeup/       the players' writeup of every challenge: writeup.md -> writeup.pdf
platform/      CTFd config, connection info, the theme and plugins, the front
               and Info pages, and the Azure template (platform/azure/)
docs/          running, hosting and AI-modus guides
ctfd-backup/   CTFd exports and database dumps you take (git-ignored, see its README)
tools/         challenge lookup and checks; tools/pwn/ is exploit scratch, not a challenge
ctf.sh         run the whole CTF
azure.sh       run it on an Azure VM (docs/azure.md)
compose.yml    every hosted challenge and its host port
local.sh       run one challenge
```

See [challenges/README.md](challenges/README.md) for the challenge list and the
folder contract every challenge follows.

## Running an event

- [docs/local-setup.md](docs/local-setup.md) - running it on your machine, also for
  players on the same network
- [docs/hosting.md](docs/hosting.md) - on a server with a domain and HTTPS:
  `./ctf.sh up --domain ctf.example.com`
- [docs/azure.md](docs/azure.md) - on an Azure VM with `./azure.sh up`:
  short-lived test and event deployments
- [platform/pages/info.md](platform/pages/info.md) - the players' Info page (and
  [info.no.md](platform/pages/info.no.md) in Norwegian): fill in your event's time,
  agenda and contact before it starts

The flags are public here, so for an event where that matters, change them in a
private copy first (each challenge's `metadata.yml` and the flag in its
`challenge/`; `tools/check-flags.py` checks that they agree).

## AI-modus (two brackets in one CTF)

A navbar lane control (**Classic | AI-MODUS**) splits the event into two brackets that share one
CTFd: the **normal** challenges (no-AI, honour system) and a **much harder**
AI-modus set that echoes the originals and expects AI. Each bracket has its own
scoreboard, and a team scores in both. Classic is a calm blue skin; switching to AI-modus
turns the site into a burning retro-hacker terminal. It's set up automatically by `ctf.sh` — nothing
to configure in the admin panel.

- [docs/ai-mode.md](docs/ai-mode.md) - the concept, the AI challenges (in
  `challenges/ai/`), and how `ctf.sh` creates them in CTFd
- [docs/ai-difficulty-tuning.md](docs/ai-difficulty-tuning.md) - how hard the AI
  challenges are for an AI, and how they were tuned
- [platform/theme/](platform/theme/README.md) - the lane control + skin source
- [platform/plugins/ai_brackets/](platform/plugins/ai_brackets/__init__.py) - the
  CTFd plugin that scores each bracket separately

Turn it off with `CTF_AI_MODE=off ./ctf.sh up`.

## Languages

Everything players see is in English and Norwegian, switched with **NO | EN** in the
navbar. Challenge texts are `message`/`message_no` in each `metadata.yml`; see
[docs/language.md](docs/language.md).

## How to add a challenge

`ctf.sh up` builds every challenge from the repo and creates it in CTFd — there is
no registry to push to and no admin-panel clicking. Follow the folder contract in
[challenges/README.md](challenges/README.md):

1. Create `challenges/normal/<name>/` (or `challenges/ai/<name>/` for an AI-modus
   one) with `challenge/`, `distfiles/`, `solution/` and `metadata.yml`: `flag`,
   `category`, `value` (points), English `message` and Norwegian `message_no`, and
   optionally `hints`/`hints_no` and `extra_flags` (other accepted spellings).
   AI-modus ones use an `ai-…` category and add `builds_on`. Keep the real flag out
   of `distfiles/`.

2. For a **hosted** challenge, give the `Dockerfile` an `EXPOSE` line, add a service
   with an unused host port to [compose.yml](compose.yml), and a line to
   [platform/connections.txt](platform/connections.txt).

3. Run `./ctf.sh up`. It builds the image, creates the challenge in CTFd with its
   flag (case-insensitive), description, hints and `distfiles/`, and fills in the
   connection info. Later runs keep its description and hints in step with
   `metadata.yml`. See [docs/language.md](docs/language.md) and
   [docs/ai-mode.md](docs/ai-mode.md).

On Azure, `./azure.sh up` (or `deploy`) copies the repo to the VM, runs `ctf.sh`
there, and opens the new host port in the NSG.

## License and credits

The code, challenges and writeups in this repository are released under the
[MIT License](LICENSE), apart from third-party material, which stays with its
owners:

- Several Classic challenges are adapted from other CTFs: BSidesSF CTF 2023, and
  ALLES! CTF 2021 and 1337UP CTF 2023 by way of
  [sajjadium/ctf-archives](https://github.com/sajjadium/ctf-archives). Each one's
  `metadata.yml` names its source under `credits:`; the original challenges
  remain their authors' work.
- Some challenge files show other people's work, such as the street art and the
  Street View screenshot in `art` and the painting in `pdfcrypt`.
- [CTFd](https://github.com/CTFd/CTFd), which `ctf.sh` downloads, is Apache 2.0.
