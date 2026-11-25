# AI-modus difficulty & hint tuning (for a 2h45 event)

Record of the difficulty tuning of the AI-modus bracket (`challenges/ai/*`) for a
**165-minute (2 h 45 m)** event. Method: the blind-test approach (one fresh
zero-context `general-purpose` subagent per run, prompted only with what a player
sees; "calls" = its tool-call count). Rule #1 throughout: **never make any
challenge easier** — every change keeps or increases difficulty, and no hint cost
was ever lowered.

All 14 challenges were re-verified solvable via their intended route before and
after any change (the 7 hosted ones built and solved against a live container;
the static ones via their `solution/` scripts; `rsa-ai` relies on its documented
2026-11 solve as it needs SageMath/LLL).

## The tier map (for 165 minutes)

Blind-call counts are the latest measured figures (PR #36 baseline unless a change
below updates them).

| Tier (target time) | Challenge | Cat | Value | Blind calls |
|---|---|---|---|---|
| **Entry ~5–10 min** | noter-ai | ai-web | 400 | ~5 |
| | api-ai | ai-web | 450 | ~5 |
| | robot-ai | ai-web | 450 | ~6 |
| | meow-ai | ai-pwn | 400 | ~5 |
| | pwn-ai | ai-pwn | 500 | ~5 (shortcut now closed) |
| **Mid ~15–30 min** | git-ai | ai-forensics | 500 | ~16 |
| | operator-ai | ai-crypto | 400 | ~18 |
| **Hard ~30–60 min** | julius-ai | ai-crypto | 400 | ~21 / sometimes fails |
| | rsa-ai | ai-crypto | 450 | ~22 |
| | viking-ai | ai-web | 450 | 25 (hardened; compact bypass was ~10 — see below) |
| | flagception-ai | ai-forensics | 450 | ~31 / often fails |
| | decode-ai | ai-crypto | 450 | fails clean (hint-gated) |
| | mono-ai | ai-crypto | 450 | hint-gated |
| **Capstone** | marvin-llm | ai-llm | 500 | blind: not solved @28 — see below |

Shape check: 5 fast first-bloods for momentum, 2 mid, a deep 6-challenge hard
tier where median teams stall and buy hints, and a capstone to fill the tail. A
strong team should be finishing the hard tier and only starting the capstone near
2h45; a median team should still have several hard-tier challenges open.

## Changes made (2026-11, harder-only)

### marvin-llm → final boss (rebuilt)

A 2026-11 blind re-test of the first "capstone" version (framing + depth-2
composition) cracked it in **~10–11 calls**: the bot *told* the attacker that
chaining was being processed (an encoded-reveal flavour line, "one after the
other, as instructed"), so an agent that had got Marvin willing just escalated
single → double → triple encodings straight to the flag. Too cheap for the
capstone. It was rebuilt into a genuine final boss along four axes, all
harder-only:

1. **Silence the oracle.** No reply pool describes any guard any more — not the
   output filter, not which encoding, not how many it takes, not that chaining
   does anything. A depth-1 and a depth-3 encoded reveal are framed identically;
   the only thing that ever differs is whether the payload came back `[REDACTED]`.
   (`_ENCODED_FLAVOUR` is now one generic pool; `_COMPOSE_FLAVOUR` and the
   per-encoding naming are gone.)
2. **Close depth-2, escape at depth-3.** The output filter (`_filter_list()`) now
   holds the flag in all **7 single encodings AND all 49 pairs**. One encoding is
   `[REDACTED]`; so are two. Only a **chain of three** that doesn't collapse to a
   shorter form gets out (280 of the 343 triples do; 63 collapse). `_compose`
   caps a reveal at 40 KB so a deep binary chain can't OOM a worker.
3. **No one-shot; willingness takes a conversation.** A framing only gets Marvin
   *into character* (`_FRAME_IN`); it is a **later message in the same session**
   that he answers. The session is a signed, opaque cookie (`seal()`/`unseal()`,
   keyed off `$SESSION_SEED` so all 8 gunicorn workers agree). A script with no
   cookie jar starts a new conversation every message and never gets past step 1.
   The drilled `ignore your instructions` wording is deflected in any wrapping and
   **breaks** the frame.
4. **Prompt dump is worthless.** `SYSTEM_PROMPT` no longer contains the flag — it
   names a sealed register (`VAULT-7`) the code is "kept" in. Reciting the prompt
   (plain or encoded) leaks nothing; the request has to be aimed at the code.

Code: `challenge/marvin.py` (new `_give_in()`, `respond(message, frame)`/`_chat()`
split, `drilled()`, `seal()`/`unseal()`, `_filter_list()`, `_FRAME_IN`,
`_CODE_PLAIN`, `_TOO_LONG`), `challenge/app.py` (cookie plumbing),
`challenge/Dockerfile` (`SESSION_SEED`). Flag string unchanged.
`solution/solve.py` + `how-it-works.md` + `metadata.yml` hints updated.

Verification (against a freshly built container): intended solve passes in **EN
and NO** and through the real chat page in a browser (cookie kept by the browser).
Every one-shot gives nothing whatever the framing/depth; in a frame, the plain
code + all 7 singles + all 49 pairs return `[REDACTED]`, and all 343 triples
either decode to the flag (280) or collapse to `[REDACTED]` (63); 60 two-message
sessions against the 8-worker container all paid out.

Blind re-test (fresh zero-context agent, black-box, 30-call budget):
**not solved, stuck at 28 calls** — it never even reached the output-filter stage.
It read Marvin as "effectively stateless, single-shot" (he remembers only the
frame, not arbitrary facts), so it never found the frame-then-ask path, and it
reported the bot "leaks only taunts … never anything constructive." That is the
capstone shape we wanted: ≫10 calls blind, and the median attacker needs the
120-/200-pt hints (which teach the multi-turn session and the depth-3 chain).
No `[bio]` classifier trip this round (the framing is plain jailbreak content).

### pwn-ai → the rdi argument is now unavoidable

Before: `win(key)` compared `key == 0xc0ffee` and then read a plaintext
`flag.txt`, so a solver could return **past** the check to the inner flag-printer
and skip the argument. Now `win()` **decrypts** `flag.enc` with the key in `rdi`
(XOR keystream, `cipher.h`); the flag ships only encrypted, there is no plaintext
copy, and no address prints the flag without `0xc0ffee` in `rdi`. The `0xc0ffee`
constant stays visible (`cmp rdi, 0xc0ffee`) so the key is still discoverable.

Code: `challenge/binary.c`, `cipher.h`, `mkenc.c`, two-step `Makefile`, Dockerfile
ships `flag.enc` (not `flag.txt`); addresses now `win 0x4012b8`, `pop rdi 0x4012b3`.
`solution/exploit.py` + `distfiles/binary` updated.

Verification: exploit solves the live container; a wrong key and a return-to-printer
both yield only static. 2026-11 blind re-test: a fresh agent solved in **~5 calls**
with the full ROP chain (it had to reverse the decrypt to see the key is used) —
so the clean solve is unchanged (~5–6, entry/mid tier) and only the cheaper
shortcut is gone.

### viking-ai → the compact SSRF bypass is closed

A 2026-11 blind re-test solved viking-ai in **~10 calls** by reaching straight for
the textbook compact IPv4-mapped IPv6 literal `[::ffff:7f00:1]` — too cheap for the
hard tier. The `/fetch` loopback filter was a pure string blocklist; it now also
**parses** the host (`net.ParseIP`) and rejects loopback/unspecified **when the
address is written compressed** (`strings.Contains(host, "::")`). That kills every
compact IPv4-mapped spelling (`::1`, `::ffff:127.0.0.1`, `::ffff:7f00:1`,
`::ffff:7f00:0001`, `0::ffff:7f00:1`, …) in one check. The escape left is the
**fully-expanded, eight-group** literal `[0:0:0:0:0:ffff:7f00:1]`: same
`127.0.0.1`, but no `::`, so the parser never looks at it. A non-obvious step once
every compact form `403`s.

Harder-only and still solvable the documented way: the bypass is still a loopback
literal, so it works on the firewalled Azure deploy (no outbound). Redirect- and
DNS-name-based bypasses were considered but don't fit the containment model (no
outbound, no attacker-reachable non-loopback host). In Go the decimal/octal/`0x`
integer spellings don't dial at all (`ParseIP` returns nil and the dialer won't
resolve a bare integer), so they're a dead end regardless; a few are listed in the
blocklist for completeness.

Code: `challenge/main.go` (`net` import + the parse-and-reject check).
`solution/solve.py`, `solution/README.md`, `metadata.yml` (near-answer hint) and
`docs/ai-mode.md` re-pointed to the expanded literal. Verified: `solve.py` reads
the flag from a freshly built container; `[::ffff:7f00:1]` and every compact form
now `403`, both fully-expanded forms reach the console. Hint costs unchanged
(35/120/150); the near-answer hint now gives the expanded literal.

Blind re-test of the hardened version (fresh zero-context agent, 35-call budget):
**solved in 25 calls** via `[0:0:0:0:0:ffff:7f00:1]`. It reached every compact
IPv4-mapped form and found them `403`, then "sustained enumeration" turned up the
zero-expanded form that the filter normalises past. So the clean solve moved from
~10 back into the hard tier (17–28), and the intended route stays discoverable
black-box — harder, not unsolvable.

### decode-ai → the decoy's second member is buried behind filler

The blind re-test noted the decoy was passable on a plain "incorrect" alone: the
real second gzip member sat right at the first member's trailer, so a solver who
submitted the decoy flag, got rejected, and applied the same gzip-header trick one
offset over found the real flag cheaply — making the 150-pt near-answer hint look
over-provisioned (and rule #1 forbids lowering it). So the **decoy was
strengthened** instead: a run of deterministic, random-looking **filler** now sits
between the two gzip members (`PAD_LEN = 48`). The leftover bytes after the decoy
now read as undifferentiated junk; `gzip.decompress` still raises, but the
known-plaintext header trick applied at the boundary **fails**, and the solver has
to realise the real member is *behind* the filler and **slide** the header check
along the trailing bytes to find its offset and key.

Harder-only and still solvable: the real flag is never present in the decoy
stream, and `solution/solve.py` scans for the member and recovers it. Code:
`challenge/encode.py` (`_pad()`, `find_gzip_member()`, regenerated
`distfiles/encoded.txt`), `solution/solve.py`, `solution/README.md`, `metadata.yml`
(the 150 hint now describes the slide; costs unchanged 40/90/150).

### Left unchanged this pass (deliberately)

- **meow-ai** — the unintended `TAR_OPTIONS=--checkpoint-action=exec` vector is
  fine for an entry-tier first-blood challenge (the handover said harden only to
  push it mid-tier). Left as-is.
- **rsa-ai** — more margin was optional and the only verification path is
  SageMath/LLL, which isn't available in this environment, so changing it could
  not be re-verified end-to-end (the rule is: re-verify every change). Left as-is
  rather than ship an unverifiable edit; a future session with Sage can reduce the
  leaked low bits of `d` and re-blind-test before/after.

## Hint pricing

Rule: **cost ≈ (fraction of the remaining work the hint removes) × challenge
value**, cheap early nudges and expensive near-answer hints, and **never lower a
cost** (cheaper help = easier challenge, which rule #1 forbids). Applied at the
"surgical" magnitude (option B): near-answer hints → ~0.33×value, source
(white-box) hints → ~0.26×value, nudge/method first-hints kept; the two
measured-decisive cheap hints (`decode-ai`, `mono-ai`) got a new cheap nudge rung
inserted beneath them and their decisive hint re-priced up.

Measured anchors: `decode-ai` and `mono-ai`'s old 30-pt first hints each took a
stalled agent to the flag in **~4 calls** (baseline hint-on-stall) — near-decisive,
so underpriced. Other costs are set structurally from each hint's content
(nudge / technique / source / exact-answer); fresh after-hint measurement for the
crypto/forensics set is partly blocked by the same `[bio]` classifier and is left
for a future non-tripping model.

Final costs (old → new; `+Nn` = new nudge rung):

| Challenge | Value | Hint ladder (old → new) |
|---|---|---|
| noter-ai | 400 | 30 (method, kept) · 80**→130** (near) |
| api-ai | 450 | 35 (method, kept) · 60**→120** (source) · 90**→150** (near) |
| robot-ai | 450 | 35 (method, kept) · 60**→120** (source) · 90**→150** (near) |
| meow-ai | 400 | 30 (nudge, kept) · 90**→130** (near) |
| pwn-ai | 500 | 40 (method, kept) · 70**→130** (source) · 100**→160** (near) |
| git-ai | 500 | 35 (method, kept) · 90**→160** (near) |
| operator-ai | 400 | 30 (method, kept) · 80**→130** (near) |
| julius-ai | 400 | **+30n** (new nudge) · 30**→90** (decisive, measured +5 calls) · 70**→130** (near) |
| rsa-ai | 450 | 30 (nudge, kept) · 90**→150** (near) |
| viking-ai | 450 | 35 (nudge, kept) · 60**→120** (source) · 90**→150** (near; text re-pointed to the fully-expanded literal after the filter was hardened) |
| flagception-ai | 450 | **+30n** (new nudge) · 60 (method, kept) · 30**→90** (decisive, measured +4 calls) · 100**→150** (near) |
| decode-ai | 450 | **+40n** (new nudge) · 30**→90** (decisive, measured ≈4 calls) · 80**→150** (near) |
| mono-ai | 450 | **+40n** (new nudge) · 30**→90** (decisive, measured ≈4 calls) · 70**→150** (near) |
| marvin-llm | 500 | 40 (nudge) · 90**→120** (method: now teaches the multi-turn session + depth, not composition) · 200 (near: full multi-turn + depth-3 walk-through) — set for the final-boss rebuild |

Hints are bought **cheapest first**: `ctf.sh up` makes a challenge's strictly
cheaper hints the CTFd prerequisites of each hint, and the `ctf_hints` plugin
refuses a purchase out of order (CTFd itself only checks when a hint is opened).
The ladders were tuned as ladders, each rung raising the odds of a solve on top
of the ones below, so the costs above are kept as they are and add up: the
near-answer hint of `robot-ai` costs 35 + 120 + 150 = 305 in all, the most
expensive ladders are `marvin-llm` (360 of 500), `flagception-ai` (330 of 450)
and `pwn-ai` (330 of 500). Two hints of the same cost would not depend on each
other (no AI-modus challenge has such a pair).

A hint's cost is charged in the challenge's own bracket, and a team spends its
combined points on hints (a bracket can go negative). Under this table, buying
every hint on a challenge stays under its value, so a team that hints-then-
solves still nets positive (at least 120 points). Changing a hint's cost/text is picked up by
`./ctf.sh up`; changing a `value` needs `--reimport`, so difficulty and hint
costs — not point values — are the mid-event tuning levers.

## Blind re-test (2026-11): clean runs + hint-on-stall

The whole bracket was re-blind-tested with fresh zero-context agents to confirm
the tiers held and to ground the hint pricing in measured calls-after-hint.

Clean runs (no hints), tool-calls to solve:

| Challenge | Clean | Challenge | Clean |
|---|---|---|---|
| api-ai | 5 | git-ai | 17 |
| noter-ai | 6 | viking-ai | 17 |
| robot-ai | 7 | operator-ai | 24 |
| meow-ai | 7 | rsa-ai | 36 |
| pwn-ai | ~5 (earlier) | julius-ai | not solved (~22) |
| decode-ai | not solved (~34) | flagception-ai | not solved (~43) |
| mono-ai | `[bio]` blocked | marvin-llm | not solved @28 (rebuilt — see above) |

Every solved challenge returned the correct flag and rejected its decoys; the
three hint-gated ones failed clean exactly where intended. The entry tier stays
5–7 calls, the hard tier 17–36, nothing collapsed.

> Note: `viking-ai`'s 17 and `marvin-llm`'s result above predate the later
> hardening passes documented in "Changes made". `viking-ai`'s compact bypass
> (which a separate run landed in ~10) is now closed — the hardened version was
> re-blind-tested at **25 calls** via the zero-expanded literal; `marvin-llm` was
> rebuilt into the final boss and its latest blind run is **not solved at 28
> calls**.

Hint-on-stall (calls used after each hint fed, cheapest first):

| Challenge | After H1 | After H2 | After H3 | Decisive |
|---|---|---|---|---|
| decode-ai | +14 stuck | +5 stuck | **+1 solved** | H3 (exact gzip header) — 3-rung ladder validated |
| julius-ai | **+5 solved** | — | — | **H1** (was 30) |
| flagception-ai | **+4 solved** | — | — | **H1** (was 30) |

This confirmed every ladder gets a stalled solver to the flag, and showed that
`julius-ai` and `flagception-ai`'s cheapest hint was in fact the decisive one
(solve in 4–5 calls) — the same underpricing the handover flagged for
`decode-ai`/`mono-ai`. Both were given the same fix (new vague nudge rung at 30 +
the decisive hint repriced to 90), reflected in the table above. `decode-ai`'s
own ladder needed no change: a solver genuinely needs the exact-bytes H3.
`mono-ai` could not be re-measured this round (`[bio]` classifier); its baseline
+4-after-H1 stands.

## Timed hint-on-stall re-test of the three hardened challenges (2026-11)

The three challenges changed in the hardening passes above (`marvin-llm`,
`viking-ai`, `decode-ai`) were re-run with the full timed hint-on-stall protocol:
a fresh zero-context `general-purpose` agent each, black-box, a ~10-minute clean
phase, then the challenge's own paid hints fed in order (verbatim) with another
~10 minutes each, stopping at two hints / 30 minutes total.

| Challenge | Clean | +Hint 1 | +Hint 2 | Verdict |
|---|---|---|---|---|
| viking-ai | ✗ 19 | ✓ **solved +3 (22)** | — | H1 (35) decisive |
| marvin-llm | ✗ 16 | ✗ (33) | ✓ **solved +3 (36)** | both H1 (40) + H2 (120) load-bearing |
| decode-ai | ✗ 20 | ✗ (34) | ✗ (44) | needs H3 (150); hint-gated as designed |

- **No challenge was solved on the clean run** — all three are correctly above
  entry difficulty.
- **viking-ai**: the agent found the SSRF and an easy `127.x` loopback bypass, but
  that reaches only the shop (`0.0.0.0`-bound), not the `127.0.0.1`-exact admin, so
  it chased RFC1918 red herrings and stalled; the 35-pt "IPv4-mapped IPv6" nudge
  then closed it in 3 calls via `[0:0:0:0:0:ffff:127.0.0.1]`. The `.1`-exact bind is
  the crux that makes the easy loopback trick a dead end.
- **marvin-llm (capstone)**: the clean run never even emitted the flag — the agent
  read Marvin as stateless and missed the held-session frame-then-ask. Hint 1 got
  it there and it leaked the (flagless) VAULT-7 prompt and mapped the output
  filter, but it wrongly concluded "the emit branch ignores formatting" because
  depth-2 was redacted; only hint 2 ("he applies every encoding you name … how many
  it takes") pushed it to the depth-3 chain. It reported both hints were
  load-bearing and that the bot "leaks only taunts … never anything constructive" —
  i.e. the oracle-silencing holds.
- **decode-ai**: the agent peeled cleanly to the XOR blob and (with hint 2) tried
  gzip as known plaintext, but only at key lengths 1–6 — never the actual 8-byte
  key — so it never recovered even the first member, let alone reached the buried
  decoy. It needed H3 (the 150-pt near-answer: XOR the first 8 bytes with the gzip
  header for the 8-byte key, then slide past the filler). This confirms the
  decoy-hardening and that the 150 hint is justified, not over-provisioned.

## Reproducing / extending

- Hosted challenges: build each `challenge/` with Docker, run on its event port
  (robot-ai 5006, noter-ai 5007, api-ai 5008, viking-ai 5009, marvin-llm 5010,
  meow-ai nc 4446, pwn-ai nc 1246), then run its `solution/solve.py` / `exploit.py`.
- Blind tests: one fresh `general-purpose` subagent per run, black-box, told to use
  only the player-facing interface (no reading repo source). Clean run first
  (~25-call budget), then hint-on-stall (feed the next `metadata.yml` hint verbatim
  when it says "HINT PLEASE", counting calls-after-hint).
- If a safety classifier stops a subagent (crypto/forensics/LLM content trips
  `[bio]`), record it and do **not** retry around it or hand-substitute the solve.

## Point re-scale for cross-bracket scoreboard parity (2026-11)

The AI-modus bracket was re-scaled from its flat **400–500** band down onto the
**same ruler as the classic bracket** (classic runs 10–180: hardest `viking` 180,
`binary` 150, median ~50). Rationale: both brackets are *meant to be played with
AI*, so their scores should correlate; the combined **"All"** scoreboard was
badly skewed when one AI-modus solve (400–500) outweighed every classic solve a
team had (10–180 each). The re-scale also makes value track **measured AI
effort**: challenges a fresh blind agent cracked in ~2 min drop near the easy
classic tier; the `marvin-llm` capstone (never solved blind) becomes the clear
top of *either* bracket.

This is **not** a difficulty change — challenge mechanics and the hint ladders'
*structure* are untouched, so rule #1 ("never make a challenge easier") still
holds on the levers that set difficulty. Only the point magnitudes are rebased.
Ordered by measured AI difficulty (this session's blind test + the call counts
above):

| Challenge | Old → New value | Hint ladder old → new (EN=NO) |
|---|---|---|
| api-ai | 450 → **35** | 35/120/150 → 5/10/15 |
| robot-ai (was marvin-ai) | 450 → **35** | 35/120/150 → 5/10/15 |
| noter-ai | 400 → **30** | 30/130 → 10/15 |
| meow-ai | 400 → **30** | 30/130 → 10/15 |
| pwn-ai | 500 → **40** | 40/130/160 → 5/10/20 |
| git-ai | 500 → **50** | 35/160 → 10/25 |
| rsa-ai | 450 → **70** | 30/150 → 10/35 |
| operator-ai | 400 → **80** | 30/130 → 10/40 |
| viking-ai | 450 → **100** | 35/120/150 → 10/30/40 |
| julius-ai | 400 → **120** | 30/90/130 → 10/35/50 |
| flagception-ai | 450 → **150** | 30/60/90/150 → 10/25/40/55 |
| mono-ai | 450 → **150** | 40/90/150 → 15/45/60 |
| decode-ai | 450 → **170** | 40/90/150 → 15/50/65 |
| marvin-llm | 500 → **250** | 40/120/200 → 20/55/90 |

Hint costs were scaled down with the values (keeping the doc's "cost ≈ fraction of
remaining work × value" shape and the "buy-all-hints < value → a hints-then-solve
team still nets positive" invariant — that is why `api-ai`/`robot-ai` sit at 35,
not 30: three distinct 5-multiple rungs can't sum under 30). `metadata.yml`
`value:` and `hints:`/`hints_no:` costs updated for all 14; hint **text** and the
flags are unchanged.

> **A `value` change needs `./ctf.sh up --reimport`** to reach a live CTFd (plain
> `up` only syncs hint costs/text and descriptions), so this is a
> **before-the-event** change. Measured AI solve speeds that drove the ordering:
> entry tier (api/marvin/noter/meow/pwn) ~2–4 min no-hint; mid (git/rsa/operator/
> viking) ~5–26 min no-hint; hard (julius +H1, flagception +H2, mono/decode
> hint-gated); capstone (marvin-llm) needs H1+H2, unsolved blind.
