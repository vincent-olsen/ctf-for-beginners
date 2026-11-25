#!/usr/bin/env bash
# Build the git-ai distfile (AI-modus): a repo where no object holds the flag.
#
# The original `git` hides the flag in plain history (`git log` -> checkout).
# The first AI-modus cut put it in a dangling commit, the second in a dangling
# blob behind a decoy commit, and an assistant still solved that in four
# commands: decompress every object, grep for flag{. So now the flag is only
# ever stored ENCRYPTED, and opening it takes git knowledge in three places.
# (A draft that kept share B as plain text in the stash's index commit fell in
# five commands: `git log --all -p` prints that commit's diff. The next, with the
# current share A as a plain dangling blob, fell in seven.)
#
#   * vault.bin (on main) is the flag, sealed by vault.py (on main) with
#     key = share A XOR share B; neither share is in the current tree.
#   * Share A comes in three versions, and only the newest opens the vault:
#     - v1 in plain history (ops/vault.env, removed in a "rotate share A" commit);
#     - v2 `git add`ed as .env.prod, then reset and deleted: a dangling BLOB that
#       `git fsck` reports. It looks like the answer and opens nothing;
#     - v3, the current one, only in an ORPHAN PACKFILE: .git/objects/pack/ holds
#       a pack-*.pack whose .idx is gone. Git cannot read a pack without its
#       index, so `git fsck`, `git cat-file --batch-all-objects` and `git log`
#       never see it, and the pack is zlib-compressed, so grep finds nothing.
#       `git count-objects -v` calls it garbage. `git index-pack` rebuilds the
#       index, and then `git verify-pack -v` / `git cat-file -p` read it.
#   * Share B: in a GIT BUNDLE (handover.bundle, from the ops team's own little
#     repo), parked in a stash. The reflog is wiped, so `git stash list` is
#     empty, but refs/stash survives (`git log --all` shows it). A bundle is a
#     packfile: its objects are zlib-compressed inside the blob, so grepping
#     every object, or `git log -p`, never shows the share. And it is an
#     INCREMENTAL bundle: it only holds the ops repo's second commit ("rotate
#     share B"), and needs the first as a prerequisite. `git clone` of it fails
#     with "lacks these prerequisite commits". That first commit (with the old,
#     stale share B) is in the same orphan pack as share A v3, so the two hiding
#     places chain: index-pack first, then `git fetch` the bundle into this repo.
#   * The old decoy stays: a deleted branch whose flag.txt says "keep digging".
#
# Commit dates are fixed, so the commit ids are stable from build to build.
#
# Run:  bash make_repo.sh   -> writes ../distfiles/repo.zip  (needs git, zip, python3)
set -euo pipefail
cd "$(dirname "$0")"

REAL_FLAG="flag{two_shares_one_stash_zero_plaintext}"
DECOY_FLAG="flag{this_one_is_a_decoy_keep_digging}"
SHARE_A_OLD="5b0e8c7d2f61a4398e17c05b6d22f9a1"
SHARE_A_V2="c4a1f07e9b3d5268e0f71a4c8d2b6e95"
SHARE_A="e93b27d4a0c58f1e6b7d34a2c91f0e58"
SHARE_B_OLD="2d81c6f04e9ab35d7c0e18f2a64b9d07"
SHARE_B="7f2d94e1b06c3a58d1e8f42a90b7c6d3"
BUILD="build"
rm -rf "$BUILD"
git init -q -b main "$BUILD"
cd "$BUILD"
git config user.email "dev@corp.local"
git config user.name "Careless Dev"
git config gc.auto 0            # never auto-prune the unreachable objects

T=1700000000                    # each step one hour later, so hashes are stable
tick() { T=$((T + 3600)); export GIT_AUTHOR_DATE="@$T +0100" GIT_COMMITTER_DATE="@$T +0100"; }

# --- innocuous history ---------------------------------------------------------
tick
cat > README.md <<'EOF'
# internal-tool

Small internal helper. Nothing to see here.
EOF
printf 'def main():\n    print("hello")\n' > app.py
git add . && git commit -q -m "initial import"

tick
echo "- [ ] wire up real auth" >> README.md
git add . && git commit -q -m "jot down some TODOs"

# --- the vault tool, and share A (OLD) committed by mistake --------------------
tick
cat > vault.py <<'EOF'
#!/usr/bin/env python3
"""Seal or open vault.bin.

The key is never committed. It is split into two shares, held by two people,
each 16 bytes of hex: VAULT_SHARE_A and VAULT_SHARE_B (environment variables).
key = A xor B, and the vault is XORed with SHA-256(key || counter) blocks.

    VAULT_SHARE_A=... VAULT_SHARE_B=... python3 vault.py open
    VAULT_SHARE_A=... VAULT_SHARE_B=... python3 vault.py seal < secret.txt
"""
import hashlib
import os
import sys


def keystream(key, n):
    out, i = b"", 0
    while len(out) < n:
        out += hashlib.sha256(key + i.to_bytes(4, "big")).digest()
        i += 1
    return out[:n]


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def main():
    key = xor(bytes.fromhex(os.environ["VAULT_SHARE_A"]), bytes.fromhex(os.environ["VAULT_SHARE_B"]))
    if sys.argv[1:] == ["seal"]:
        data = sys.stdin.buffer.read()
        with open("vault.bin", "wb") as f:
            f.write(xor(data, keystream(key, len(data))))
    elif sys.argv[1:] == ["open"]:
        with open("vault.bin", "rb") as f:
            data = f.read()
        sys.stdout.buffer.write(xor(data, keystream(key, len(data))))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
EOF
mkdir -p ops
printf '# local testing only\nVAULT_SHARE_A=%s\n' "$SHARE_A_OLD" > ops/vault.env
git add . && git commit -q -m "add vault.py (two-share key) + my share for local testing"

# --- DECOY: a flag on a branch that then gets deleted (a dangling commit) ------
tick
git checkout -q -b feature/prod-secret
printf '%s\n' "$DECOY_FLAG" > flag.txt
git add flag.txt
git commit -q -m "TEMP: drop prod flag here so I can test; MUST remove before pushing"
git checkout -q main
git branch -qD feature/prod-secret

# --- rotate share A, because the old one is in history --------------------------
tick
git rm -q ops/vault.env
printf 'ops/*.env\n.env*\n' > .gitignore
git add .gitignore
git commit -q -m "rotate share A (the old one leaked into git); never commit shares again"

# --- share B: in an incremental bundle from the ops repo, parked in a stash ------
# The ops repo has two commits: B1 (old share B) and B2 (rotated, current). The
# bundle carries B2 only and lists B1 as a prerequisite. B1's objects go into the
# orphan pack below, together with share A v3.
tick
OPS="$(mktemp -d)"
(
  cd "$OPS"
  git init -q -b main .
  git config user.email "ops@corp.local"
  git config user.name "Ops"
  # A long handover note, so the rotated version is stored in the bundle as a
  # DELTA against this one: without the prerequisite, the bundle's pack data
  # cannot be unpacked by hand either.
  handover_note() {
    printf 'Vault handover, ops copy. Share B: %s\n\n' "$1"
    for i in $(seq 1 40); do
      printf 'Step %02d: confirm with the second share holder over the phone, never by mail or chat.\n' "$i"
    done
    printf '\nVAULT_SHARE_B=%s\n' "$2"
  }
  handover_note "first issue" "$SHARE_B_OLD" > share-b.txt
  git add share-b.txt
  git commit -q -m "share B for the vault handover"
  git tag first
  T=$((T + 60)); export GIT_AUTHOR_DATE="@$T +0100" GIT_COMMITTER_DATE="@$T +0100"
  handover_note "rotated" "$SHARE_B" > share-b.txt
  git commit -qam "rotate share B"
  git bundle create -q handover.bundle HEAD main ^first
)
cp "$OPS/handover.bundle" handover.bundle
git add -f handover.bundle
git stash push -q -m "parking the ops handover bundle, do not push"

# --- share A v2: staged, reset, deleted -> a dangling blob (stale) ----------------
tick
printf 'VAULT_SHARE_A=%s\n' "$SHARE_A_V2" > .env.prod
git add -f .env.prod
git reset -q HEAD .env.prod
rm -f .env.prod

# --- share A v3 (current) and the ops repo's first commit: only in a packfile ---
# whose index is gone. Packed in the ops scratch repo; only the .pack is copied.
(
  cd "$OPS"
  blob=$(printf 'VAULT_SHARE_A=%s\n' "$SHARE_A" | git hash-object -w --stdin)
  { git rev-list --objects first; echo "$blob"; } | git pack-objects -q pack-out >/dev/null
)
packfile=$(ls "$OPS"/pack-out-*.pack)
cp "$packfile" ".git/objects/pack/pack-${packfile##*/pack-out-}"
rm -rf "$OPS"

# --- seal the vault with the current shares ------------------------------------
tick
printf 'The vault is open. Both shares, found the hard way.\n%s\n' "$REAL_FLAG" |
  VAULT_SHARE_A="$SHARE_A" VAULT_SHARE_B="$SHARE_B" python3 vault.py seal
git add vault.bin
git commit -q -m "seal the vault (the shares are NOT in git)"

tick
echo "print('bye')" >> app.py
git add . && git commit -q -m "cleanup: removed the throwaway secret branch, all clear"

# --- check, then wipe the reflog -----------------------------------------------
CHECK="$(mktemp -d)"
git show 'refs/stash:handover.bundle' > "$CHECK/handover.bundle"
if git clone -q "$CHECK/handover.bundle" "$CHECK/ops" 2>/dev/null; then
  echo "the bundle should not clone on its own (it needs its prerequisite)" >&2; exit 1
fi
# Nor can its pack data be unpacked by hand: share B must be a delta against
# the prerequisite's blob, which only the orphan pack holds.
( cd "$CHECK" && git init -q raw && python3 - handover.bundle raw.pack <<'PY'
import sys
data = open(sys.argv[1], "rb").read()
open(sys.argv[2], "wb").write(data[data.index(b"PACK"):])
PY
  cd raw && { git unpack-objects -r -q < ../raw.pack 2>/dev/null || true; }
  git cat-file --batch-all-objects --batch > ../raw-objects.txt 2>/dev/null || true )
if grep -aq "$SHARE_B" "$CHECK/raw-objects.txt"; then
  echo "share B can be unpacked from the bundle without its prerequisite" >&2; rm -rf "$CHECK"; exit 1
fi
cp -r .git "$CHECK/repo.git"
( cd "$CHECK" && git --git-dir=repo.git index-pack repo.git/objects/pack/pack-*.pack >/dev/null \
  && git --git-dir=repo.git fetch -q handover.bundle main:refs/heads/ops ) \
  || { echo "index-pack + fetch of the bundle failed" >&2; rm -rf "$CHECK"; exit 1; }
share_b=$(git --git-dir="$CHECK/repo.git" show ops:share-b.txt | grep VAULT_SHARE_B | cut -d= -f2)
rm -rf "$CHECK"
[ "$share_b" = "$SHARE_B" ] || { echo "share B from the bundle is wrong" >&2; exit 1; }
opened=$(VAULT_SHARE_A="$SHARE_A" VAULT_SHARE_B="$share_b" python3 vault.py open)
grep -qF "$REAL_FLAG" <<<"$opened" || { echo "vault round-trip failed" >&2; exit 1; }
for stale in "$SHARE_A_OLD" "$SHARE_A_V2" "$SHARE_A:$SHARE_B_OLD"; do
  a=${stale%%:*}; b=$share_b; [[ "$stale" == *:* ]] && b=${stale##*:}
  stale_out=$(VAULT_SHARE_A="$a" VAULT_SHARE_B="$b" python3 vault.py open | od -An -c | tr -d ' \n')
  if [[ "$stale_out" == *"flag{"* ]]; then
    echo "a stale share opens the vault" >&2; exit 1
  fi
done
# Dump to a file before grepping: with pipefail, `... | grep -q` can fail on SIGPIPE.
DUMP="$(mktemp)"
git cat-file --batch-all-objects --batch > "$DUMP"
if grep -aq -e "flag{two_shares" -e "$SHARE_B" -e "$SHARE_A" "$DUMP"; then
  rm -f "$DUMP"
  echo "the real flag, share B or the current share A is readable as a plain object" >&2; exit 1
fi
rm -f "$DUMP"
if grep -rqa -e "$SHARE_A" -e "$SHARE_B" .git; then
  echo "the current share A or share B is in plain bytes somewhere under .git" >&2; exit 1
fi
# ...but index-pack does bring share A back.
RECOVER="$(mktemp -d)"
cp -r .git "$RECOVER/.git"
( cd "$RECOVER" && git index-pack .git/objects/pack/pack-*.pack >/dev/null \
  && git cat-file --batch-all-objects --batch > objects.txt && grep -aq "$SHARE_A" objects.txt ) \
  || { echo "share A cannot be recovered with index-pack" >&2; rm -rf "$RECOVER"; exit 1; }
rm -rf "$RECOVER"
git reflog expire --expire=now --all 2>/dev/null || true
rm -rf .git/logs
# NOTE: deliberately NOT running `git gc --prune`, which would delete the
# unreachable objects and ruin the challenge.

cd ..
rm -f ../distfiles/repo.zip
( cd "$BUILD" && zip -qr -X ../../distfiles/repo.zip . )
rm -rf "$BUILD"
echo "wrote ../distfiles/repo.zip: share A (current) and the bundle's prerequisite are in an orphan pack; share B in an incremental bundle in refs/stash"
