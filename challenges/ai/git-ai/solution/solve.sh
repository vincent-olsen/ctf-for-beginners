#!/usr/bin/env bash
# Solve git-ai from ../distfiles/repo.zip, step by step. Needs git, unzip, python3.
#
#   1. The stale shares: share A v1 in history, share A v2 as a dangling blob.
#   2. The orphan pack: a .pack with no .idx. index-pack it; it holds share A v3
#      and the ops repo's first commit (the bundle's prerequisite).
#   3. The stash holds handover.bundle, an incremental bundle: fetch it into the
#      repo (a plain clone fails) and read the rotated share B.
#   4. Open the vault with share A v3 and share B.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir "$work/repo"
cd "$work/repo"
unzip -q "$here/../distfiles/repo.zip"

echo "== 1. what plain git shows"
echo "share A v1 (history):  $(git log --all -p -- ops/vault.env | grep -m1 '^+VAULT_SHARE_A' | cut -d= -f2)"
blob=$(git fsck --unreachable 2>/dev/null | awk '/unreachable blob/ {print $3}' | head -1)
echo "share A v2 (dangling): $(git cat-file -p "$blob" | cut -d= -f2)"
echo "decoy commit:          $(git fsck --unreachable 2>/dev/null | awk '/unreachable commit/ {print $3}')"

echo "== 2. the pack without an index"
git count-objects -v | grep garbage
pack=$(ls .git/objects/pack/*.pack)
echo "$pack (no .idx)"
git index-pack "$pack" >/dev/null
share_a=""
for obj in $(git verify-pack -v "${pack%.pack}.idx" | awk '$2 == "blob" {print $1}'); do
  line=$(git cat-file -p "$obj" | grep -a '^VAULT_SHARE_A=' || true)
  [ -n "$line" ] && share_a=${line#VAULT_SHARE_A=}
done
echo "share A v3 (in the pack): $share_a"

echo "== 3. the incremental bundle in the stash"
git show refs/stash:handover.bundle > "$work/h.bundle"
head -c 16 "$work/h.bundle"; echo
git clone -q "$work/h.bundle" "$work/clone" 2>&1 | head -2 || true
git fetch -q "$work/h.bundle" main:refs/heads/ops
share_b=$(git show ops:share-b.txt | grep '^VAULT_SHARE_B=' | cut -d= -f2)
echo "share B (rotated, from the bundle): $share_b"

echo "== 4. open the vault"
VAULT_SHARE_A="$share_a" VAULT_SHARE_B="$share_b" python3 vault.py open
