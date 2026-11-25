# git-ai (AI-modus)

The original `git` challenge hides the flag in plain history: `git log`, then
`git checkout <old-commit>`. Earlier AI-modus versions hid it in a dangling commit,
then in a dangling blob behind a decoy commit. An assistant solved that last one
in four commands by decompressing every object and grepping for `flag{`.

Now **no object in the repository holds the flag**. It exists only encrypted, in
`vault.bin`, and opening it takes three different corners of git.

## What's in the repo

- `vault.bin` and `vault.py` on `main`. `vault.py` explains the scheme:
  `key = share A xor share B` (16 bytes each, hex), and the vault is XORed with
  `SHA-256(key || counter)` blocks. Neither share is in the current tree.
- **Share A, v1:** in plain history (`ops/vault.env`, added "for local
  testing", deleted in "rotate share A"). Stale: with it the vault opens to
  garbage.
- **Share A, v2:** it was `git add`ed as `.env.prod`, then `git reset` and
  deleted, so it is a **dangling blob** that only `git fsck` reports. It looks
  like the answer and is stale too.
- **Share A, v3 (current):** only in an **orphan packfile**:
  `.git/objects/pack/` holds a `pack-*.pack` whose `.idx` is gone. Git can't
  read a pack without its index, so `git fsck`, `git cat-file
  --batch-all-objects` and `git log` never see it. The pack is zlib-compressed,
  so grep finds nothing either. `git count-objects -v` reports it as
  `garbage: 1`.
- **Share B:** in a **stash**. The reflog is wiped, so `git stash list` is empty,
  but `refs/stash` survives (`git log --all` shows "On main: parking the ops
  handover bundle"). The stash holds `handover.bundle`, a **git bundle** from the
  ops team's own repo. A bundle is a packfile, so its contents are
  zlib-compressed inside the blob: neither `git log -p` nor grepping every object
  shows the share. It is **incremental**: it holds only the ops repo's second
  commit ("rotate share B") and needs the first as a prerequisite, so `git clone`
  of it fails with "lacks these prerequisite commits". That first commit (with a
  stale share B) is in the **same orphan pack** as share A v3. `share-b.txt` is a
  long handover note, so the rotated version is stored in the bundle as a
  **delta** against the first one: cutting the pack out of the bundle and running
  `git unpack-objects` gives "unresolved deltas" and no share. The two hiding
  places really do chain together.
- **Decoy:** a deleted branch's commit (dangling) with `flag.txt` =
  `flag{this_one_is_a_decoy_keep_digging}`.

## Intended solve

```bash
unzip repo.zip -d repo && cd repo
git log --all --oneline              # main + the stash commits
git log --all -p -- ops/vault.env    # the OLD share A (rotated out)
git fsck --unreachable               # dangling commit (decoy) + dangling blob
git cat-file -p <blob>               # VAULT_SHARE_A=c4a1f07e...  (v2, stale)

git count-objects -v                 # garbage: 1
ls .git/objects/pack/                # pack-00bc2086....pack, no .idx
git index-pack .git/objects/pack/pack-*.pack
git verify-pack -v .git/objects/pack/pack-*.idx   # a commit, a tree, two blobs
git cat-file -p <that blob>          # VAULT_SHARE_A=e93b27d4...  (v3, current)

git show refs/stash:handover.bundle > ../h.bundle
head -c 16 ../h.bundle               # "# v2 git bundle"
git clone ../h.bundle ../ops         # error: lacks prerequisite commits d059b0c1...
# d059b0c1 is in the orphan pack (after the index-pack above):
git fetch ../h.bundle main:ops
git show ops:share-b.txt             # VAULT_SHARE_B=7f2d94e1...  (rotated, current)

VAULT_SHARE_A=e93b27d4a0c58f1e6b7d34a2c91f0e58 \
VAULT_SHARE_B=7f2d94e1b06c3a58d1e8f42a90b7c6d3 python3 vault.py open
```

Share A v1 or v2 with share B gives garbage. Share A v3 with share B gives:

```
The vault is open. Both shares, found the hard way.
flag{two_shares_one_stash_zero_plaintext}
```

[`solve.sh`](solve.sh) runs these steps on `../distfiles/repo.zip` in a
temporary folder and prints the vault:

```bash
bash solve.sh
```

## Flag

```
flag{two_shares_one_stash_zero_plaintext}
```

## Regenerating the asset

```bash
bash challenge/make_repo.sh       # rebuilds distfiles/repo.zip (needs git, zip, python3)
```

The build checks the round trip and that the stale shares open nothing. It
also checks that neither the flag, share B nor the current share A is readable
in any object or in plain bytes under `.git`, and that `git index-pack`
recovers share A and lets the bundle be fetched, while a plain clone of the
bundle fails. Commit dates are fixed, so commit ids are
stable. The zip bytes still differ between builds because of file times.

## Debrief: what you learn and how to protect against it

**What you learn:** how much a `.git` folder remembers besides the visible
history: dangling objects from a `git add` that was never committed, stashes,
packfiles without an index, and bundles. `git log` shows only a part of it. You
also see that splitting a key in two shares helps little when both shares end up
in the same place.

**The solve in short:**

1. `vault.py` says the key is share A xor share B, and neither is in the tree.
2. Share A in the history (`git log --all -p`) and the one in a dangling blob
   (`git fsck --unreachable`) are both old: the vault opens to garbage.
3. `git count-objects -v` reports garbage: a packfile without its `.idx`.
   Rebuild the index with `git index-pack` and read the current share A.
4. `refs/stash` holds a git bundle. It only fetches once the objects from step 3
   are available: `git fetch ../h.bundle main:ops`, then read share B.
5. Run `vault.py open` with the two current shares.

**How to protect against it:**

- Git forgets almost nothing. A file that was only `git add`ed, or stashed, is
  stored as an object. Keep secrets out entirely: a secret store, `.gitignore`,
  and a scanner as a pre-commit hook (gitleaks) plus push protection on the
  server.
- Rotate a secret that has been in a repo. The old shares in this challenge open
  nothing because they were rotated, which is the part the "ops team" got right.
- Never hand out a copy or zip of a working folder with its `.git/`. Share a
  fresh clone from the server instead: it contains only what the branches reach,
  with no dangling objects, no stash and no stray packfiles.
- Shares of a key belong in different systems with different access.

## How hard it is for an AI

Each draft was given to a fresh assistant with only `repo.zip` and "What is the
ctf flag?". The dangling-blob version fell in 4 commands, a draft with share B as
plain text in the stash in 5, and a draft with the current share A as a plain
dangling blob in 7, and a draft with the orphan pack but a self-contained bundle
in 8 (`git fsck` warns about the index-less pack, so the pack alone is a short
detour). An incremental bundle that stored share B whole fell in 9: the agent cut
the pack out of the bundle and unpacked it by hand. Now share B is a delta
against the prerequisite, so that shortcut is closed.

A 2026-11 re-test reproduced the intended difficulty: a fresh assistant solved
it in ~16 tool calls, ruling out all four decoys (dangling flag, leaked/rotated
env share, dangling-blob share, pre-rotation share), manually decompressing the
index-less pack for the real share A and parsing the bundle's ref-delta opcodes
for the rotated share B.

## Solving it with an AI (prompts)

- **Cold open:** "I unzipped a git repo (`.git` included). There's an encrypted `vault.bin` and a `vault.py` that needs two key shares. Find both shares anywhere in the repo, including unreachable objects and stashes, and open the vault."
- **If it stalls:** "Both share A values you can see are stale. Look in `.git/objects/pack/`: is there a `.pack` without an `.idx`? Rebuild it with `git index-pack`, then read the blob. Share B is in `refs/stash` inside `handover.bundle`, an incremental bundle: once the pack is indexed, `git fetch h.bundle main:ops` inside the repo and read `ops:share-b.txt`."

## Difficulty-tuning re-test (2026-11)

A fresh zero-context agent solved it clean in **17 tool calls**, ruling out all three decoy layers (dangling flag, stale shares) before the index-less pack + thin-bundle delta. The solve path is unchanged by the 2h45-event tuning pass; what changed is
hint pricing: 35/90 -> 35/160 (near-answer/source hints repriced toward their marginal value,
no cost lowered). Full cross-challenge detail in [docs/ai-difficulty-tuning.md](../../../../docs/ai-difficulty-tuning.md).
