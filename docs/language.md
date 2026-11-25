# Language: Norwegian and English

Everything players see is in English by default, and in Norwegian one click
away: **NO | EN** at the far right of the navbar (small on purpose; the lane
control is the loud one). The switch takes effect at once, with no reload, in
every open tab, and the browser remembers it (`localStorage` `ctf-lang`). It works
in both lanes and in a preview, where it reads `[no] en`.

| What | Where its words live |
|---|---|
| The theme: lane control, banners, chooser, chips, solve moments, the preview's boot screen and countdown, the "try again" lines | [`platform/theme/i18n.strings.js`](../platform/theme/i18n.strings.js), `strings` |
| CTFd's own pages: navbar, log in, register, teams, scoreboard, settings, the challenge window, answers to a flag, error messages | the same file, `ctfd` and `ctfdPatterns` |
| Challenge descriptions | each challenge's `metadata.yml`: `message` (English), `message_no` (Norwegian) |
| Hints | each challenge's `metadata.yml`: `hints` (English), `hints_no` (Norwegian) |
| The Info page | [`platform/pages/`](../platform/pages/): `info.md` (English), `info.no.md` (Norwegian) |
| The front page | [`platform/pages/index.md`](../platform/pages/index.md): one file, a block per language for each text |
| Other pages from Admin → Pages (pause, winners) | the page itself in CTFd: write a block per language (below) |

## The default language

```bash
./ctf.sh up              # English until a player switches (the default)
./ctf.sh up --lang no    # Norwegian until a player switches
```

`--lang` is saved in `.ctf/settings.env` like the other options; on Azure,
`./azure.sh up --lang no` (or `deploy --lang no`) passes it on to the VM. A player
who has used the switch keeps their choice.

Under the theme CTFd renders its own pages in English, and `i18n.js` translates
them. So `up` clears the Language a player picked in CTFd's Settings, and `i18n.js`
drops CTFd's `language` cookie (both would make CTFd render another language,
which the table doesn't know), reloading once if the page came in another language.
CTFd's dialogs for unlocking a hint (`confirm`, and an `alert` for an error) are
replaced by `i18n.js` with translated ones, through `CTFd._functions.challenge`.

## Changing the words

Edit the file, run `./ctf.sh up` (or just reload the page: the theme files are
served straight from `platform/theme/`; a browser may keep a copy for a day until
the next `up` gives the file a new URL).

**The theme's own text** is in `strings`, one entry per text, both languages
side by side:

```js
"banner.classic.rule": { no: "Klassisk bane: ingen AI.", en: "Classic lane: no AI." },
```

`{name}` is filled in by the code; keep it. A key that starts with `css.` is
text the stylesheets show (`content:`), there `{n}` is the number of wrong
flags in a row.

**CTFd's own text** is in `ctfd`: CTFd's English exactly as it shows on the
page (spaces and line breaks don't count), and what to show instead:

```js
{ en: "Scoreboard", no: "Poengtavle" },
```

CTFd renders English underneath (`ctfd_admin.py` sets its `default_locale`), and
`i18n.js` replaces every text on the page that is exactly one of these, as the
page loads and whenever CTFd draws more. Texts with a number or a name in them
are regular expressions in `ctfdPatterns`. To translate something that still
shows in English: find its exact English (switch to EN), and add a line.

Left alone on purpose: challenge names and categories, descriptions and hints
(they have their own blocks), code, team and player names, and the pages an
organiser writes. CTFd draws a few texts into images, which can't be replaced:
the titles of the scoreboard and team graphs ("Top 10 Teams", "Score over
Time"). The admin panel stays in English.

## Challenge descriptions and hints

In `metadata.yml`, next to the English:

```yaml
message: |
  This encryption was once used by the Roman military. Can you crack it?
message_no: |
  Denne krypteringen ble en gang brukt av det romerske militæret. Klarer du å knekke den?

hints:
  - "25 | One shift is one guess; ..."
hints_no:
  - "25 | Ett skift er én gjetning; ..."
```

`hints_no` holds the same hints in the same order; the cost always comes from
`hints`, so `hints_no` may leave out the `COST |`. A multi-line hint is a block:

```yaml
hints:
  - |
    9 | With `objdump` you can calculate the offset ...

    A useful command
```

`./ctf.sh up` writes both into CTFd, as a block per language:

```html
<div class="ctf-lang" lang="no">

...Norwegian Markdown...

</div>
<div class="ctf-lang" lang="en">

...English Markdown...

</div>
```

and the page shows the one in the player's language. A text in one language only
(no `message_no`) is shown as it is, in both. The repo is the source of truth:
`up` overwrites edits made in the admin panel.

Normal challenges take their hints from `metadata.yml` too. One whose metadata has
no `hints` keeps the hints CTFd has (an imported export's). Editing a hint keeps a
player's paid unlock.

Hints are unlocked cheapest first: a hint requires the challenge's strictly
cheaper ones (CTFd's hint prerequisites, set on every `up`), and hints of the
same cost can be taken in any order. So give two independent tips the same cost,
and a ladder rising costs.

## Pages

A page kept in [`platform/pages/`](../platform/pages/) is synced into CTFd on every
`./ctf.sh up`: `<route>.md` is the page in English and `<route>.no.md` in
Norwegian, both Markdown, and together they replace the content of the CTFd page
with that route (`info` is `/info`, the Info page). They become a block per
language, like a challenge's description; edit the files, not the page in the
admin panel, which `up` overwrites. The page keeps its title, visibility and place
in the navbar as CTFd has them; a route CTFd doesn't have yet is created (visible,
except the break, winners and podium pages, which you show in Admin → Pages when
it's time). The Info
page there says the registration code is given out at the start (the code itself
stays out of the repo; `./ctf.sh up --registration-code` sets it). Fill in your own
event's time, agenda and contact before an event.

A page can also keep both languages in one file, `<route>.md` alone with its own
blocks. The front page, [`index.md`](../platform/pages/index.md), does: its
countdown script must run once, so the style and script are shared and each text
is a pair of elements with `class="ctf-lang"`, like
`<span class="ctf-lang" lang="no">Timer</span><span class="ctf-lang" lang="en">Hours</span>`.
The pair must be siblings. Without the theme, the sync drops the blocks in the
other language. The countdown runs to the CTF's end time and stays hidden while
none is set (`--event-start`/`--event-end` set them).

The break page [`pause1.md`](../platform/pages/pause1.md), the winners page
[`winners.md`](../platform/pages/winners.md) and the podium page
[`podium.md`](../platform/pages/podium.md) are built the same way (see
[ai-mode.md](ai-mode.md#the-podium-page)).

A page you make in the admin panel instead is left alone by `up`. To make one
bilingual, wrap each language in a block, with blank lines around the Markdown
inside:

```html
<div class="ctf-lang" lang="no">

## Regler
- Samle så mange poeng som mulig.

</div>
<div class="ctf-lang" lang="en">

## Rules
- Collect as many points as possible.

</div>
```

A page without blocks shows as it is in both languages.

## Without the theme

With `CTF_AI_MODE=off` there is no switch. The sync then writes only the default
language's text (`--lang`), and CTFd shows its own pages in its own translation of
that language (CTFd ships a Norwegian one, with its own menu for changing it).

## Adding a language

1. Add it to `languages` in `i18n.strings.js` (`code`, the `label` on the switch,
   its `name`, and its `html` language tag), and a translation to each entry of
   `strings` and `ctfd` (a missing one falls back to English).
2. Add its code to `LANGUAGES` in [`platform/ctfd_admin.py`](../platform/ctfd_admin.py)
   and to the `--lang` check in `ctf.sh`.
3. Add its two rules to the "bilingual content" block in
   [`platform/theme/ai-mode.css`](../platform/theme/ai-mode.css).
4. Write `message_<code>` and `hints_<code>` in the challenges.
