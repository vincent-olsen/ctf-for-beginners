# AI-modus theme

The two lanes' skins (a calm blue **Classic** and a loud, burning **AI-modus**)
and the navbar lane control that drives the two brackets. These files are the source of truth; `ctf.sh` links them into CTFd on
every `./ctf.sh up`, so you edit them here and re-run — no theme fork, no manual
admin-panel steps.

CTFd serves them as files: `platform/ctfd.yml` mounts this folder read-only at
`/opt/ctf-theme` in the ctfd container, the `ctf_theme` plugin
([platform/plugins/ctf_theme](../plugins/ctf_theme/__init__.py)) serves its `.css`
and `.js` files at `/ctf-theme/<file>`, and `theme_header`/`theme_footer` only hold a
`<link>` or `<script src>` per file. Inlined, they would outgrow the 64 KB a CTFd
setting holds in MariaDB. Each URL ends in `?v=<the file's hash>`, so a browser keeps
a version for up to a day and fetches a changed file after the next `up`.

## Files

| File | Linked from | What it does |
|---|---|---|
| `ai-mode.css` | `theme_header` (`<link>`) | both skins (Classic under `html:not([data-ai-mode="on"])`, AI-modus under `html[data-ai-mode="on"]`), the lane control, the lane banner, the first-visit chooser, the effect layers, and the rule that hides the other bracket |
| `ai-mode.head.js` | `theme_header` (`<script src>`) | early bootstrap: sets the mode, and whether the AI-modus effects are off, from `localStorage` before paint (no flash); on the Scoreboard, points CTFd's scoreboard API calls at the bracket picked in the page's tabs (`?board=` in the address, else the selected lane's); reports each flag answer with its challenge's id, name and points (a `ctf-attempt` event), for the wrong-flag feedback and the solve moment |
| `ai-mode.js` | `theme_footer` (`<script src>`) | builds the navbar lane control and the first-visit chooser, tags each board category as `ai`/`normal` for the CSS filter, adds the lane banner to the Challenges page, gives the Scoreboard its All \| Classic \| AI-MODUS tabs, adds per-bracket scores to team pages, counts wrong flags in a row, celebrates a solve, runs the AI-modus fun mode |
| `i18n.strings.js` | `theme_header` (`<script src>`) | every word the theme and CTFd's own pages show players, in Norwegian and English side by side: edit the words here ([docs/language.md](../../docs/language.md)) |
| `i18n.js` | `theme_header` (`<script src>`), before `ai-mode.head.js` | the language: sets it on `<html>` before paint, gives the other scripts their words (`ctfI18n.t`), translates CTFd's English on the page, and builds the NO \| EN switch at the far end of the navbar |
| `hosted-fx.css`, `hosted-fx.js` | not linked into CTFd: loaded by the hosted AI challenge pages | the AI Slop-o-meter's levels on noter-ai, robot-ai, api-ai and viking-ai (see "Hosted AI challenges" below) |
| `first-blood.css` | `theme_header` (`<link>`), not in a preview | the first-blood show, banner, stamp and sound control (see "First blood" below) |
| `first-blood.js` | `theme_footer` (`<script src>`), not in a preview | asks the `ctf_firstblood` plugin who solved what first and announces it: the show with sound on the Scoreboard, a banner elsewhere; also keeps the Scoreboard's table and graph fresh |
| `solve-limit.js` | `theme_footer` (`<script src>`), not in a preview | asks the `ctf_solve_limit` plugin which challenges with `max_solves` are locked; marks their tile and, in the challenge window, names who found the flag and switches the flag field off |
| `first-blood.mp3` | not linked: `first-blood.js` fetches it when the sound is on | the voice that says "FIRST BLOOD" (rebuild it with `tools/first-blood-voice.py`, or drop in your own) |
| `preview.css` | `theme_header` (`<link>`), preview only | the preview's vintage green-phosphor terminal look over Classic, and the boot screen's styles |
| `preview.head.js` | `theme_header` (`<script src>`), preview only | covers the page before paint on the first page of a browser session, for the boot screen |
| `preview.js` | `theme_footer` (`<script src>`), preview only | the 5-second boot screen, the countdown to the event, and the preview's solve moment and solved list |

## Name, logo and favicon

They come from a brand folder, `brand/` unless `./ctf.sh up --brand DIR` picks
another (saved for later runs; `--brand ""` leaves CTFd's own, from the imported
export or Admin → Config). Its `brand.conf` names them:

```
name=CTF for n00bs
logo=flag-logo.svg
icon=flag-logo.ico
```

For your own event, copy the folder, change the name and the files, and pass it with
`--brand`.

On every `up`, `ctfd_admin.py` sets CTFd's `ctf_name` to `name` (the page title, the
logo's alt text, and the start of an export's file name), in place of the imported
export's, and uploads `logo` and `icon` as CTFd's **Logo** (`ctf_logo`, the
navbar) and **Small Icon** (`ctf_small_icon`, the favicon). A file is uploaded again
only when its bytes change. While a brand is set it wins over Admin → Config, so edit
the folder rather than the admin panel. This happens with the theme off too, and a
failed upload only warns.

The logo is square, so the navbar shows it at 32px instead of CTFd's 25px
(`ai-mode.css`), in place of the event's name. In a preview it stands in front of the
`guest@ctf $` prompt (`preview.css`). `flag-logo.png` (32px) and
`flag-logo-512.png` are the same mark as PNGs, for anything else that needs one.

## Language

Players see English by default and switch to Norwegian (and back) with **NO | EN**
at the far end of the navbar, after the light/dark switch: small on purpose, next
to the loud lane control. `./ctf.sh up --lang no` makes Norwegian the default. The
switch is instant, with no reload, follows in other tabs, and is remembered in
`localStorage` (`ctf-lang`).

Every word lives in `i18n.strings.js`: the theme's own (`strings`, both languages
side by side, read with `ctfI18n.t(key)`; text that stays on the page is bound to
its key, so a switch rewrites it) and CTFd's (`ctfd`: CTFd's English and what to
show instead; `ctfd_admin.py` keeps CTFd itself on English underneath). The
stylesheets' `content:` text comes from the same file as `--ctf-t-*` variables.
Challenge descriptions and hints carry both languages as blocks
(`<div class="ctf-lang" lang="no">`, written by the sync from `message_no` /
`hints_no`), and `ai-mode.css` shows the one in the page's language. The whole
story, including how to make a page bilingual and add a language, is in
[docs/language.md](../../docs/language.md).

## How the injection works

`platform/ctfd_admin.py` wraps the `<link>`/`<script src>` tags in HTML-comment
markers (`<!-- >>> ai-modus (managed by ctf.sh) >>> -->` … `<!-- <<< ai-modus <<< -->`)
and **appends** them to whatever `theme_header`/`theme_footer` the imported
export already has (an export's own `theme_header` is kept).
Re-running strips the old managed block first, so it's idempotent and picks up
your edits. The tags in `<head>` are ordinary blocking ones, so the CSS and
`ai-mode.head.js` are in place before the page paints and before CTFd's own
scripts load.

Both lanes paint the navbar and page header themselves, so **Admin → Config →
Theme → Theme Color has no effect** while this theme is on (it did nothing in
AI-modus before either). That's on purpose: a Theme Color set there (an older
export has CTFd's `#212529` grey) would undo the Classic look. To change the colours,
edit `--cl-deep` / `--cl-ground` (Classic) or `--ai-bg` (AI-modus) at the top of
`ai-mode.css`.

Turn it off (restore stock CTFd) with either:

```bash
CTF_AI_MODE=off ./ctf.sh up          # ctf.sh passes --no-ai-theme and removes ctf_theme and ctf_firstblood
```

A preview (`--preview`) keeps the theme even then, as the Classic lane only: its
note and its hidden Login link are part of it.

In both lanes the theme also trims CTFd's chrome: no "Powered by CTFd" footer, and
none of CTFd's own language choices (its navbar menu and the Language field in
Settings), since the theme's NO | EN switch replaces them; see "Language" below. After a correct flag every challenge
window has a **Close** button where CTFd shows "Next Challenge" (only for a
challenge with a next one set); `ai-mode.js` relabels it and makes it close the
window.

A wrong flag gets a "try again" line under CTFd's **Incorrect**: "Not quite. Try
again." in Classic, `> access denied. try again` in AI-modus (where every alert
glows on the dark panel instead of Bootstrap's pastels: red for Incorrect and errors,
neon green for Correct and already solved, amber while paused and for the page
notices above the board, such as "... is paused"). CTFd reuses one alert
for every answer, so a second wrong flag would look like nothing happened; from the
second in a row the line counts them ("Still not it (2 in a row)", `access denied x2`)
and the alert shakes: a short head-shake in Classic, a jolt with a red flare in
AI-modus. Reduced motion keeps the count without the shake. `ai-mode.head.js` sees
each answer (CTFd keeps its own copy of `window.fetch`, so the hook must be in before
CTFd loads), `ai-mode.js` sets `data-ctf-fails` on the alert and replays the
`ctf-refail` class, and `ai-mode.css` draws the line and the shake.

The same hook keeps the answer box from going blank. CTFd draws it from the
answer's `data`, and an answer without one (CTFd's own 403 when the session has
expired, the preview plugin refusing a request, an error page) used to leave an
empty box. `ai-mode.head.js` hands CTFd `{status: "error", message}` instead, which
every lane shows as a warning: "Your session has expired. Reload the page and try
again." for that 403, otherwise the server's own message or the error code.
`ai-mode.js` also works around CTFd 3.8 requesting the challenge's solution after
every answer: a visitor without an account is refused, and CTFd's handler threw
before it refreshed the board. A refused request now reads as "no solution".

A correct flag gets a moment of its own over the page, about three seconds, that
never takes a click (CTFd's **Correct** still says it in words). Classic: a calm
card, "Flag captured" with a check mark drawing itself, the challenge and its points,
and blue confetti falling. AI-modus: `FLAG PWNED` in fire under
`// target compromised`, the challenge window jolts, a heat glow comes up from the
bottom and embers rise. Reduced motion shows the card alone, still. An answer to a
challenge you already solved ("already solved") gets none. `ai-mode.js` (`celebrate`)
builds it from the same answer hook, and `ai-mode.css` (`.ctf-win`) styles it.

Ratings are off for the whole CTF, set by `ctfd_admin.py`
(`challenge_ratings = disabled`), so the "Rate this challenge" box and review field
are gone even with the theme off.

In a preview (`./ctf.sh up --preview julius,meow1`), `ctfd_admin.py` adds
`data-ctf-preview` to `<html>` ahead of `ai-mode.head.js`. The theme then has the
Classic lane only: no lane control, no first-visit chooser, no Login link and no
lane rule (the countdown takes its place). The bracket filter is
off, so an AI-modus challenge put in a preview shows on the same board.

The preview also gets `preview.css` and its scripts, injected only then: a vintage
green-phosphor terminal (VT323 from Google Fonts, scanlines, a vignette and glowing
text) where the board reads like `ls -la` (`drwxr-xr-x crypto/`, `./julius`), a
challenge window like `$ cat julius`, and a wrong flag answers `[ FAIL ]` with
`> try again` under it; from the second in a row it reads
`> still wrong (2 in a row) - try again` and the alert jolts and flares amber (the
lanes' wrong-flag feedback above, in the terminal's words). The first
page of a browser session opens with a 5-second boot screen (BIOS lines, systemd-style
`[  OK  ]`, a login and a progress bar); a click or any key skips it, a session cookie
(`ctf-preview-booted`) keeps it from replaying, and reduced motion gets a still
frame for 1.5 seconds. The cover that hides the page during the boot lifts itself
after 7 seconds even if the script never runs.

A preview saves nothing on the server, so the challenges you solve there are kept in
the browser only: `localStorage` `ctf-preview-solved`, a list of their names. The
board marks them `[  OK  ] solved`, and other tabs follow along.
A new solve gets the preview's own moment in place of the lanes': a terminal over the
page types `$ ./capture --flag julius`, `[  OK  ] flag accepted (+100 pts)`, then
`ACCESS GRANTED`, with green glyphs raining behind it. A challenge already in the
list gets CTFd's "Correct" only. Clearing the site's data starts the list over.

Under the page title, a countdown to the event's start ticks every second:
`$ ./countdown --until "2026-11-18 16:00 Europe/Oslo"`, then `T-39d 05h 12m 44s` in big
glowing digits (the boot screen logs `[  OK  ] Armed countdown to ...` too). Once the
start has passed it reads `[  OK  ] The CTF has started.` and stops. The time is
`CTF_PREVIEW_EVENT_START` at the top of `preview.js`, with the offset written out
(`+01:00`, Oslo in November); `CTF_PREVIEW_EVENT_LABEL` next to it is what it shows.

## First blood

The first team to solve a challenge draws **first blood**, and everyone gets to
know. It is made for the Scoreboard page on the big screen:

| Where | What happens |
|---|---|
| the Scoreboard page | the show, about 9 seconds: blood on a machine. It opens with a two-second intro: the page goes dark behind red hex rain and scanlines, a frame draws itself around it (*LIVE*, the solve's number in hex, its time), `> first solve detected` types itself, and the line of a cut is traced across the screen. Then a white-hot blade follows that line, and **FIRST** and **BLOOD** slam in on two beats while the picture tears. Blood sprays out and runs from the letters, the team's name resolves out of noise over a heartbeat, the challenge follows with its category, points and lane, and the whole announcement appears bottom left as an `xxd` hexdump of its real bytes. At the end the screen switches off like a CRT. With the sound on: one deep bass note that grows all through the intro, two impacts, a sub-bass drop that swells in behind the voice, low brass, the heartbeat, a crackle when the picture tears, and a deep voice saying "first blood" on the same two beats |
| every other page | a small red banner at the top for six seconds, *FIRST BLOOD · Team X drew first blood on overflow3 +400 pts*. Never a sound |
| the player who drew it | **FIRST BLOOD**, *Nobody solved it before you*, stamped on the solve moment (*Flag captured* / *FLAG PWNED*) |

Nothing takes a click or gets in the way of typing (Esc ends the show early), the
look is the same in both lanes and at every level of the AI Slop-o-meter, and
reduced motion gets the words on a still card.

**On the big screen.** Open `/scoreboard` (or `/scoreboard?board=all`) in any
account that may see the scoreboard; the admin's works, and the admin doesn't
have to play. Under the title sits *First blood · Sound off · Test*:

- **Sound** is off until someone turns it on, and is remembered per browser
  (`localStorage` `ctf-fb-sound`), so the projector has it and forty laptops
  don't. Players may turn it on for themselves; it only ever plays on the
  Scoreboard page.
- A browser lets a page make sound only after a click or key press on it. After
  a reload the control says *Click anywhere on the page to let the sound
  through* until you do. A kiosk that nobody touches can start Chrome with
  `--autoplay-policy=no-user-gesture-required` instead.
- **Test** plays the show with an example, for checking the screen and the
  volume. `window.ctfFirstBlood.demo("Team", "challenge")` does the same from
  the console, on any page.

The page also stops lagging behind: CTFd refreshes the Scoreboard every five
minutes, but with this on, its table and graph are fetched again within seconds
of a solve or a hint (at most every ten seconds).

**The rules.**

- First blood is a challenge's first solve by a visible account. A hidden or
  banned account never draws it (the admin account is hidden): the first visible
  team after it does. Hidden challenges are left out.
- Whoever may see the scoreboard gets the announcements (CTFd's score and
  account visibility settings). After the scoreboard freeze nothing new is
  announced, for the admin too, since the projector is public.
- Only a first blood of the last five minutes is announced, at most three in a
  row, each browser announces one once (`localStorage` `ctf-fb-seen`, so a reload
  or a second tab doesn't repeat it), and a browser's first visit announces
  nothing: opening the board mid-event doesn't replay the day.
- A tab in the background doesn't ask; it catches up when you look at it.

**How it works.** The `ctf_firstblood` plugin
([platform/plugins/ctf_firstblood](../plugins/ctf_firstblood/__init__.py)) serves
`/first-blood/feed`: the first bloods of the last quarter of an hour, each with
its age by the server's clock, and a revision of the standings. `first-blood.js`
asks every 4 seconds on the Scoreboard and every 12 elsewhere. `ctf.sh` installs
the plugin with the theme, so `CTF_AI_MODE=off` removes it, and a preview, which
saves no solve, has neither. If the plugin can't load it switches itself off
(` * ctf_firstblood disabled` in the CTFd log) and nothing is announced.

**The sound.** Everything but the voice is made in the browser with Web Audio
(`first-blood.js`, `Sound`), so there is nothing to license or download. It is
mixed for a room: most of its weight is below 60 Hz, which a laptop's own
speakers barely play, so give the projector real speakers. Everything else
steps back while the voice speaks and the bass swells in right behind it, so
the words stay clear however loud it is.

The voice is `first-blood.mp3`, 48 KB: the Kokoro text-to-speech model
(Apache 2.0) saying "First. Blood.", made by `tools/first-blood-voice.py` into a
machine's idea of an arena announcer. Its body is pitched far down, the highs
of a copy pitched down only a little keep the consonants crisp, a third copy
sits an octave below, and the end of "blood" is caught in a loop that breaks up
as it fades. To use your own, a friend with a deep voice, say, replace the
file (keep the name) and set `VOICE_BEATS` at the top of `first-blood.js` to the
seconds where its two words start: the title's two words land on them. Without
the file the browser's own speech synthesis says it.

## The two brackets

Both brackets live in the same CTFd. The **category name** is the real divider:

- **Classic bracket** (the normal challenges) — categories WITHOUT an `ai-` prefix (`web`, `crypto`, …).
  Solve with Google + brains; the honour system says no AI.
- **AI bracket** — categories starting with `ai-` (`ai-crypto`, `ai-web`,
  `ai-pwn`, …). Much harder; using AI is expected.

The navbar lane control (**Classic | AI-MODUS**, a keyboard-friendly radio group)
flips `html[data-ai-mode="on"|"off"]`, remembers the choice in `localStorage`, and on the Challenges page shows only the matching
bracket's categories. The switch takes effect instantly, with no reload: `ai-mode.js`
tags each category block `data-ai-bracket="ai"|"normal"` as the board renders, and
the CSS hides the bracket that doesn't match the `<html>` attribute. Other open
tabs and pages restored with Back/Forward pick up the change too. If a future CTFd theme changes the board markup, the filter
falls back to the `/api/v1/challenges` API and, failing that, degrades to "skin
only" — the `ai-` categories are still clearly labelled, so nothing breaks.

## The two lanes

**Classic** is calm on purpose: a slate navbar and header, blue accents, tiles
that lift on hover and a tick on solved ones. On the Challenges page a rule strip
under the title says *Classic lane: no AI. Google, docs and your own head.*

**AI-modus** is the loud one, so nobody forgets they're in the hard lane:

| Effect | What it does |
|---|---|
| Boot sequence | a green terminal intro (~2.7 s) when you switch into the lane, and on the first AI-modus page of a browser session. Click or Esc skips it. |
| Flames + embers | drawn flames along the bottom of the screen, **behind** the content: four rows of flame shapes (dark red at the back, then orange, yellow and a white-hot core) that each lick on their own loop, over a bright bed, with embers floating up. `ai-mode.js` places and sizes them (more of them on a wider window); `ai-mode.css` animates them |
| Matrix rain | faint green code falling behind the flames: about a third of the columns at a time, each at its own pace, with a pale glyph at the head. It fades out before it reaches the fire |
| Burning headings | the page title, the brand, the final boss's name and a challenge window's title in a moving fire gradient; the title also glitches. Category names are small and quiet |
| Lane banner | *AI-MODUS · AI EXPECTED · THREAT LEVEL: NIGHTMARE* above the title and, beside it, how much of the bracket you have rooted (*5 / 14 rooted* and a thin bar), counted from the board |
| Final boss | the `ai-llm` category (`marvin-llm`) heads the board as one wide row: *FINAL BOSS*, its name, its points and the boss's sanity, which drops with every team that breaks it (100% minus solves per team; no bar when CTFd doesn't show the solve or team count) |
| Tiles | dark glass that burns on hover: the name on top, the points and 1–5 flames (the `difficulty` in `metadata.yml`, else from the points: 300 → 3) below; a solved tile says *rooted* in green where its points were, and its flames go grey; a solved challenge's window gets a green *✓ ROOTED* chip next to *AI EXPECTED* |
| CRT | scanlines and a slow rolling bar |
| Random flicker | the page jolts and flashes a warning (*SIGNAL INTERRUPTED*, *KERNEL PANIC*, …) |

The flicker spaces out the longer you play: every 45–75 s for the first 10
minutes in the lane, then every 1.5–2.5 min, then every 3–6 min, where about 1 in
12 comes back within 3–10 s as a surprise double-hit. The lane clock
(`ctf-ai-since`) and the next due time (`ctf-ai-next-flicker`) live in
`localStorage`, so CTFd's page reloads don't reset them; a clock older than 12
hours starts over. Only the tab you're looking at flickers. Each flicker is two
dips in 0.8 s with no brightness, invert or colour spikes, and the warning fades
in and out, so it stays under the three-flashes-a-second limit for
photosensitive players. The boot sequence plays on the first AI-modus page of a
browser session (a session cookie, `ctf-ai-booted`, so new tabs don't replay
it) and whenever you switch into the lane, except from a link in a challenge
window.

With *reduce motion* set in the OS, the colours stay and every animation stops:
no boot sequence, rain or flicker, and the flames stand still. This
follows the setting live, so turning it on mid-session stops the effects at once.
The flicker also never fires while a challenge (or any) pop-up is open, so it
can't get in the way of typing or submitting a flag.

### The AI Slop-o-meter

How much of all that a player gets is theirs to pick: the **AI Slop-o-meter**
sits in the bottom-left corner of every AI-modus page (under any pop-up), a
slider over four levels and a button per level, with the level's number and
name. The Classic lane has none of it.

| Level | Name (NO / EN) | The board |
|---|---|---|
| −1 | WEB 1.0 | the lane as a homepage from 2003: a starfield, a grey bevelled frame, Times New Roman and Verdana, a WordArt fire title, blue underlined links, a navy marquee under the navbar, an LED hit counter at the bottom, under-construction stripes, and the challenge window and the meter as Windows 98 dialogs. Entering it greets you with a "Message from webpage" box. No flames, rain, CRT layers or flicker |
| 1 | ROLIG / CALM | the old Effects OFF: the colours, burning headings, banner and solve moment stay; no flames, matrix rain, scanlines, rolling bar, flicker or boot sequence |
| 2 | BRANN / BURN | everything above, as it always was. The default |
| 3 | AI-SKREKK / AI HORROR | everything of level 2 recoloured violet-pink-orange (the fire's gradients, ✦/AI/GPT token rain), with slop around the board: a holographic title that melts, a "Certainly!" typewriter line and a whisper, tiles that float in spinning gradient edges with badges (✦ AI, NEW, TRENDING…) while a solved one stops, turns green and gets a ✓ in its corner and a *✓ ROOTED* badge, a buzzword ticker, "✦ Ask AI 99+" in the navbar, blobs, a synthwave floor and eyes behind the page, sparkles and a violet vignette over it, toasts, the board's own assistant (*Marvin AI*, bottom right, answering from a fixed list; nothing is sent anywhere), a slow sway, and a flicker every 8–15 s with *HALLUCINATION DETECTED* and friends. The challenge window gets an AI summary, *Explain like I'm 5*, *Generate flag* (it hallucinates one) and *Was this challenge helpful?* around the real description; either vote button lights up with a burst of sparkles, the question turns into a thanks and Marvin answers (nothing is sent anywhere) |

The choice is kept in `localStorage` (`ctf-ai-fx`: `-1`, `1`, `2` or `3`; the old
button's `off` reads as 1), set on `<html>` as `data-ai-fx` before paint by
`ai-mode.head.js`, and followed by other open tabs. `ai-mode.js` builds level 3's
and level −1's extras the first time the level shows and keeps them; `ai-mode.css`
shows each only at its level, so a level change is one attribute. The first-visit
chooser's AI-MODUS side points at the meter. `window.ctfAiModus.level(3)` sets it
from the console.

At every level: reduced motion keeps the look and stops all motion; the flicker
stays two dips in 0.8 s (level 3 only flickers more often); nothing moves over an
open challenge window; and level 3 uses no blur filter, blend mode or
backdrop-filter on big layers, and no drop shadow on moving parts, because phones
run out of memory on those. On a narrow screen level 3 leaves out the chat, the
toasts and the eyes.

The level reaches the AI challenges too. In an AI challenge's window, `ai-mode.js`
rewrites the connection info: a terminal challenge's `nc` command gets the port of
the player's level (meow-ai and pwn-ai serve each level's look on a port of its
own, see the table in `TERMINAL_PORTS` and `compose.yml`; CTFd keeps level 2's),
and a web challenge's link gets `#fx=<level>`, which never reaches the challenge's
server. See "Hosted AI challenges" below.

### Hosted AI challenges

noter-ai, robot-ai, api-ai and viking-ai share their building blocks (`.bar`,
`.box`, `.rule`, glitching titles), so one kit draws every level on all four:
`hosted-fx.css` and `hosted-fx.js` here, served by CTFd at
`/ctf-theme/hosted-fx.*` (the `ctf_theme` plugin, with a 5-minute cache because the
pages can't know the files' hash) and not linked into CTFd's own pages. A small
inline script at the top of each page's `<head>` (the same in all four: Jinja
`base.html`, `skin.py`, `main.go`) reads `#fx=<level>` from the address, keeps it in
the page's own `localStorage` (`ctf-ai-fx`, per origin), takes it out of the
address bar, sets `<html data-ai-fx>` and loads the kit from CTFd on the same host
(`//<host>/ctf-theme/`). The kit only adds layers and CSS: no requests to the
challenge, no cookies, nothing that changes what the page sends; if CTFd can't be
reached (or runs with `CTF_AI_MODE=off`, or the challenge runs alone with
`local.sh`), the page looks exactly as it always did.

| Level | The page |
|---|---|
| −1 | the whole page as a 2003 homepage: starfield, a grey bevelled window, Times New Roman, Impact fire titles, Windows 98 buttons and inputs, a marquee and an LED hit counter |
| 1 | today's look without scanlines |
| 2 | today's look with the board's matrix rain, flames and embers behind it and a rolling bar on top |
| 3 | violet AI fire and token rain, glass panels with spinning edges, holographic titles, a buzzword ticker, an "AI Summary of this page", blobs, eyes in the margins, sparkles, a vignette and toasts (never over a form control). No flicker, no fake chat |

marvin-llm has its own look (MARVIN-GPT ∞, its level 2) and its levels −1, 1 and 3
live in its own templates, switched by the same `#fx` link. meow-ai and pwn-ai
serve each level's banner on a port of their own (`listen.sh` in each, one socat
per level, `AI_FX=<level>` in the session): the board's window shows the `nc`
command for the player's level.

The lanes are linked through each AI challenge's `builds_on`, which the sync
keeps in a CTFd config value that players never see and the `ai_brackets`
plugin serves at `/ai-brackets/siblings`. The tiles show nothing about it; the
links are in the pop-ups. An AI pop-up's *← builds on mono* chip (next to *AI
EXPECTED*) switches to Classic and opens mono, and a solved Classic pop-up gets
one small line under its description, *Next level in AI-modus: mono-ai →*, that
switches to AI-modus and opens the sibling. See
[docs/ai-mode.md](../../docs/ai-mode.md#siblings-from-classic-to-ai-modus).

A browser that hasn't picked a lane yet gets a **first-visit chooser** on the
Challenges page (*Pick a lane to start*). Esc or *Enter Classic* keeps the
default. It never shares the screen with a pop-up: a challenge opened from a
link, or a pop-up that opens while it is up (an admin's notification alert),
comes first, and the chooser follows once that closes (after 4 s at most for a
link to a challenge that doesn't open).

For the intro talk, `window.ctfAiModus.boot()` and `window.ctfAiModus.flicker()`
in the browser console replay the effects on demand, and
`window.ctfAiModus.level(3)` turns the slop all the way up.

The Scoreboard follows the lane too: each bracket has its own ranking, scored
by the `ai_brackets` plugin in [`platform/plugins/`](../plugins/ai_brackets/__init__.py),
which `ctf.sh` installs into CTFd. `ai-mode.js` puts three tabs above the table,
**All | Classic | AI-MODUS** (`#ai-board-tabs`): the page opens on the selected
lane's bracket, a lane switch moves it there, and All lists every team once per
bracket it plays in, each with that bracket's score: *Team C (Klassisk)* and
*Team C (AI-MODUS)* for a team that plays both, never the two added together (the
plugin's `bracket=all`; `ai-mode.head.js` puts the lane after the name, in the
page's language, and a NO | EN switch fetches the board again). The pick sits in `html[data-ctf-board]`
and in the address (`?board=all|normal|ai`), so a reload or a shared link shows the
same board. `ai-mode.head.js` sends the page's
`/api/v1/scoreboard` calls to the plugin for the picked bracket (before CTFd's
own JS loads, since that keeps its own reference to `fetch`), and on a new pick
`ai-mode.js` has CTFd's table and graph fetch again (the latest request wins, so
overlapping fetches can't show the other bracket). If the plugin is missing or
fails, the page falls back to the stock scoreboard, labels it *Both brackets
combined* and shows no tabs. Team pages (user pages in users mode) get a line per bracket under
the combined score. See [docs/ai-mode.md](../../docs/ai-mode.md#two-scoreboards).

To add an AI challenge to the board, create it in `challenges/ai/` with a
`category:` that starts with `ai-` in its `metadata.yml`; `ctf.sh` creates it in
CTFd (see [docs/ai-mode.md](../../docs/ai-mode.md)).
