# Challenges

One folder per challenge, split by bracket:

- [`normal/`](normal/) — the regular CTF (no AI, honour system).
- [`ai/`](ai/) — the AI-modus bracket: harder `*-ai` siblings of the normal
  challenges, auto-created in CTFd from their `metadata.yml` (see
  [docs/ai-mode.md](../docs/ai-mode.md)).

The folder name is the challenge's identity everywhere else: the `compose.yml`
service and the `./local.sh <name>` argument. Keep names unique across both
brackets: `local.sh` and `ctf.sh` refuse a name that exists in both, and ignore
any `metadata.yml` that is not exactly at `challenges/<group>/<name>/` (`ctf.sh up`
warns about it).

Every challenge follows the same layout:

| Path | Contents |
|---|---|
| `challenge/` | everything needed to build the asset; for hosted challenges a `Dockerfile` with an `EXPOSE` line. The real flag lives here. |
| `distfiles/` | what the player downloads in CTFd (`.keep` when empty). Never the answer. |
| `solution/` | a working exploit and/or a writeup. The writeup has a **Debrief** section: what the player learns, the solve in short, and how to protect against it. |
| `metadata.yml` | `flag`, `category`, `value` (points), player-facing `message` (English) and `message_no` (Norwegian), paid `hints` / `hints_no`, internal `notes`; optional `extra_flags` (other spellings accepted), `state` (`hidden` keeps a challenge off the board), `name` (when the CTFd name differs from the folder), `max_solves`, `credits`; AI challenges use an `ai-…` category and add `builds_on` (the normal challenges they level up) and `difficulty` |

`./ctf.sh up` creates every challenge CTFd doesn't have yet from its `metadata.yml`:
its name, category, points, state, flag and `extra_flags` (all case-insensitive),
and its `distfiles/` as downloads. On every run it writes each challenge's `message`
and `message_no` into its CTFd description (a multi-line Markdown message goes in a
`message: |` block), and its `hints` and `hints_no` into its hints, a block per
language that players switch between with NO | EN in the navbar (see
[docs/language.md](../docs/language.md)). A hint can only be unlocked after the
challenge's cheaper ones; hints of the same cost in any order. It matches the CTFd
challenge by `name`, else the folder name, so a challenge whose CTFd name differs
sets `name` (`qrcode` is `qr`, `overflow5` is `binary`). Points, state and extra
flags are only set when a challenge is created, so changes made in the admin panel
during an event stay.

Hosted challenges also need a service in [`compose.yml`](../compose.yml) and a
line in [`platform/connections.txt`](../platform/connections.txt).

`max_solves: N` (either bracket) locks a challenge once N teams have solved it: the
`ctf_solve_limit` plugin refuses later flags, and the board marks it as locked
with the name of the team that found it.

## Normal

| Family | Challenges | Type |
|---|---|---|
| Terminal | `meow1`–`meow4` | hosted (nc) |
| Pwn (published) | `overflow1`–`overflow3` | hosted (nc) |
| Pwn (hidden, ready to release) | `overflow5` (CTFd name `binary`) | hosted (nc) |
| Pwn (hidden, retired) | `binary1`, `binary2`, `overflow4` (CTFd name `overflow4(deprecated)`) | hosted (nc) |
| Web | `noter1`–`noter4`, `marvin`, `viking` | hosted (http) |
| Web (two services) | `noter5` + `noter5-backend` (infrastructure, no flag) | hosted (http) |
| API | `api1`–`api3` | hosted (http) |
| Crypto / encoding | `julius`, `mono`, `operator`, `birds`, `flagception`, `decode1`–`decode3` | static |
| Forensics | `git`, `image`, `unk`, `pdfcrypt` | static |
| Misc | `qrcode` | static |
| Physical | `paper` (a flag printed on a card and hidden in the venue; one solve only) | not hosted, nothing attached |
| OSINT | `art`, `email` | static |

Families are for orientation; each `metadata.yml` `category` is the CTFd
category. The published pwn track is `overflow1`–`overflow3`. The other pwn
challenges were hidden at the last event: `binary1`/`binary2` are retired (superseded
by the overflows), `overflow4` is deprecated, and `overflow5` (CTFd name `binary`)
is kept ready to release during an event if wanted. They, plus `noter5` and
`marvin`, sit in the `extra` profile in `compose.yml` and carry
`state: hidden`, and `platform/connections.txt` marks them `hidden` (which hides
them in CTFd on every `./ctf.sh up`). See
[docs/local-setup.md](../docs/local-setup.md) for what players see.

## AI-modus

| Challenge | Builds on (`builds_on`) | Category | Type |
|---|---|---|---|
| `julius-ai` | `julius` | `ai-crypto` | static |
| `mono-ai` | `mono` | `ai-crypto` | static |
| `operator-ai` | `operator` | `ai-crypto` | static |
| `rsa-ai` | (new) | `ai-crypto` | static |
| `decode-ai` | `decode1`–`decode3` | `ai-crypto` | static |
| `flagception-ai` | `image` | `ai-forensics` | static |
| `git-ai` | `git` | `ai-forensics` | static |
| `robot-ai` | `marvin`, `noter2`, `noter3` | `ai-web` | hosted (http) |
| `noter-ai` | `noter4` | `ai-web` | hosted (http) |
| `api-ai` | `api1`–`api3` | `ai-web` | hosted (http) |
| `viking-ai` | `viking` | `ai-web` | hosted (http) |
| `pwn-ai` | `binary` | `ai-pwn` | hosted (nc) |
| `meow-ai` | `meow4` | `ai-pwn` | hosted (nc) |
| `marvin-llm` | (new) | `ai-llm` | hosted (http) |
