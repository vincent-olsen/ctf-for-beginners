# Shared challenge and backup lookup, and the option checks ctf.sh and azure.sh share;
# sourced by local.sh, ctf.sh and azure.sh. Needs $REPO (and warn, for newest_backup,
# and die, for check_event_time).
#
# A challenge is a folder with a metadata.yml (or metadata.yaml) at exactly
# challenges/<group>/<name>/. The folder name is its identity (compose service,
# docker image, CTFd registry image, AI staging dir), so it must be unique
# across groups. Plain bash 3.2 (macOS) compatible: no mapfile, no ${x,,}.

_has_metadata() { [[ -f "$1/metadata.yml" || -f "$1/metadata.yaml" ]]; }

# Print every challenge directory, one per line (no trailing slash).
challenge_dirs() {
  local d
  for d in "$REPO"/challenges/*/*/; do
    d="${d%/}"
    _has_metadata "$d" && printf '%s\n' "$d"
  done
  return 0
}

# Print the challenge directories named $1 (0, 1 or more lines).
challenge_dirs_named() {
  local d
  while IFS= read -r d; do
    [[ "$(basename "$d")" == "$1" ]] && printf '%s\n' "$d"
  done < <(challenge_dirs)
  return 0
}

# Print each challenge name that exists in more than one group.
duplicate_challenge_names() {
  challenge_dirs | while IFS= read -r d; do basename "$d"; done | sort | uniq -d
}

# Print metadata files that are not at challenges/<group>/<name>/ and are
# therefore ignored by every tool (e.g. a challenge added at the repo root).
stray_challenge_metadata() {
  find "$REPO" \( -path "$REPO/.git" -o -path "$REPO/.ctf" -o -path "$REPO/ctfd-backup" \) -prune -o \
    \( -name metadata.yml -o -name metadata.yaml \) -print 2>/dev/null |
    while IFS= read -r f; do
      [[ "$(dirname "$(dirname "$(dirname "$f")")")" == "$REPO/challenges" ]] || printf '%s\n' "$f"
    done
}

# resolve_challenge ARG: set CHALLENGE_DIR (absolute) and CHALLENGE_NAME, or
# print why not and return 1. ARG is either
#   - a bare name (meow1), which must match exactly one challenges/*/<name>, or
#   - a path (anything with a /), used as given. One level too deep
#     (…/meow1/challenge) is tolerated. The path may be outside this repo.
resolve_challenge() {
  # Initialised: under `set -u`, bash 4+ treats a bare `local dir` as unset.
  local arg="$1" dir="" name="" matches="" n=0
  CHALLENGE_DIR="" CHALLENGE_NAME=""
  [[ -n "$arg" ]] || { echo "No challenge given" >&2; return 1; }

  if [[ "$arg" == */* || "$arg" == . || "$arg" == .. ]]; then
    [[ -d "$arg" ]] || { echo "Not a directory: $arg" >&2; return 1; }
    dir="$(cd "$arg" && pwd)"
    case "$(basename "$dir")" in
      challenge|distfiles|solution) _has_metadata "$(dirname "$dir")" && dir="$(dirname "$dir")" ;;
    esac
    _has_metadata "$dir" || { echo "Not a challenge folder (no metadata.yml): $arg" >&2; return 1; }
    name="$(basename "$dir")"
  else
    name="$arg"
  fi

  # The name becomes a docker image/container name and a registry path.
  [[ "$name" =~ ^[a-z0-9][a-z0-9_.-]*$ ]] || {
    echo "Invalid challenge name: '$name' (lowercase letters, digits, '-', '_', '.')" >&2
    return 1
  }

  matches="$(challenge_dirs_named "$name")"
  n=0; [[ -n "$matches" ]] && n="$(printf '%s\n' "$matches" | wc -l | tr -d ' ')"
  if (( n > 1 )); then
    echo "Ambiguous challenge name '$name'; names must be unique across groups:" >&2
    printf '%s\n' "$matches" | sed "s|^$REPO/|  |" >&2
    return 1
  fi
  if [[ -z "$dir" ]]; then
    (( n == 1 )) || { echo "Challenge not found: $name (looked in challenges/*/)" >&2; return 1; }
    dir="$matches"
  fi

  CHALLENGE_DIR="$dir" CHALLENGE_NAME="$name"
}

# preview_list NAMES: the challenges of a --preview (ctf.sh, azure.sh), folder
# names separated by commas and/or spaces, each resolved with resolve_challenge.
# Printed comma-separated without duplicates; returns 1 on the first bad name.
preview_list() {
  local n out="" names=()
  IFS=', ' read -r -a names <<< "$1"
  for n in ${names[@]+"${names[@]}"}; do
    [[ -n "$n" ]] || continue
    resolve_challenge "$n" || return 1
    case ",$out," in *",$CHALLENGE_NAME,"*) ;; *) out="${out:+$out,}$CHALLENGE_NAME" ;; esac
  done
  printf '%s' "$out"
}

# is_guid S: is S a GUID (an Entra ID tenant or client id)?
is_guid() { [[ "$1" =~ ^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$ ]]; }

# check_event_time OPTION VALUE: VALUE (for --event-start, --event-end, --event-freeze)
# is a time with its UTC offset, so it means the same on a laptop and on the VM;
# ctfd_admin.py turns it into CTFd's timestamp. "" (clear it) passes too.
check_event_time() {
  local re='^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(:[0-9]{2})?([+-][0-9]{2}:[0-9]{2}|Z)$'
  [[ -z "$2" || "$2" =~ $re ]] ||
    die "$1 takes a time with its UTC offset, e.g. 2026-11-18T16:00+01:00 (Oslo in winter; +02:00 in summer), or \"\" to clear it"
}

# newest_backup: the backup `ctf.sh up` imports, printed as a path. Backups are named
# "<CTF name>.<YYYY-MM-DD_HH_MM_SS>.zip"; the latest by that timestamp wins. Exports
# from "ctf.sh backup" (local.*) stay unused until renamed, and a name without a
# parseable timestamp is skipped with a warning (the caller's warn), not ranked above
# every dated one. ctf.sh imports it; azure.sh copies only it to the VM.
newest_backup() {
  local f base ts
  for f in "$REPO"/ctfd-backup/*.zip; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f")"
    [[ "$base" != local.* ]] || continue
    ts="$(printf '%s' "$base" | sed -nE 's/.*\.([0-9]{4}-[0-9]{2}-[0-9]{2}[_T][0-9][0-9:_-]*)\.zip$/\1/p')"
    if [[ -z "$ts" ]]; then
      warn "ignoring backup without a timestamp in its name: $base"
      continue
    fi
    printf '%s|%s\n' "$ts" "$f"
  done | sort | tail -n1 | cut -d'|' -f2-
}

# compose_ports DIR: print the "host:container" port mapping compose.yml gives
# the service built from DIR/challenge, or nothing if it has none.
compose_ports() {
  local ctx="./${1#"$REPO"/}/challenge"
  [[ -f "$REPO/compose.yml" ]] || return 0
  awk -v ctx="$ctx" '
    /^  [A-Za-z0-9_.-]+:[[:space:]]*$/ { inside = 0 }
    $1 == "build:" && $2 == ctx        { inside = 1; next }
    inside && $1 == "ports:" {
      if (match($0, /:[0-9]+:[0-9]+"/)) print substr($0, RSTART + 1, RLENGTH - 2)
      exit
    }' "$REPO/compose.yml"
}
