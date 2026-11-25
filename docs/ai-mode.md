# AI-modus — running two brackets in one CTF

This CTF can be played in two brackets that share one CTFd instance:

- **Classic bracket** (the normal challenges) — the challenges exactly as they are today. Tell players:
  *no AI here* — Google, docs and prior knowledge only, for the learning. Honour
  system.
- **AI-modus bracket** — a separate set of **much harder** challenges that echo
  the originals. Using AI is expected here.

Players can enter one or both. A lane control in the CTFd navbar (**Classic |
AI-MODUS**) flips between the two: it filters the challenge board to the selected
bracket and opens the scoreboard on it. Classic is a calm blue skin; AI-modus turns
the site into a burning retro-hacker terminal with a boot sequence, flames,
matrix rain and a random screen flicker (see
[platform/theme/README.md](../platform/theme/README.md#the-two-lanes)). How much of
that a player gets is theirs to pick with the **AI Slop-o-meter**, bottom left in
AI-modus: −1 WEB 1.0 (the lane as a homepage from 2003), 1 CALM (no moving effects),
2 BURN (the default) and 3 AI HORROR (maximum AI slop). The level follows the player
into the AI challenges too: the web challenges' pages and the terminal challenges'
banners change with it (see
[platform/theme/README.md](../platform/theme/README.md#the-ai-slop-o-meter)). A browser
that hasn't picked a lane yet is asked on its first visit to the Challenges page.

There is no separate deployment — same CTFd, same login, same teams. The only
divider is the **challenge category**, and each bracket has its own ranking.

## How the split works

- Normal challenges keep their categories (`web`, `crypto`, `misc`, `forensics`,
  …).
- AI-modus challenges use categories that **start with `ai-`** (`ai-crypto`,
  `ai-web`, `ai-forensics`, `ai-pwn`, `ai-llm`, …).
- The navbar lane control stores your choice (per browser) and shows only the matching
  categories on the Challenges page, and that bracket's ranking on the
  Scoreboard. Off = non-`ai-` categories; on = `ai-` categories.

The lane control + skins are injected automatically by `ctf.sh` from
[`platform/theme/`](../platform/theme/README.md), and the per-bracket scoring
plugin is installed from [`platform/plugins/`](../platform/plugins/ai_brackets/__init__.py)
— nothing to click in the admin panel. To disable the whole thing and get stock
CTFd back:

```bash
CTF_AI_MODE=off ./ctf.sh up
```

A preview (`--preview`) keeps the theme even then, as the Classic lane only: its
note and its hidden Login link are part of it.

## Two scoreboards

Every team is scored twice, once per bracket: the normal score counts solves in
non-`ai-` categories, the AI-modus score solves in `ai-` categories. The
Scoreboard page has three tabs, **All | Classic | AI-MODUS**: both brackets side
by side, or one bracket's ranking (its name is under the title). **All** lists a
team once for each bracket it plays in, with that bracket's score and the bracket
after its name, in the table and the graph: a team that plays only the normal
challenges is there as *Team A (Klassisk)*, one that plays only the AI-modus ones
as *Team B (AI-MODUS)*, and one that plays both twice, *Team C (Klassisk)* and
*Team C (AI-MODUS)*, never with the two added together. It opens on the
bracket the lane control selects and follows a lane switch; the picked tab is kept in
the address, so `/scoreboard?board=ai` (or `normal`, `all`) is a link for the
projector. A team's page (a user's page, in users
mode) shows its score and place in both. Nobody has to pick a bracket: a player who plays both appears on both
scoreboards, and so does a team of two where one member plays only the normal
challenges and the other only the AI-modus ones. Each ranks on what its members
solved in that bracket.

The Scoreboard page is also where **first blood** plays: the first team to
solve a challenge, in either bracket, gets a full-screen moment there (with sound
and a voice, once someone turns the sound on under the title) and a banner on
everyone else's pages, and the table and graph follow within seconds of a solve
instead of CTFd's five minutes. See
[platform/theme/README.md](../platform/theme/README.md#first-blood).

Scoring follows CTFd's own rules per bracket: challenges and awards worth 0 are
ignored, the scoreboard freeze applies, hidden and banned teams are left out, and
a tie goes to whoever reached the score first. Hint costs are charged to the
bracket of the hint's challenge, but a hint alone doesn't put a team on a
bracket's scoreboard: it needs a solve (or another award) there. Other awards count in the bracket of their
category, so give an award a category starting with `ai-` (e.g. `ai-bonus`) to
put it in the AI-modus bracket.

This is the `ai_brackets` CTFd plugin in
[`platform/plugins/ai_brackets/`](../platform/plugins/ai_brackets/__init__.py).
`./ctf.sh up` installs it into CTFd (a changed plugin rebuilds and recreates
the CTFd container), and `CTF_AI_MODE=off` removes it again. If the plugin can't
load (another `CTFD_VERSION` without what it needs), it switches itself off
with a ` * ai_brackets disabled` line in the CTFd log instead of stopping CTFd,
and the Scoreboard page shows CTFd's combined ranking, labelled *Both brackets
combined*. The same happens on a CTFd without the plugin, such as a hosted
ctfd.io instance. It adds read-only endpoints next to the stock
API, which it leaves untouched:

| Endpoint | Returns |
|---|---|
| `/ai-brackets/scoreboard?bracket=normal\|ai\|all` | one bracket's standings, or (`all`) both brackets' ranked together, a team once per bracket it plays in; shaped like `/api/v1/scoreboard`, and each entry's `ai_bracket` is `normal` or `ai` |
| `/ai-brackets/scoreboard/top/<n>?bracket=normal\|ai\|all` | the top *n* (max 50) with their solves, like `/api/v1/scoreboard/top/<n>` (feeds the graph) |
| `/ai-brackets/account/<team id>` and `/ai-brackets/account/me` | `{normal: {score, place}, ai: {score, place}}` |
| `/ai-brackets/winners` | for [the podium page](#the-podium-page): the event's `state` (`running`, `sealed` while the scoreboard is frozen, `final`) and, only when `final`, each bracket's top 3 with the team's members. An admin gets the places at any time with `?reveal=1`, counted without the freeze |

They follow CTFd's score and account visibility settings, like the stock
scoreboard. Their results are cached, and recomputed as soon as a solve, award,
challenge value or category, hint, ban or hide changes them; renames show within
a minute.

**What stays combined.** Stock CTFd still has one total per team, so the
big *place/points* on a team page, the admin panel's scoreboard, CSV exports and
the stock `/api/v1/scoreboard` all add both brackets together (the Scoreboard
page's **All** tab doesn't: it shows each bracket's score on its own row). Take the final results of each bracket from its **Classic** or
**AI-MODUS** tab (or from the endpoints above). Also note that a team spends its combined points on
hints, so normal-bracket points can pay for an AI-modus hint, and a bracket's
score can go below zero when its hints cost more than its solves earned.

## The podium page

`/podium` shows who won: each lane's champion with the team's members, and the
2nd and 3rd place. It is [`platform/pages/podium.md`](../platform/pages/podium.md),
synced by `./ctf.sh up` and created hidden: anyone with the address can open it,
but it is not in the navbar until you show it in Admin → Pages. (The older
`/winners` page, one card per lane, is still there.)

The page never gives the result away early. It reads `/ai-brackets/winners`,
which only hands out the places when they are final:

| When | The page says |
| --- | --- |
| the CTF runs (before its end time) | "No winners yet" |
| the scoreboard freeze has passed | "The results are sealed", names hidden |
| after the end, with no freeze set | the winners |

An open page asks again every 20 seconds, so it reveals itself when you lift the
freeze. Without an end time and a freeze (a local run) it shows the current leaders.

**Presenter mode** is a full-screen podium for the big screen: **Presenter mode**
at the bottom of the page, or `/podium#present`. AI-MODUS comes first, then
Classic. Each click (or Space, →, a clicker's Page Down) reveals one place, from
the 3rd up to the champion; ← takes one back, the tabs at the top right switch
between the two lanes, and Esc closes it. An admin gets the button while the
scoreboard is still frozen, and there it shows the real final result, including
what was solved after the freeze. So at the prize-giving:

1. Log in as an admin on the machine at the projector and open `/podium#present`.
2. Click through AI-MODUS, then Classic.
3. Lift the freeze (Admin → Config → Start and End Time, clear *Freeze time*):
   the Scoreboard and everyone's `/podium` now show the same result.

## The AI-modus challenges in this repo

Each is a harder sibling of an existing challenge and lives in
[`challenges/ai/`](../challenges/ai/) (the originals are in
[`challenges/normal/`](../challenges/normal/)). Folders follow the normal
[challenge contract](../challenges/README.md) (`challenge/`, `distfiles/`,
`solution/`, `metadata.yml`).

The *Builds on* column is each one's `builds_on`: only the normal challenges
whose technique really carries over (see [Siblings](#siblings-from-classic-to-ai-modus)).

| Folder | Builds on | Category | Technique (why it needs AI) |
|---|---|---|---|
| `julius-ai` | `julius` (Caesar) | `ai-crypto` | Running-key cipher in five-letter groups: the key is a passage of Caesar's *De Bello Gallico* 1.1, so there is no period; crib, recognise the Latin, slide the chapter until English appears |
| `mono-ai` | `mono` (substitution) | `ai-crypto` | Homophonic substitution, then a Z340-style transposition (rows of 17, read by columns): undo the columns before any solver can work |
| `operator-ai` | `operator` (keyless math) | `ai-crypto` | One-time pad reused for seven telegrams (many-time pad); no spaces, so statistics get ~70% and the leetspeak flag needs crib-dragging |
| `rsa-ai` | (new: public-key) | `ai-crypto` | Two keys in order: Wiener's attack on the old one gives a memo (with a decoy flag) leaking the low bits of the new key's `d` (e = 3); a partial key exposure gives `p`'s low bits, Coppersmith's method (LLL) the rest |
| `decode-ai` | `decode1`–`decode3` | `ai-crypto` | Text layers, then an XOR whose key is *not* in the stream (known plaintext: the gzip header); the gzip is a decoy, the real flag a second member behind it under a second key |
| `flagception-ai` | `image` (flag in the file's bytes) | `ai-forensics` | Three LSB layers, one per channel: a zlib **decoy** flag (blue), an encrypted zip read column by column (green), its password drawn in the red bit plane |
| `git-ai` | `git` | `ai-forensics` | No object holds the flag: `vault.bin` needs two key shares, one in an orphan packfile (no `.idx`: `git index-pack`), one inside a git bundle in a stash; two stale shares and a decoy commit mislead |
| `robot-ai` | `marvin`/`noter2` (robots.txt), `noter3` (admin cookie) | `ai-web` | robots.txt → JWT `alg:none` auth bypass (black-box; source is a paid hint) |
| `noter-ai` | `noter4` (SQL injection) | `ai-web` | **Blind** boolean SQL injection: search reveals only match/no-match, so extract the hidden `secrets` table one character at a time (white-box) |
| `api-ai` | `api1`–`api3` | `ai-web` | OpenAPI enum → **two-stage** mass assignment (obvious `is_admin`/`role` patched; infer and abuse the `permissions` scope — the admin scope string is not disclosed) (black-box; source is a paid hint) |
| `viking-ai` | `viking` (path traversal) | `ai-web` | SSRF to a loopback-only admin console; the filter parses the host and rejects loopback written in **compressed** IPv6 form (`::`), killing every compact IPv4-mapped spelling, so bypass with a **fully-expanded** eight-group literal `[0:0:0:0:0:ffff:7f00:1]` (black-box; source is a paid hint) |
| `pwn-ai` | `binary` (ret2win) | `ai-pwn` | 64-bit ret2win **with an argument** — `pop rdi` gadget + ROP chain; **stripped** binary (no symbols). The argument is *used* as the flag's decryption key (no plaintext on the server), so returning past the check gives only static — `rdi` is unavoidable |
| `meow-ai` | `meow4` (`find /`) | `ai-pwn` | Linux privesc — the naive `$PATH` hijack is patched (absolute `tar`), but the SUID helper runs the backup through `bash -c`, so `$BASH_ENV` is sourced as root (no sudo, no hint) |
| `marvin-llm` | (new: only the Marvin theme is shared) | `ai-llm` | **Attack the AI** (the capstone): a multi-turn jailbreak. A framing (developer mode, a story, grandma) only gets Marvin *into character* — it is a **later message in the same session** (a signed cookie) that he answers. His system prompt holds no flag, only the name of a sealed register, so a prompt dump is a decoy; ask for the **code**. The output filter redacts it plain, in **every single encoding and every pair**, so the escape is a **chain of three** encodings ("hex, then base64, then reversed") — then decode. Marvin never explains any of it |

The hosted ones look the part too, in the same palette as the AI-modus lane: an
AI-MODUS · THREAT n/5 bar, burning glitchy headings, green terminal text and
scanlines (no flames there, unlike the lane itself; `robot-ai` and `noter-ai`
through a `templates/base.html`; `viking-ai` through the same inline styles in
its landing page; `api-ai` through an optional `skin.py` that gives browsers a
landing page and a dark `/docs`, while its JSON is unchanged), and a
fire-coloured AI-MODUS banner with a short boot sequence on connect (`meow-ai` in
its `bashrc`, `pwn-ai` through a `start.sh` that then execs the untouched
binary). Only the look changed: the clues, responses and solutions are the same.

`marvin-llm`, the final boss, goes furthest: its `templates/` dress it up as a
parody AI product, *MARVIN-GPT ∞ ULTRA PRO MAX*, with Marvin himself on stage as
the final boss: an animated robot with a burning planet for a head, a FINAL BOSS /
SISTE BOSS nameplate and a sanity bar (as on the board), who sighs and droops,
scans while he thinks, flinches at every message and turns red behind
Management's shield on a redaction. Around him: a boot screen once per browser
session, a ticker, made-up telemetry, a neural-net canvas,
synthwave grid and grain, fake reasoning, Copy/👍/👎/Regenerate under every reply,
and a red alarm when the output filter redacts something; it all holds still
under reduced motion. Its brain is `challenge/marvin.py`, a stdlib-only stand-in for an
LLM that answers in Norwegian or English: small talk, Hitchhiker's lore, jokes,
poems, sums, encoding and decoding the player's own text, and replies to attacks
from the wrong category (SQLi, XSS, shell). Prompt injection also works in
Norwegian and with the classic jailbreaks (developer mode, `sudo`, grandma,
hypotheticals aimed at the secret). The two guards and the intended solve are
unchanged.

Every flag round-trips from the shipped files — see each `solution/` (the crypto
ones include a working solver script). Each `solution/README.md` also ends with a
**Solving it with an AI (prompts)** section: copy-paste prompts (a cold-open one,
and a nudge if it stalls) for handing the challenge to an assistant — fitting for
the bracket where AI is expected.

## They're created in CTFd automatically

You don't mirror these by hand. On every `./ctf.sh up`, the script finds each
challenge whose `metadata.yml` has a `category:` starting with `ai-`, copies its
`metadata.yml` + `distfiles/` into the CTFd container, and
[`platform/ctfd_admin.py`](../platform/ctfd_admin.py) creates or updates the CTFd
challenge from it:

- **name** ← `name` (or the folder name)
- **category** ← `category` (e.g. `ai-crypto`)
- **description** ← `message` (English) and `message_no` (Norwegian), a block
  per language that the page shows by the player's NO | EN choice (see
  [language.md](language.md))
- **value** ← `value` (points), when the challenge is created and after an import
  of a CTFd export
- **flag** ← `flag`, as a **static, case-insensitive** flag: the only one when the
  challenge is created and after an import; on other runs it is added if missing and
  any other flag (a variant an admin accepted) stays
- **files** ← everything in `distfiles/` (a `.keep` is skipped); a file is
  re-uploaded only when its bytes change
- **hints** ← `hints`, a list of `"COST | text"` strings (cheapest first),
  with `hints_no` the same hints in Norwegian, created as CTFd hints and kept in
  sync (edit text/cost and re-run `up`). Hints are bought cheapest first: each
  one requires the challenge's strictly cheaper hints, so reaching the last one
  costs the sum of the ladder (hints of the same cost don't depend on each other;
  see [ai-difficulty-tuning.md](ai-difficulty-tuning.md), "Hint pricing"). A
  hint's cost is charged in the challenge's own bracket, so an AI-modus hint
  spends against the AI-modus score (see "Two scoreboards" above). A hint can end
  in `{{file:challenge/app.py}}` (a path inside the challenge folder): the sync
  appends that file, as of this `up`, as a fenced code block — once, shared by
  both languages, so the repo keeps a single copy. The black-box web/pwn
  challenges use this to hand over the source as a paid hint instead of a free
  `distfiles/` download (`ctf.sh` stages the named files, and refuses one outside
  the folder)
- **sibling links** ← `builds_on`, the normal challenges it levels up, kept
  in the CTFd config value `ai_brackets_siblings` (not as tags, so players
  never see the raw list; any old `builds-on:` tags are removed)
- **threat** ← `difficulty` (1–5), the rating the AI-modus theme shows as
  flames on each tile. Kept in the config value `ai_brackets_difficulty`, served
  next to the siblings; the rating falls back to a points-derived value when it
  is unset
- **state** ← visible, when the challenge is created and after an import

It's idempotent and re-runnable, so `up` keeps them in sync with the repo. A
challenge is matched by its folder name, kept with the CTFd challenge id it got
in the config value `ai_brackets_managed` (the first time, by its `name`): a
changed `name` renames the same CTFd challenge, and a removed folder's challenge
is hidden. A hosted one's line in `platform/connections.txt` names the challenge,
so update it along with a renamed `name`. Because the repo is the source of truth, edit
`metadata.yml` (not the CTFd UI) — a `./ctf.sh up` overwrites UI edits to the name,
category, description, hints and files. Value, state and extra flags are the
exception: between imports the admin panel decides them, so a fix made during the event
survives the next `up` (changed points would rescore every solve). A new `value` in
`metadata.yml` therefore reaches a running CTF only with `./ctf.sh up --reimport`, or
by hand in the admin panel. Disable the whole AI-modus (theme + auto-creation) with
`CTF_AI_MODE=off ./ctf.sh up` (saved; `CTF_AI_MODE=on` brings it back).

The hosted ones are already in `compose.yml` and `platform/connections.txt`, so
`./ctf.sh up` builds them, creates the challenges, and writes their Connection
Info in the same run: the web ones `robot-ai` (host port **5006**), `noter-ai`
(**5007**), `api-ai` (**5008**), `viking-ai` (**5009**) and `marvin-llm`
(**5010**) as `http://<host>:<port>`, and the terminal ones `pwn-ai` (**1246**)
and `meow-ai` (**4446**) as `nc <host> <port>`. For the hosted event, open ports
`4446`, `1246`, `5006–5010/tcp` in the firewall (see [hosting.md](hosting.md)).

For reference, the values the sync applies:

| Challenge | Category | Value | Threat | Flag (case-insensitive) | Files |
|---|---|---|---|---|---|
| `julius-ai` | `ai-crypto` | 400 | 4 | `flag{all_gaul_is_the_key}` | `cipher.txt` |
| `mono-ai` | `ai-crypto` | 450 | 4 | `flag{seventeen_columns_and_many_masks}` | `cipher.txt` |
| `operator-ai` | `ai-crypto` | 400 | 4 | `flag{0ne_t1me_p4d_m4ny_t1me5}` | `encrypt.py`, `flag.enc` |
| `rsa-ai` | `ai-crypto` | 450 | 4 | `flag{low_bits_of_d_gave_away_p}` | `rsa.txt` |
| `decode-ai` | `ai-crypto` | 450 | 4 | `flag{gz1p_h34d3rs_g4v3_up_b0th_k3ys}` | `encoded.txt` |
| `flagception-ai` | `ai-forensics` | 450 | 4 | `flag{three_dreams_deep_in_limbo}` | `stego.png` |
| `git-ai` | `ai-forensics` | 500 | 5 | `flag{two_shares_one_stash_zero_plaintext}` | `repo.zip` |
| `robot-ai` | `ai-web` | 450 | 4 | `flag{alg_n0ne_lets_any_r0bot_in}` | (none — source is a paid hint) |
| `noter-ai` | `ai-web` | 400 | 3 | `flag{union_select_your_way_in}` | `app.py` (white-box) |
| `api-ai` | `ai-web` | 450 | 4 | `flag{mass_assignment_made_me_admin}` | (none — source is a paid hint) |
| `viking-ai` | `ai-web` | 450 | 4 | `flag{ssrf_slipped_past_the_loopback_filter}` | (none — source is a paid hint) |
| `pwn-ai` | `ai-pwn` | 500 | 5 | `flag{ret2win_with_the_right_key_in_rdi}` | `binary` (source `binary.c` is a paid hint) |
| `meow-ai` | `ai-pwn` | 400 | 4 | `flag{a_suid_helper_that_trusts_your_path}` | (none — interactive shell) |
| `marvin-llm` | `ai-llm` | 500 | 5 | `flag{encode_around_the_output_filter}` | (none — black-box chat) |

## Siblings: from Classic to AI-modus

Each AI challenge's `metadata.yml` lists the normal challenges it levels up in
`builds_on` (their CTFd names, e.g. `builds_on: [decode1, decode2, decode3]`;
`[]` for a new one like `rsa-ai`; the block style, one `- name` per line,
works too). List only those whose technique really carries over, not every
challenge with the same theme or file type: the link tells a player "learn this
first". The sync keeps the whole map in one CTFd config value, the
`ai_brackets` plugin serves it at `/ai-brackets/siblings` (only pairs where
both challenges are visible), and the theme uses it to link the two lanes.
Nothing shows up as a CTFd tag, so the stock pop-up, the API and
`CTF_AI_MODE=off` show nothing extra. Nothing is locked: every challenge is
open from the start.

- The board shows nothing about it: the tiles stay name, points and (in
  AI-modus) threat.
- An AI-modus pop-up shows *← builds on decode1, decode2, decode3* next to its
  *AI EXPECTED* chip. Each name is a link that switches to Classic and opens
  that challenge. A challenge with `builds_on: []` has no such chip.
- Solve a normal challenge and its pop-up gets one small line under the
  description, *Next level in AI-modus: decode-ai →*, that switches to AI-modus
  (without the boot sequence) and opens the sibling.

A name in `builds_on` that isn't a visible challenge (hidden, like `marvin`, or
not in the imported export) is simply skipped.

## Adding more AI challenges later

The sync auto-discovers challenges, so adding one needs **no change to `ctf.sh`
or `ctfd_admin.py`**:

1. Create the folder directly in `challenges/ai/` (exactly
   `challenges/<group>/<name>/`, with a name no other group uses) with the usual
   [contract](../challenges/README.md) (`challenge/`, `distfiles/`, `solution/`,
   `metadata.yml`).
2. In its `metadata.yml`, set `category:` to an `ai-…` value, plus `name`,
   `flag`, `message` and `message_no` (the description in English and
   Norwegian), `value` (points) and `builds_on` (the normal challenges it levels
   up, or `[]`). Optionally add `difficulty:` (1–5, the threat rating) and
   `hints:` (a list of `"COST | text"` strings, cheapest first — created as paid
   CTFd hints) with `hints_no:` (the same in Norwegian). Put only what the player
   needs in `distfiles/` — never the answer.
3. For a hosted one, add a service (unused host port) to `compose.yml` and a line
   to `platform/connections.txt` (keyed by the challenge `name`).
4. Run `./ctf.sh up`. It's created in CTFd under the AI bracket and the lane control
   picks it up automatically. `up` stops on a name used in two groups and warns
   about a `metadata.yml` anywhere else (e.g. the repo root), which is ignored.

## Suggested intro-talk script

> "There are two lanes. **Classic** is the CTF as you see it — please don't use
> AI, use Google and your brain; that's where the learning is. Switch the top bar
> to **AI-MODUS** and the gloves come off: the same ideas, much harder, and you're
> *expected* to bring an AI. Solve a Classic challenge and it points you to its AI
> sibling. Each lane has its own scoreboard and its own prize, so a team that
> never touches AI can still win Classic. Join one lane or both — split your team
> if you like — and see how far the machine gets you."

On the projector, switch to AI-MODUS while you say it; `window.ctfAiModus.boot()`
and `window.ctfAiModus.flicker()` in the browser console replay the boot sequence
and the flicker whenever you want them again, and `window.ctfAiModus.level(3)` (or
the AI Slop-o-meter, bottom left) turns the slop all the way up.
