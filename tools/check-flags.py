#!/usr/bin/env python3
"""Check that every challenge's real flag is stored in its challenge/ folder.

For each challenges/<group>/<name>/metadata.y[a]ml, the top-level `flag:` value
must appear literally in at least one file under that challenge's challenge/
directory (flag.txt, `ENV FLAG=...`, source, a plaintext asset). A flag that
drifts between metadata.yml (what CTFd accepts) and challenge/ (what the
container or generator holds) makes the challenge unsolvable, and nothing else
in the repo would notice before the event.

Some challenges legitimately do not store the flag literally; they are listed
in ALLOWLIST below, each with the reason. The check is strict both ways: an
allowlisted challenge whose flag *is* found literally is reported as a stale
entry, so the list cannot rot. Challenges without a `flag:` key (infrastructure
such as noter5-backend) are listed in NO_FLAG with the same two-way check.

The output names challenges only. Flag values are never printed, not even in
parse errors, because the log of a CI run is readable by everyone with access
to the repository.

Usage: tools/check-flags.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Challenge folder name -> why its flag is not stored literally under challenge/.
# Keep a reason on every line; add an entry only after checking the challenge.
ALLOWLIST = {
    # Static distfile challenges whose asset hides the flag in encoded form.
    "decode1": "challenge/readme holds the flag base64-encoded",
    "decode2": "challenge/readme holds the flag base64-then-base32-encoded",
    "decode3": "challenge/readme holds the flag base32/morse/hex/base64-encoded",
    "julius": "challenge/README.md holds the flag as a Caesar-shifted ciphertext",
    "birds": "birds.png draws the flag as a Birds-on-a-Wire cipher",
    "flagception": "flags.png spells the flag in maritime signal flags",
    "qrcode": "the flag is split into one QR-code PNG per character; no plaintext copy",
    "unk": "the asset is a corrupted .docx (zip); challenge/ is only a .keep and the flag is inside the compressed document",
    "pdfcrypt": "the asset is an AES-encrypted PDF; challenge/ is only a .keep and the flag is inside the encrypted stream",
    "git": "the real flag exists only in the git history inside distfiles/gitIsGood.zip; challenge/gitIsGood/flag.txt is the redacted working-tree copy",
    # OSINT: the answer is derived from live third-party state, not stored in the repo.
    "art": "OSINT: the flag is built from a live news article; art.png only carries the clue",
    "email": "OSINT: the flag is derived from a commit author email on a live GitHub account",
}

# Challenge folder name -> why it has no `flag:` key in its metadata.
NO_FLAG = {
    "noter5-backend": "infrastructure for noter5; it has no player-facing flag",
}

# A top-level `flag:` line. Values are single-line scalars; anything else is
# reported without echoing the line (a parse error must not leak the value).
FLAG_LINE = re.compile(r"^flag:[ \t]*(.*?)[ \t]*$")
DOUBLE_QUOTED = re.compile(r'^"((?:[^"\\]|\\.)*)"[ \t]*(?:#.*)?$')
SINGLE_QUOTED = re.compile(r"^'((?:[^']|'')*)'[ \t]*(?:#.*)?$")


def read_flag(metadata: Path):
    """Return the flag string, None if the file has no flag key, or raise ValueError."""
    values = [
        m.group(1)
        for m in map(FLAG_LINE.match, metadata.read_text(encoding="utf-8").splitlines())
        if m
    ]
    if not values:
        return None
    if len(values) > 1:
        raise ValueError("more than one top-level flag: key")
    raw = values[0]
    if m := DOUBLE_QUOTED.match(raw):
        try:
            return json.loads(f'"{m.group(1)}"')
        except ValueError:
            raise ValueError("flag: has an escape sequence this check cannot read") from None
    if m := SINGLE_QUOTED.match(raw):
        return m.group(1).replace("''", "'")
    if not raw or raw[0] in "\"'|>[{&*!%@`#":
        raise ValueError("flag: is empty or not a single-line scalar")
    return raw.split(" #", 1)[0].strip()


def found_under(challenge_dir: Path, flag: str) -> bool:
    needle = flag.encode("utf-8")
    for path in sorted(challenge_dir.rglob("*")):
        if path.is_file() and not path.is_symlink():
            try:
                if needle in path.read_bytes():
                    return True
            except OSError:
                continue
    return False


def main():
    metadata_files = sorted(
        p
        for pattern in ("metadata.yml", "metadata.yaml")
        for p in (ROOT / "challenges").glob(f"*/*/{pattern}")
    )
    errors = []
    literal = allowlisted = no_flag = 0
    seen = set()

    for metadata in metadata_files:
        cdir = metadata.parent
        name = cdir.name
        rel = cdir.relative_to(ROOT)
        seen.add(name)

        try:
            flag = read_flag(metadata)
        except ValueError as e:
            errors.append(f"{rel}: cannot read flag from {metadata.name}: {e}")
            continue

        if flag is None:
            if name in NO_FLAG:
                no_flag += 1
            else:
                errors.append(f"{rel}: {metadata.name} has no flag: key (add one, or list it in NO_FLAG with a reason)")
            continue
        if name in NO_FLAG:
            errors.append(f"{rel}: listed in NO_FLAG but {metadata.name} has a flag: key; remove the stale entry")
            continue
        if not flag:
            errors.append(f"{rel}: empty flag value")
            continue

        search_dir = cdir / "challenge"
        if not search_dir.is_dir():
            errors.append(f"{rel}: no challenge/ directory (every challenge needs one, see CLAUDE.md)")
            continue

        present = found_under(search_dir, flag)
        if name in ALLOWLIST:
            if present:
                errors.append(f"{rel}: listed in ALLOWLIST but its flag is stored literally under challenge/; remove the stale entry")
            else:
                allowlisted += 1
        elif present:
            literal += 1
        else:
            errors.append(
                f"{rel}: the flag in {metadata.name} was not found literally under challenge/ "
                "(fix the mismatch, or add the challenge to ALLOWLIST in tools/check-flags.py with a reason)"
            )

    for table, label in ((ALLOWLIST, "ALLOWLIST"), (NO_FLAG, "NO_FLAG")):
        for name in sorted(table):
            if name not in seen:
                errors.append(f"{label} names '{name}', which is not a challenge folder; remove the stale entry")

    if errors:
        print("check-flags: FAILED", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    print(
        f"check-flags: ok ({literal} literal, {allowlisted} allowlisted, {no_flag} without a flag key, "
        f"{len(metadata_files)} challenges)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
