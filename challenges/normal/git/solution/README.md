# git — the flag is in the history

**Category:** forensics · **Flag:** `flag{protect_your_git}`

The download `gitIsGood.zip` unpacks to a folder with a `flag.txt` that reads
`flag{REDACTED}` — and a `.git/` directory. Redacting a file in the working tree
does nothing to the previous versions git has already committed.

### Solve

```bash
unzip gitIsGood.zip
cd gitIsGood

cat flag.txt          # flag{REDACTED}  — redacted at HEAD

git log --oneline     # three commits, all "Edited files"
# 90dc6f9  (HEAD, redacted)
# dbd0803
# 9bafec0  (redacted)
```

The flag was committed before it was redacted. Read `flag.txt` as it was at the
middle commit — no need to even check it out:

```bash
git show dbd0803:flag.txt
# flag{protect_your_git}
```

(Or `git checkout dbd0803 && cat flag.txt`.)

**Lesson:** committing a secret and then "removing" it leaves it in the git history
forever. The fix is to rewrite history (and rotate the secret) — not just delete the
file in a new commit. Hence `flag{protect_your_git}`.

## Debrief: what you learn and how to protect against it

**What you learn:** git keeps every version that was ever committed. Deleting or
redacting a secret in a new commit leaves the old version in the history, one
`git log` away.

**The solve in short:**

1. Unzip and notice the `.git/` folder next to the redacted `flag.txt`.
2. `git log --oneline` shows three commits.
3. Read the file as it was in the middle one: `git show dbd0803:flag.txt`.

**How to protect against it:**

- Keep secrets out of git from the start: `.gitignore` for `.env` files, secrets
  in a secret store, and a scanner that stops the commit (gitleaks as a
  pre-commit hook, GitHub secret scanning with push protection).
- When a secret has been committed, **rotate it first**. Everyone who cloned the
  repo already has it, so the secret must be made worthless.
- Then clean the history with `git filter-repo` (or BFG) and force-push. This is
  the second step, not a replacement for rotating.
- Never publish or zip a folder with its `.git/` directory by accident, e.g. on
  a web server.
