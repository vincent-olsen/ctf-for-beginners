#!/usr/bin/env bash
# Run the whole CTF - CTFd plus every challenge container. A new CTF is set up from the
# repo; a CTFd export in ctfd-backup/, if there is one, is imported instead.
# See docs/local-setup.md and docs/hosting.md.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM="$REPO/platform"
CHALLENGES="$REPO/challenges"
STATE="${CTF_STATE_DIR:-$REPO/.ctf}"
CTFD_DIR="$STATE/CTFd"
CTFD_VERSION="${CTFD_VERSION:-3.8.6}"
PROJECT="${CTF_PROJECT:-ctf}"
CHALLENGES_COMPOSE="${CTF_CHALLENGES_COMPOSE:-$REPO/compose.yml}"
CONNECTIONS="$PLATFORM/connections.txt"
SETTINGS="$STATE/settings.env"
ADMIN_PASSWORD_FILE="$STATE/admin-password"
# Written by import_backup just before CTFd's import starts, and by new_ctf for a CTF
# set up from the repo (so never by a run that dies before touching CTFd's data),
# removed only once that import or setup has been fully configured. Its presence means "imported but not configured": a later `up` then
# re-applies the import-time config (clear dates, registration code, --fresh) even
# though CTFd already has challenges, so a crash between import and configure can't
# leave the previous event's players on a public board.
IMPORT_MARKER="$STATE/import-pending"
# Written whenever an `up` has finished configuring CTFd. azure.sh checks this, and
# the import marker, to tell a brand-new CTF from a configured one, so a first run
# that dies after its import is retried as new (with --fresh and a registration
# code) from any checkout.
CONFIGURED_MARKER="$STATE/configured"
SECRET_KEY_FILE="$STATE/secret-key"
SSO_SECRET_FILE="$STATE/sso-client-secret"
SSO_SECRET_ID_FILE="$STATE/sso-client-secret.id" # the client id that secret belongs to
SSO_COOKIE_FILE="$STATE/sso-cookie-secret"
NOTER5_SECRET_FILE="$STATE/noter5-secret"
# ./ctf.sh backup --db: gzipped dumps of CTFd's database (git-ignored, outside the
# *.zip names newest_backup reads, and kept on the VM by azure.sh's rsync).
DB_BACKUP_DIR="$REPO/ctfd-backup/db"
# The status page's config (write_status_config), mounted into its container.
STATUS_DIR="$STATE/status"

# challenge_dirs, duplicate_challenge_names, stray_challenge_metadata, resolve_challenge,
# preview_list, is_guid, check_event_time, newest_backup
. "$REPO/tools/challenge.sh"

usage() {
  cat <<EOF
usage: ./ctf.sh <command> [options]

commands:
  up            build and start CTFd and all challenges, and write connection info into
                CTFd. The first run sets CTFd up from the repo, or imports the newest
                CTFd export in ctfd-backup/ if there is one
  down          stop everything (CTFd data is kept in .ctf/)
  status        show running containers
  logs [NAME]   follow logs of a service, e.g. ctfd, nginx, noter4 (default: all challenges)
  reset NAME... recreate challenge containers from their images, e.g. after a player broke
                one (a restart keeps the container's changes; this doesn't)
  connections   rewrite CTFd connection info only (e.g. after changing --host)
  backup        export the running CTFd to ctfd-backup/local.<timestamp>.zip (git-ignored)
  backup --db   dump CTFd's database to ctfd-backup/db/ctfd.<timestamp>.sql.gz (small and
                quick: players, teams, solves); dumps older than 7 days are deleted.
                --if-event dumps only from 30 minutes before the event's start to 30
                minutes after its end (CTFd's start and end time), for a timer
  restore-db [FILE]
                put a dump from backup --db back into CTFd (the database as it is now is
                dumped first); asks to confirm unless --yes. Without FILE it lists the
                dumps in ctfd-backup/db/, newest first, and asks which one

options for up:
  --host NAME             hostname players connect to (default: localhost)
  --domain NAME           hosted mode: CTFd over HTTPS at NAME, challenges on all interfaces
  --bind ADDR             interface to publish ports on (default: 127.0.0.1, or 0.0.0.0
                          with --domain or a non-localhost --host)
  --port N                CTFd HTTP port in local mode (default: 80)
  --backup FILE           CTFd export to import (default: the newest in ctfd-backup/,
                          if any; without one, a new CTFd is set up from the repo)
  --reimport              wipe CTFd and set it up again: import the export again, or,
                          without one, start a new CTF from the repo
  --fresh                 on a run that imports an export: remove its players, teams
                          and submissions (for a new event); ignored otherwise
  --registration-code C   require code C to register ("" = open registration)
  --preview NAMES         preview: only these challenges (folder names, e.g. julius,meow1),
                          playable without an account, flags checked but not saved;
                          "" ends it and brings everything back
  --sso-tenant ID         Entra ID tenant for --sso-client-id
  --sso-client-id ID      hosted mode: sign in with Microsoft (Entra ID) before reaching
                          CTFd; needs the app registration's secret in SSO_CLIENT_SECRET
                          the first time with each client id ("" turns sign-in off)
  --brand DIR             the event's name, logo and favicon in CTFd: a folder with a
                          brand.conf (default: platform/theme/brand); "" leaves CTFd's own
  --lang CODE             the language players see until they switch with NO | EN in the
                          navbar: en (English, the default) or no (Norwegian); see docs/language.md
  --event-start TIME      CTFd's start time, with its UTC offset: 2026-11-18T16:00+01:00
  --event-end TIME        CTFd's end time, the same way
  --event-freeze TIME     when the scoreboard freezes, the same way
  --team-size N           most players in a team
                          (saved, and set in CTFd on this run and after every import or
                          new setup; "" clears one. An up without them leaves CTFd's
                          own, so a change in the admin panel during the event stays)
  --status on|off         the status page: https://status.<domain> when hosting, and
                          http://localhost:8081 on this machine (default: on)

options for connections:
  --host NAME

Settings from the last 'up' are saved in .ctf/settings.env and reused.
Environment: ADMIN_PASSWORD (default: generated, stored in .ctf/admin-password)
             SSO_CLIENT_SECRET (stored in .ctf/sso-client-secret, with its client id)
             CTF_AI_MODE=off leaves out the AI-modus challenges and theme (saved by up;
             CTF_AI_MODE=on brings them back)
EOF
}

log()  { printf '\033[1;34m==>\033[0m \033[1m%s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

trim() {
  local s=$1
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

random_hex() { head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'; }

# --- compose wrappers --------------------------------------------------------

ctfd_compose() {
  local files=(-f "$CTFD_DIR/docker-compose.yml" -f "$PLATFORM/ctfd.yml")
  if [[ -n "$CTF_DOMAIN" ]]; then files+=(-f "$PLATFORM/ctfd.hosted.yml"); fi
  if sso_on; then files+=(-f "$PLATFORM/ctfd.sso.yml"); fi
  if status_on; then files+=(-f "$PLATFORM/ctfd.status.yml"); fi
  docker compose -p "$PROJECT-platform" "${files[@]}" "$@"
}

# Microsoft sign-in in front of CTFd: hosted mode only, since it sits in Caddy.
sso_on() { [[ -n "$CTF_DOMAIN" && -n "$CTF_SSO_CLIENT_ID" ]]; }

# The status page (platform/ctfd.status.yml), unless --status off.
status_on() { [[ "${CTF_STATUS:-on}" != off ]]; }

# Where to find the status page, for the summaries.
status_url() {
  if [[ -n "$CTF_DOMAIN" ]]; then echo "https://status.$CTF_DOMAIN"; else echo "http://localhost:8081"; fi
}

# in_preview PREVIEW SVC: is compose service SVC one of the challenges in the
# (comma-separated) PREVIEW?
in_preview() { case ",$1," in *",$2,"*) return 0 ;; esac; return 1; }

challenges_compose() {
  docker compose -p "$PROJECT-challenges" -f "$CHALLENGES_COMPOSE" "$@"
}

# The proxy in front of CTFd: nginx locally, Caddy when hosting. It starts last, so
# CTFd is unreachable until it is imported or set up and configured (a fresh CTFd
# serves its setup page to whoever gets there first).
proxy_service() {
  if [[ -n "$CTF_DOMAIN" ]]; then echo caddy; else echo nginx; fi
}

# CTFd prints migration and plugin-loading lines on every app start.
quiet_ctfd() { grep -vE '^INFO  \[alembic|^ \* Loaded module' || true; }

# Run platform/ctfd_admin.py inside the ctfd container. Extra env: ENV_ARGS array.
ctfd_admin() {
  ctfd_compose exec -T "${ENV_ARGS[@]}" ctfd python - "$@" < "$PLATFORM/ctfd_admin.py" 2>&1 | quiet_ctfd
}

# --- settings ----------------------------------------------------------------

load_settings() {
  # CTF_AI_MODE in the environment wins over the saved one, and up saves it.
  local env_ai_mode="${CTF_AI_MODE:-}"
  CTF_HOST="" CTF_DOMAIN="" CTF_BIND="" CTFD_HTTP_PORT=""
  CTF_PREVIEW="" CTF_SSO_TENANT="" CTF_SSO_CLIENT_ID="" CTF_BRAND="platform/theme/brand" CTF_LANG="en"
  CTF_EVENT_START="" CTF_EVENT_END="" CTF_EVENT_FREEZE="" CTF_TEAM_SIZE="" CTF_STATUS="on" CTF_AI_MODE="on"
  if [[ -f "$SETTINGS" ]]; then
    # shellcheck source=/dev/null
    . "$SETTINGS"
  fi
  if [[ -n "$env_ai_mode" ]]; then CTF_AI_MODE="$env_ai_mode"; fi
  SAVED_SSO_CLIENT_ID="$CTF_SSO_CLIENT_ID"
}

save_settings() {
  mkdir -p "$STATE"
  printf '%s=%q\n' CTF_HOST "$CTF_HOST" CTF_DOMAIN "$CTF_DOMAIN" \
    CTF_BIND "$CTF_BIND" CTFD_HTTP_PORT "$CTFD_HTTP_PORT" CTF_PREVIEW "$CTF_PREVIEW" \
    CTF_SSO_TENANT "$CTF_SSO_TENANT" CTF_SSO_CLIENT_ID "$CTF_SSO_CLIENT_ID" \
    CTF_BRAND "$CTF_BRAND" CTF_LANG "$CTF_LANG" \
    CTF_EVENT_START "$CTF_EVENT_START" CTF_EVENT_END "$CTF_EVENT_END" \
    CTF_EVENT_FREEZE "$CTF_EVENT_FREEZE" CTF_TEAM_SIZE "$CTF_TEAM_SIZE" \
    CTF_STATUS "$CTF_STATUS" CTF_AI_MODE "$CTF_AI_MODE" > "$SETTINGS"

  # Compose reads the .env next to compose.yml, so a plain "docker compose" in the
  # repo folder publishes on the same interface as ctf.sh.
  local dotenv
  dotenv="$(dirname "$CHALLENGES_COMPOSE")/.env"
  if [[ ! -e "$dotenv" ]] || head -n1 "$dotenv" | grep -q '^# Written by ctf.sh'; then
    printf '# Written by ctf.sh; change it with ./ctf.sh up --bind/--host/--domain\nCTF_BIND=%s\n' \
      "$CTF_BIND" > "$dotenv"
  else
    warn "left $dotenv alone (not written by ctf.sh); plain 'docker compose' will publish on 127.0.0.1"
  fi
}

export_compose_env() {
  export CTF_BIND CTFD_HTTP_PORT CTF_DOMAIN
  export CTFD_SECRET_KEY CTF_PLATFORM_DIR="$PLATFORM"
  export CTF_SSO_TENANT CTF_SSO_CLIENT_ID CTF_SSO_CLIENT_SECRET CTF_SSO_COOKIE_SECRET
  export NOTER5_SECRET
  # The status page: its config folder, and its site in the Caddyfile. Off (or not
  # hosting), the site is a name nobody resolves, so Caddy asks for no certificate.
  export CTF_STATUS_DIR="$STATUS_DIR" CTF_STATUS_SITE="http://status.invalid"
  if status_on; then
    # Made here, not by Docker for the bind mount (root-owned, so ctf.sh couldn't write it).
    mkdir -p "$STATUS_DIR"
    if [[ -n "$CTF_DOMAIN" ]]; then CTF_STATUS_SITE="status.$CTF_DOMAIN"; fi
  fi
}

ctfd_url() {
  if [[ -n "$CTF_DOMAIN" ]]; then
    echo "https://$CTF_DOMAIN"
  elif [[ "$CTFD_HTTP_PORT" == 80 ]]; then
    echo "http://$CTF_HOST"
  else
    echo "http://$CTF_HOST:$CTFD_HTTP_PORT"
  fi
}

# --- steps -------------------------------------------------------------------

preflight() {
  command -v git >/dev/null || die "git is not installed"
  command -v docker >/dev/null || die "docker is not installed"
  docker compose version >/dev/null 2>&1 || die "the docker compose plugin is not installed"
  docker info >/dev/null 2>&1 || die "Docker is not responding. On Docker Desktop, run: docker desktop restart"
}

ensure_ctfd_source() {
  if [[ ! -f "$CTFD_DIR/docker-compose.yml" ]]; then
    log "Downloading CTFd $CTFD_VERSION"
    mkdir -p "$STATE"
    git -c advice.detachedHead=false clone --quiet --branch "$CTFD_VERSION" --depth 1 https://github.com/CTFd/CTFd.git "$CTFD_DIR"
  fi
}

# Install platform/plugins/<name> into the CTFd source, or remove it when $2 is "off"
# or empty. Sets PLUGINS_CHANGED=1 when it changed anything. The source is CTFd's
# build context, so a changed plugin changes the image and the `up -d --build` that
# follows recreates CTFd with it: no separate restart needed.
sync_plugin() {
  local src="$PLATFORM/plugins/$1" dst="$CTFD_DIR/CTFd/plugins/$1"
  if [[ -z "$2" || "$2" == off ]]; then
    [[ ! -e "$dst" ]] || { rm -rf "$dst"; PLUGINS_CHANGED=1; }
  elif ! { [[ -d "$dst" ]] && diff -rq -x __pycache__ "$src" "$dst" >/dev/null 2>&1; }; then
    rm -rf "$dst"
    cp -R "$src" "$dst"
    PLUGINS_CHANGED=1
  fi
}

# sync_plugins PREVIEW: the plugins CTFd needs with PREVIEW and CTF_AI_MODE.
# ai_brackets (per-bracket scoreboards) unless CTF_AI_MODE=off; ctf_theme (serves
# platform/theme) whenever the theme is linked, so unless CTF_AI_MODE=off and
# always in a preview; ctf_preview (anonymous flag checks) while a preview is set;
# ctf_firstblood (who solved each challenge first, which the theme announces)
# with the theme outside a preview, where no solve is saved; ctf_hints (no buying
# a hint before the cheaper ones) and ctf_solve_limit (a challenge with max_solves
# locks once that many teams solved it) always.
sync_plugins() {
  local theme="" first_blood=""
  if [[ "${CTF_AI_MODE:-on}" != off || -n "$1" ]]; then theme=on; fi
  if [[ "${CTF_AI_MODE:-on}" != off && -z "$1" ]]; then first_blood=on; fi
  sync_plugin ctf_hints on
  sync_plugin ctf_solve_limit on
  sync_plugin ai_brackets "${CTF_AI_MODE:-on}"
  sync_plugin ctf_theme "$theme"
  sync_plugin ctf_firstblood "$first_blood"
  sync_plugin ctf_preview "${1:+on}"
}

# ensure_secrets [up]: "up" for the one command that applies the admin password.
ensure_secrets() {
  mkdir -p "$STATE"
  ADMIN_PASSWORD_SET=0
  if [[ ! -s "$SECRET_KEY_FILE" ]]; then
    (umask 077; random_hex 32 > "$SECRET_KEY_FILE")
  fi
  CTFD_SECRET_KEY="$(cat "$SECRET_KEY_FILE")"
  # noter5's proxy derives its AES key and admin password from this (compose.yml),
  # so every rebuild and recreate of it matches the notes its backend holds.
  if [[ ! -s "$NOTER5_SECRET_FILE" ]]; then
    (umask 077; random_hex 32 > "$NOTER5_SECRET_FILE")
  fi
  NOTER5_SECRET="$(cat "$NOTER5_SECRET_FILE")"

  # ADMIN_PASSWORD_SET: should this run (re)assert the admin password in CTFd?
  # Only when the user passed ADMIN_PASSWORD, or we generated it on a first run.
  # A routine `up` with an existing stored password leaves it alone, so an admin
  # who rotated the password in the CTFd UI is not silently reverted; an import
  # turns this on explicitly (cmd_up), since a fresh CTFd needs the password set.
  # Only `up` stores or generates it: every other command leaves the file as it is,
  # so .ctf/admin-password never names a password CTFd was not given.
  if [[ "${1:-}" == up ]]; then
    if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
      (umask 077; printf '%s' "$ADMIN_PASSWORD" > "$ADMIN_PASSWORD_FILE")
      ADMIN_PASSWORD_SET=1
    elif [[ ! -s "$ADMIN_PASSWORD_FILE" ]]; then
      (umask 077; random_hex 12 > "$ADMIN_PASSWORD_FILE")
      ADMIN_PASSWORD_SET=1
    fi
    ADMIN_PASSWORD="$(cat "$ADMIN_PASSWORD_FILE")"
  elif [[ -n "${ADMIN_PASSWORD:-}" ]]; then
    warn "ADMIN_PASSWORD is applied by ./ctf.sh up only; ignored here"
  fi

  # Microsoft sign-in: the app registration's secret (given once for each client id),
  # and oauth2-proxy's cookie key (32 characters, generated). The secret is kept with
  # the client id it belongs to, so it is used for that app registration only.
  if [[ -n "${SSO_CLIENT_SECRET:-}" ]]; then
    (umask 077; printf '%s' "$SSO_CLIENT_SECRET" > "$SSO_SECRET_FILE"
      printf '%s\n' "$CTF_SSO_CLIENT_ID" > "$SSO_SECRET_ID_FILE")
  elif [[ -s "$SSO_SECRET_FILE" && ! -e "$SSO_SECRET_ID_FILE" && -n "$SAVED_SSO_CLIENT_ID" ]]; then
    # Kept without its client id by an earlier version: the last up's.
    printf '%s\n' "$SAVED_SSO_CLIENT_ID" > "$SSO_SECRET_ID_FILE"
  fi
  CTF_SSO_CLIENT_SECRET="" CTF_SSO_COOKIE_SECRET=""
  if [[ -n "$CTF_SSO_CLIENT_ID" ]]; then
    if [[ ! -s "$SSO_COOKIE_FILE" ]]; then
      (umask 077; random_hex 16 > "$SSO_COOKIE_FILE")
    fi
    CTF_SSO_COOKIE_SECRET="$(cat "$SSO_COOKIE_FILE")"
    if [[ -s "$SSO_SECRET_FILE" && "$(cat "$SSO_SECRET_ID_FILE" 2>/dev/null || true)" == "$CTF_SSO_CLIENT_ID" ]]; then
      CTF_SSO_CLIENT_SECRET="$(cat "$SSO_SECRET_FILE")"
    fi
  fi
}

wait_for_ctfd() {
  local i
  for i in $(seq 1 90); do
    if ctfd_compose exec -T ctfd python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthcheck', timeout=3)" \
      >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  ctfd_compose logs --tail 40 ctfd >&2 || true
  die "CTFd did not become healthy within 3 minutes (logs above)"
}

challenge_count() {
  local ENV_ARGS=(-e PYTHONUNBUFFERED=1) out
  out="$(ctfd_admin count || true)"
  # Anything besides the count line (e.g. the last import's error) goes to the terminal.
  printf '%s\n' "$out" | grep -vE '^challenges=|^$' >&2 || true
  printf '%s\n' "$out" | sed -n 's/^challenges=//p' | tail -n1
}

# import_backup BACKUP FRESH REGCODE: FRESH and REGCODE are this run's import-time
# intent, kept in the import marker for a later `up` to finish the configure with.
import_backup() {
  local backup=$1 count
  [[ -f "$backup" ]] || die "backup not found: $backup"
  log "Importing $(basename "$backup")"
  ctfd_compose cp "$backup" ctfd:/tmp/backup.zip
  # Only now, with nothing left to fail before CTFd's data is replaced, record the
  # intent: a run that died earlier left the running CTF untouched.
  (umask 077; printf '%s\n%s\n' "$2" "$3" > "$IMPORT_MARKER")
  ctfd_compose exec -T ctfd python manage.py import_ctf /tmp/backup.zip \
    | grep -vE '^inserting |^INFO  \[alembic|^ \* Loaded module' || true
  # docker cp leaves the file owned by root, so CTFd's own user can't delete it.
  ctfd_compose exec -T -u root ctfd rm -f /tmp/backup.zip
  ctfd_compose restart ctfd >/dev/null
  wait_for_ctfd
  count="$(challenge_count)"
  [[ "$count" =~ ^[0-9]+$ && "$count" -gt 0 ]] || die "import failed (see output above)"
  echo "imported $count challenges"
}

# new_ctf WIPE REGCODE: a new CTF from the repo alone, for an up with no export to
# import. ctfd_admin.py configure does CTFd's setup and creates every challenge from
# its metadata.yml; the import marker records the intent first, as for an import, so
# a run that dies before that is finished is completed by the next up. WIPE
# (--reimport) empties CTFd's database first, as an import would.
new_ctf() {
  log "No CTFd export in ctfd-backup/: setting up a new CTF from the repo"
  (umask 077; printf '%s\n%s\n' 0 "$2" > "$IMPORT_MARKER")
  if [[ $1 == 1 ]]; then
    log "Emptying CTFd's database (--reimport)"
    ctfd_compose stop ctfd >/dev/null
    ctfd_compose exec -T db sh -c \
      'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb -u"$MARIADB_USER" -e "DROP DATABASE \`$MARIADB_DATABASE\`; CREATE DATABASE \`$MARIADB_DATABASE\` CHARACTER SET utf8mb4"' ||
      die "could not empty CTFd's database"
    # CTFd keeps config, challenges and standings in Redis; drop them with the old data.
    ctfd_compose exec -T cache redis-cli FLUSHALL >/dev/null
    # CTFd creates its tables again as it starts.
    ctfd_compose start ctfd >/dev/null
    wait_for_ctfd
  fi
}

# published_port PS SVC CPORT: the host port compose publishes for SVC's container port
# CPORT, from PS ("<service> 127.0.0.1:4441->4445/tcp, ..." lines from compose ps), or
# nothing when it publishes none.
published_port() {
  local line re="[ :]([0-9]+)->$3/tcp"
  while IFS= read -r line; do
    if [[ "$line" == "$2 "* && "$line" =~ $re ]]; then
      printf '%s' "${BASH_REMATCH[1]}"
      return 0
    fi
  done <<< "$1"
  return 0
}

# Resolve platform/connections.txt into "<name>\t<value>" lines.
render_connections() {
  local name svc cport tmpl port ps out=""
  # One call for all published ports, as "<service> 127.0.0.1:4441->4445/tcp, ..." lines.
  ps="$(challenges_compose ps --format '{{.Service}} {{.Ports}}' </dev/null 2>/dev/null)" || true
  while IFS='|' read -r name svc cport tmpl || [[ -n "$name" ]]; do
    name="$(trim "$name")"
    [[ -z "$name" || "$name" == \#* ]] && continue
    svc="$(trim "$svc")"; cport="$(trim "$cport")"; tmpl="$(trim "$tmpl")"
    if [[ "$tmpl" == hidden ]]; then
      out+="$name"$'\t'"@hidden"$'\n'
      continue
    fi
    if [[ "$tmpl" == *"{port}"* ]]; then
      port="$(published_port "$ps" "$svc" "$cport")"
      if [[ -z "$port" ]]; then
        # A preview runs only its own challenges; the hidden ones' info stays as it is.
        if [[ -z "$CTF_PREVIEW" ]] || in_preview "$CTF_PREVIEW" "$svc"; then
          warn "no published port for $svc:$cport (is the challenge running?); left $name's connection info unchanged"
        fi
        continue
      fi
      tmpl="${tmpl//\{port\}/$port}"
    fi
    out+="$name"$'\t'"${tmpl//\{host\}/$CTF_HOST}"$'\n'
  done < "$CONNECTIONS"
  printf '%s' "$out"
}

# yaml_str TEXT: TEXT as a double-quoted YAML string.
yaml_str() {
  local s=${1//\\/\\\\}
  s=${s//\"/\\\"}
  printf '"%s"' "$s"
}

# status_endpoint NAME GROUP URL CONDITION: one check in the status page's config.
status_endpoint() {
  printf '  - name: %s\n    group: %s\n    url: %s\n    interval: 60s\n    conditions:\n      - %s\n' \
    "$(yaml_str "$1")" "$(yaml_str "$2")" "$(yaml_str "$3")" "$(yaml_str "$4")"
}

# Write the status page's config (platform/ctfd.status.yml) to .ctf/status/config.yaml:
# CTFd's health check, and a check for each challenge in platform/connections.txt
# whose container runs now (none for hidden ones, nor in a preview for the others).
# A web challenge is up while it answers HTTP without a server error, a terminal or
# pwn one while its port takes connections. Gatus reloads the file when it changes.
write_status_config() {
  local name svc cport tmpl port ps title out
  title="${BRAND_NAME:-CTF}"
  ps="$(challenges_compose ps --format '{{.Service}} {{.Ports}}' </dev/null 2>/dev/null)" || true
  out="# Written by ./ctf.sh up from compose.yml and platform/connections.txt; edits are overwritten.
web:
  port: 8080
ui:
  title: $(yaml_str "$title status")
  header: $(yaml_str "$title")
  description: $(yaml_str "Down, or is it me? CTFd and every challenge are checked once a minute.")
endpoints:
$(status_endpoint "CTFd" "Platform" "http://ctfd:8000/healthcheck" "[STATUS] == 200")"
  while IFS='|' read -r name svc cport tmpl || [[ -n "$name" ]]; do
    name="$(trim "$name")"
    [[ -z "$name" || "$name" == \#* ]] && continue
    svc="$(trim "$svc")"; cport="$(trim "$cport")"; tmpl="$(trim "$tmpl")"
    [[ "$tmpl" == *"{port}"* ]] || continue
    port="$(published_port "$ps" "$svc" "$cport")"
    [[ -n "$port" ]] || continue
    case "$tmpl" in
      http://* | https://*)
        out+=$'\n'"$(status_endpoint "$name" "Web" "http://host.docker.internal:$port/" "[STATUS] < 500")" ;;
      *)
        out+=$'\n'"$(status_endpoint "$name" "Terminal and pwn (nc)" "tcp://host.docker.internal:$port" "[CONNECTED] == true")" ;;
    esac
  done < "$CONNECTIONS"
  mkdir -p "$STATUS_DIR"
  printf '%s\n' "$out" > "$STATUS_DIR/config.yaml.new"
  mv "$STATUS_DIR/config.yaml.new" "$STATUS_DIR/config.yaml"
}

# Stage every challenge's metadata.yml and distfiles/, plus the files a hint hands
# over ({{file:challenge/app.py}}; see HINT_FILE in ctfd_admin.py), into
# .ctf/challenge-stage so it can be copied into the ctfd container: normal
# challenges take their description and flag case from it, and a newer copy of a
# file the backup attaches; AI-modus ones are created/updated from it, attachments
# included. Every challenges/<group>/<name>/ is staged: ctfd_admin.py tells the two
# kinds apart by the metadata `category` (AI-modus iff it starts with "ai-"). Fails on a
# name used in two groups (the stage dir is keyed by name) or a hint file that
# isn't in its challenge's folder, and warns about metadata files outside that
# layout, which are ignored. Prints the staging directory, or nothing when there
# are no challenges.
stage_challenges() {
  local stage="$STATE/challenge-stage" d meta name dups stray f found=0
  dups="$(duplicate_challenge_names)"
  [[ -z "$dups" ]] || die "challenge names must be unique across challenges/*/; duplicated: $(echo $dups)"
  stray="$(stray_challenge_metadata)"
  [[ -z "$stray" ]] || warn "ignored (not at challenges/<group>/<name>/): $(printf '%s\n' "$stray" | sed "s|^$REPO/||" | paste -sd ' ' -)"
  rm -rf "$stage"; mkdir -p "$stage"
  while IFS= read -r d; do
    meta="$d/metadata.yml"; [[ -f "$meta" ]] || meta="$d/metadata.yaml"
    name="$(basename "$d")"
    mkdir -p "$stage/$name"
    cp "$meta" "$stage/$name/metadata.yml"
    if [[ -d "$d/distfiles" ]]; then
      cp -R "$d/distfiles" "$stage/$name/distfiles"
    fi
    while IFS= read -r f; do
      [[ "/$f/" != */../* && -f "$d/$f" ]] || die "${d#"$REPO"/}/metadata.yml: hint file $f is not a file in the challenge's folder"
      mkdir -p "$stage/$name/$(dirname "$f")"
      cp "$d/$f" "$stage/$name/$f"
    done < <(grep -v '^[[:space:]]*#' "$meta" | grep -oE '\{\{[[:space:]]*file:[[:space:]]*[^}[:space:]]+' | sed -E 's/^\{\{[[:space:]]*file:[[:space:]]*//' | sort -u)
    found=1
  done < <(challenge_dirs)
  if [[ $found == 1 ]]; then printf '%s' "$stage"; else rm -rf "$stage"; fi
}

# The event's brand for ctfd_admin.py, from the folder CTF_BRAND (relative to the
# repo unless absolute; "" for none): its brand.conf has name=, logo= and icon=,
# the files relative to the folder. Sets BRAND_NAME, BRAND_DIR (the folder), and
# BRAND_LOGO and BRAND_ICON as paths relative to it; each empty when not set.
read_brand() {
  BRAND_NAME="" BRAND_LOGO="" BRAND_ICON="" BRAND_DIR=""
  [[ -n "$CTF_BRAND" ]] || return 0
  local dir="$CTF_BRAND"
  [[ "$dir" == /* ]] || dir="$REPO/$dir"
  [[ -f "$dir/brand.conf" ]] || die "no brand.conf in $dir (see --brand in ./ctf.sh --help)"
  BRAND_NAME="$(brand_value name "$dir/brand.conf")"
  # Just the paths in the folder; apply_config copies the folder into the container
  # and ctfd_admin reads them from there. (Passing a logo as a base64 env var broke
  # configure once the string topped Linux's ~128 KB per-env limit.)
  BRAND_LOGO="$(brand_path "$dir" "$(brand_value logo "$dir/brand.conf")")"
  BRAND_ICON="$(brand_path "$dir" "$(brand_value icon "$dir/brand.conf")")"
  BRAND_DIR="$dir"
}

brand_value() { sed -n "s/^$1=//p" "$2" | tail -n1; }

# brand_path DIR FILE: FILE (relative to DIR, as brand.conf names it), checked.
brand_path() {
  [[ -n "$2" ]] || return 0
  [[ "$2" != /* && "/$2/" != */../* ]] || die "$1/brand.conf names $2, which isn't inside the brand folder"
  [[ -f "$1/$2" ]] || die "$1/brand.conf names $2, which isn't there"
  printf '%s' "$2"
}

# Configure CTFd: the args go to "ctfd_admin.py configure". Its exit code is left in
# CONFIGURE_RC (3 when it rejected the preview's names, before changing anything)
# instead of returned, so callers don't run this with set -e off.
apply_config() {
  local conns stage stage_env=()
  conns="$(render_connections)"
  # Connections-only (./ctf.sh connections): write just the connection info and
  # nothing else — no challenge/brand/page/theme sync, no admin-password reset — so
  # refreshing connection info never reverts changes an admin made in the UI.
  if [[ "${APPLY_CONNECTIONS_ONLY:-0}" == 1 ]]; then
    local ENV_ARGS=(-e CTF_CONNECTIONS)
    CONFIGURE_RC=0
    CTF_CONNECTIONS="$conns" ctfd_admin configure --connections-only || CONFIGURE_RC=$?
    return
  fi
  # The theme (platform/theme/), linked from theme_header/footer unless
  # CTF_AI_MODE=off, with the preview's terminal look and boot screen on top while a
  # preview runs. A preview always gets it: there it is the Classic lane only (no
  # lane control, no AI-modus), and the preview's note and hidden Login link are
  # part of it. The ctf_theme plugin serves the files themselves.
  local ai_flags=()
  if [[ "${CTF_AI_MODE:-on}" == off ]]; then
    ai_flags+=(--no-ai-challenges)
    [[ -n "$CTF_PREVIEW" ]] || ai_flags+=(--no-ai-theme)
  fi
  read_brand
  # Copy the challenges' metadata into the ctfd container so ctfd_admin can sync
  # them (CTFd's DB can't see the repo). Auto-discovered, so new challenges are
  # picked up with no change here.
  stage="$(stage_challenges)" || exit 1
  if [[ -n "$stage" ]]; then
    ctfd_compose exec -T -u root ctfd rm -rf /tmp/challenges 2>/dev/null || true
    if ctfd_compose cp "$stage" ctfd:/tmp/challenges >/dev/null 2>&1; then
      stage_env=(-e CTF_CHALLENGES_DIR)
    else
      warn "could not copy the challenges' metadata into CTFd; skipping their sync"
    fi
  fi
  # The pages kept in the repo (platform/pages/<route>.md and <route>.no.md), which
  # replace the content of the backup's page with that route.
  local pages_env=()
  if compgen -G "$PLATFORM/pages/*.md" >/dev/null; then
    ctfd_compose exec -T -u root ctfd rm -rf /tmp/ctf-pages 2>/dev/null || true
    if ctfd_compose cp "$PLATFORM/pages" ctfd:/tmp/ctf-pages >/dev/null 2>&1; then
      pages_env=(-e CTF_PAGES_DIR)
    else
      warn "could not copy platform/pages into CTFd; skipping the pages' sync"
    fi
  fi
  # The brand folder (logo/icon). Copied in as files, not passed as base64 env vars,
  # so a logo of any size works (a big one topped Linux's per-env-string limit and
  # failed the whole configure).
  local brand_env=()
  if [[ -n "$BRAND_DIR" ]]; then
    ctfd_compose exec -T -u root ctfd rm -rf /tmp/ctf-brand 2>/dev/null || true
    if ctfd_compose cp "$BRAND_DIR" ctfd:/tmp/ctf-brand >/dev/null 2>&1; then
      brand_env=(-e CTF_BRAND_DIR)
    else
      warn "could not copy the brand folder into CTFd; skipping the logo and icon"
    fi
  fi
  # "-e NAME" takes the value from this environment, so secrets and large blobs
  # stay out of the process list.
  local ENV_ARGS=(-e CTF_ADMIN_PASSWORD -e CTF_CONNECTIONS -e CTF_BRAND_NAME -e CTF_BRAND_LOGO -e CTF_BRAND_ICON
    ${stage_env[@]+"${stage_env[@]}"} ${pages_env[@]+"${pages_env[@]}"} ${brand_env[@]+"${brand_env[@]}"})
  # ctfd_admin sets the admin password only when this is non-empty, so a routine up
  # that isn't meant to (re)assert it leaves a UI-rotated password alone.
  local admin_pw=""
  [[ "${ADMIN_PASSWORD_SET:-0}" == 1 ]] && admin_pw="$ADMIN_PASSWORD"
  CONFIGURE_RC=0
  CTF_ADMIN_PASSWORD="$admin_pw" CTF_CONNECTIONS="$conns" \
    CTF_BRAND_NAME="$BRAND_NAME" CTF_BRAND_LOGO="$BRAND_LOGO" CTF_BRAND_ICON="$BRAND_ICON" \
    CTF_BRAND_DIR="/tmp/ctf-brand" \
    CTF_CHALLENGES_DIR="/tmp/challenges" CTF_PAGES_DIR="/tmp/ctf-pages" \
    ctfd_admin configure ${ai_flags[@]+"${ai_flags[@]}"} --preview "$CTF_PREVIEW" --lang "$CTF_LANG" "$@" ||
    CONFIGURE_RC=$?
  # Remove the staged copies from the container and the host.
  if [[ -n "$stage" ]]; then
    ctfd_compose exec -T -u root ctfd rm -rf /tmp/challenges 2>/dev/null || true
    rm -rf "$stage"
  fi
  if [[ ${#pages_env[@]} -gt 0 ]]; then
    ctfd_compose exec -T -u root ctfd rm -rf /tmp/ctf-pages 2>/dev/null || true
  fi
  if [[ ${#brand_env[@]} -gt 0 ]]; then
    ctfd_compose exec -T -u root ctfd rm -rf /tmp/ctf-brand 2>/dev/null || true
  fi
}

# preview_services PREVIEW: the compose services among PREVIEW's challenges, one
# per line (a static challenge has none).
preview_services() {
  local svc
  while IFS= read -r svc; do
    if [[ -n "$svc" ]] && in_preview "$1" "$svc"; then printf '%s\n' "$svc"; fi
  done < <(challenges_compose config --services)
}

# Build and start the challenge containers: all of them, or in a preview only the
# preview's own (Compose starts what they depend on, noter5-backend for noter5).
# The others keep running until stop_outside_preview, once CTFd has the preview.
start_challenges() {
  if [[ -z "$CTF_PREVIEW" ]]; then
    challenges_compose up -d --build --remove-orphans
    stop_extra
    return
  fi
  local svc keep=()
  while IFS= read -r svc; do keep+=("$svc"); done < <(preview_services "$CTF_PREVIEW")
  if [[ ${#keep[@]} -gt 0 ]]; then
    challenges_compose up -d --build --remove-orphans "${keep[@]}"
  else
    echo "no hosted challenge in the preview"
  fi
  stop_extra
}

# Stop the challenges compose.yml keeps in the "extra" profile (hidden in CTFd for
# this event) if they still run from an earlier up.
stop_extra() {
  local svc active drop=()
  active=",$(challenges_compose config --services 2>/dev/null | paste -sd, - || true),"
  while IFS= read -r svc; do
    if [[ -n "$svc" && "$active" != *",$svc,"* ]]; then drop+=("$svc"); fi
  done < <(challenges_compose --profile extra ps --services --status running 2>/dev/null || true)
  if [[ ${#drop[@]} -gt 0 ]]; then
    echo "stopping ${drop[*]} (hidden for this event: profile extra in compose.yml)"
    challenges_compose --profile extra rm --stop --force "${drop[@]}" >/dev/null 2>&1 ||
      warn "could not stop ${drop[*]} (./ctf.sh status shows them)"
  fi
  return 0
}

# stop_outside_preview PREVIEW: stop every challenge container PREVIEW doesn't need,
# so no other challenge is reachable. It needs its own services and what they depend
# on, which "compose config SERVICE..." lists. If that fails, only its own are kept
# and then started again, which brings their dependencies back.
stop_outside_preview() {
  local svc out keep=() needed="," drop=() restart=0
  while IFS= read -r svc; do keep+=("$svc"); done < <(preview_services "$1")
  if [[ ${#keep[@]} -gt 0 ]]; then
    out="$(challenges_compose config "${keep[@]}" 2>/dev/null | awk '
      /^[^ ]/ { s = ($0 == "services:"); next }
      s && /^  [^ #-][^ ]*:$/ { sub(/^  /, ""); sub(/:$/, ""); print }' | paste -sd, -)" || out=""
    needed+="$out,"
    for svc in "${keep[@]}"; do
      if [[ "$needed" != *",$svc,"* ]]; then
        warn "could not list what the preview's challenges depend on; restarting them after the others stop"
        needed="$(printf ',%s' "${keep[@]}"),"
        restart=1
        break
      fi
    done
  fi
  while IFS= read -r svc; do
    if [[ -n "$svc" && "$needed" != *",$svc,"* ]]; then drop+=("$svc"); fi
  done < <(challenges_compose config --services)
  if [[ ${#drop[@]} -gt 0 ]]; then
    challenges_compose rm --stop --force "${drop[@]}" >/dev/null 2>&1 ||
      warn "could not stop every challenge outside the preview (./ctf.sh status shows them)"
  fi
  if [[ $restart == 1 ]]; then
    challenges_compose up -d --no-build "${keep[@]}"
  fi
  return 0
}

# The challenge services running now, as ",svc,svc,".
running_challenges() {
  printf ',%s,' "$(challenges_compose ps --services --status running 2>/dev/null | paste -sd, - || true)"
}

# stop_started BEFORE: stop the challenges running now that weren't in BEFORE (from
# running_challenges), which is what this run started.
stop_started() {
  local svc drop=()
  while IFS= read -r svc; do
    if [[ -n "$svc" && "$1" != *",$svc,"* ]]; then drop+=("$svc"); fi
  done < <(challenges_compose ps --services --status running 2>/dev/null || true)
  if [[ ${#drop[@]} -gt 0 ]]; then
    challenges_compose stop "${drop[@]}" >/dev/null 2>&1 ||
      warn "could not stop ${drop[*]} (./ctf.sh status shows them)"
  fi
  return 0
}

# --- commands ----------------------------------------------------------------

cmd_up() {
  local opt_host="" opt_domain="" opt_bind="" opt_port="" has_host=0 has_domain=0 has_bind=0
  local backup="" reimport=0 fresh=0 regcode="" has_regcode=0
  local opt_preview="" has_preview=0 opt_tenant="" has_tenant=0 opt_client="" has_client=0
  local opt_brand="" has_brand=0 opt_lang="" has_lang=0
  local opt_estart="" has_estart=0 opt_eend="" has_eend=0 opt_efreeze="" has_efreeze=0
  local opt_tsize="" has_tsize=0 opt_status="" has_status=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --host|--domain|--bind|--port|--backup|--registration-code|--preview|--sso-tenant|--sso-client-id|--brand|--lang|\
      --event-start|--event-end|--event-freeze|--team-size|--status)
        [[ $# -ge 2 ]] || die "$1 needs a value" ;;
    esac
    case "$1" in
      --host) opt_host="$2"; has_host=1; shift 2 ;;
      --domain) opt_domain="$2"; has_domain=1; shift 2 ;;
      --bind) opt_bind="$2"; has_bind=1; shift 2 ;;
      --port) opt_port="$2"; shift 2 ;;
      --backup) backup="$2"; shift 2 ;;
      --reimport) reimport=1; shift ;;
      --fresh) fresh=1; shift ;;
      --registration-code) regcode="$2"; has_regcode=1; shift 2 ;;
      --preview) opt_preview="$2"; has_preview=1; shift 2 ;;
      --sso-tenant) opt_tenant="$2"; has_tenant=1; shift 2 ;;
      --sso-client-id) opt_client="$2"; has_client=1; shift 2 ;;
      --brand) opt_brand="$2"; has_brand=1; shift 2 ;;
      --lang) opt_lang="$2"; has_lang=1; shift 2 ;;
      --event-start) opt_estart="$2"; has_estart=1; shift 2 ;;
      --event-end) opt_eend="$2"; has_eend=1; shift 2 ;;
      --event-freeze) opt_efreeze="$2"; has_efreeze=1; shift 2 ;;
      --team-size) opt_tsize="$2"; has_tsize=1; shift 2 ;;
      --status) opt_status="$2"; has_status=1; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) die "unknown option for up: $1 (see ./ctf.sh --help)" ;;
    esac
  done

  load_settings
  [[ $has_domain == 1 ]] && CTF_DOMAIN="$opt_domain"
  if [[ $has_host == 1 ]]; then CTF_HOST="$opt_host"
  elif [[ $has_domain == 1 && -n "$CTF_DOMAIN" ]]; then CTF_HOST="$CTF_DOMAIN"
  elif [[ $has_domain == 1 ]]; then CTF_HOST="localhost"
  fi
  CTF_HOST="${CTF_HOST:-${CTF_DOMAIN:-localhost}}"
  if [[ $has_bind == 1 ]]; then CTF_BIND="$opt_bind"
  elif [[ $has_domain == 1 || $has_host == 1 ]]; then
    if [[ -n "$CTF_DOMAIN" || ( "$CTF_HOST" != localhost && "$CTF_HOST" != 127.0.0.1 ) ]]; then
      CTF_BIND="0.0.0.0"
    else
      CTF_BIND="127.0.0.1"
    fi
  fi
  CTF_BIND="${CTF_BIND:-127.0.0.1}"
  [[ -n "$opt_port" ]] && CTFD_HTTP_PORT="$opt_port"
  CTFD_HTTP_PORT="${CTFD_HTTP_PORT:-80}"
  [[ -n "$backup" ]] || backup="$(newest_backup)"
  local old_preview="$CTF_PREVIEW" new_preview
  if [[ $has_preview == 1 ]]; then CTF_PREVIEW="$(preview_list "$opt_preview")" || exit 1; fi
  [[ $has_tenant == 1 ]] && CTF_SSO_TENANT="$opt_tenant"
  [[ $has_client == 1 ]] && CTF_SSO_CLIENT_ID="$opt_client"
  if [[ -n "$CTF_SSO_CLIENT_ID" ]]; then
    is_guid "$CTF_SSO_CLIENT_ID" || die "--sso-client-id takes the app registration's client id (a GUID)"
    is_guid "$CTF_SSO_TENANT" || die "--sso-client-id needs --sso-tenant with the Entra ID tenant id (a GUID)"
    [[ -n "$CTF_DOMAIN" ]] || warn "Microsoft sign-in only works in hosted mode (--domain); local CTFd stays open"
  fi
  if [[ $has_brand == 1 && -n "$opt_brand" ]]; then
    [[ -f "$opt_brand/brand.conf" ]] || die "--brand takes a folder with a brand.conf, like platform/theme/brand"
    opt_brand="$(cd "$opt_brand" && pwd)"
    CTF_BRAND="${opt_brand#"$REPO"/}"
  elif [[ $has_brand == 1 ]]; then
    CTF_BRAND=""
  fi
  read_brand # a brand folder that doesn't work stops here, before anything is saved
  if [[ $has_lang == 1 ]]; then
    # The languages are the ones in platform/theme/i18n.strings.js (and LANGUAGES in
    # platform/ctfd_admin.py).
    case "$opt_lang" in
      no|en) CTF_LANG="$opt_lang" ;;
      *) die "--lang takes no (Norwegian) or en (English)" ;;
    esac
  fi
  if [[ $has_estart == 1 ]]; then check_event_time --event-start "$opt_estart"; CTF_EVENT_START="$opt_estart"; fi
  if [[ $has_eend == 1 ]]; then check_event_time --event-end "$opt_eend"; CTF_EVENT_END="$opt_eend"; fi
  if [[ $has_efreeze == 1 ]]; then check_event_time --event-freeze "$opt_efreeze"; CTF_EVENT_FREEZE="$opt_efreeze"; fi
  if [[ $has_tsize == 1 ]]; then
    [[ -z "$opt_tsize" || "$opt_tsize" =~ ^[1-9][0-9]*$ ]] || die "--team-size takes a number of players, or \"\" to clear it"
    CTF_TEAM_SIZE="$opt_tsize"
  fi
  if [[ $has_status == 1 ]]; then
    case "$opt_status" in
      on|off) CTF_STATUS="$opt_status" ;;
      *) die "--status takes on or off" ;;
    esac
  fi
  case "$CTF_AI_MODE" in
    on|off) ;;
    *) die "CTF_AI_MODE takes on or off, not '$CTF_AI_MODE'" ;;
  esac

  preflight
  ensure_ctfd_source
  ensure_secrets up
  if sso_on && [[ -z "$CTF_SSO_CLIENT_SECRET" ]]; then
    die "Microsoft sign-in needs the client secret of app registration $CTF_SSO_CLIENT_ID once: SSO_CLIENT_SECRET=... ./ctf.sh up"
  fi
  sync_plugins "$CTF_PREVIEW"
  # A new preview is saved once CTFd has taken it, so one it rejects isn't kept.
  new_preview="$CTF_PREVIEW" CTF_PREVIEW="$old_preview"
  save_settings
  CTF_PREVIEW="$new_preview"
  export_compose_env

  log "Starting CTFd"
  ctfd_compose up -d --build --remove-orphans ctfd

  if [[ -n "$CTF_PREVIEW" ]]; then
    log "Building and starting the preview's challenges"
  else
    log "Building and starting challenges (the first build takes several minutes)"
  fi
  local running_before
  running_before="$(running_challenges)"
  start_challenges

  log "Waiting for CTFd"
  wait_for_ctfd

  local conf_args=() count imported=0
  count="$(challenge_count)"
  [[ "$count" =~ ^[0-9]+$ ]] || die "could not query CTFd (./ctf.sh status, then check the ctfd logs)"
  # An empty CTFd that this checkout has configured before has lost its data (a wiped
  # database, a recreated volume). Importing the backup over it would silently start
  # a new CTF in its place, with open registration and no dates: stop and say so.
  if [[ "$count" == 0 && $reimport == 0 && -f "$CONFIGURED_MARKER" && ! -f "$IMPORT_MARKER" ]]; then
    die "CTFd has no challenges, but this CTF was configured before: its data may be gone.
  Put the latest dump back with ./ctf.sh restore-db ctfd-backup/db/<file> (./ctf.sh backup --db makes them),
  or start over with ./ctf.sh up --reimport"
  fi
  if [[ $reimport == 1 || "$count" == 0 ]]; then
    ctfd_compose stop "$(proxy_service)"
    # Both write the import marker just before CTFd's data is replaced, so a crash
    # from there until a successful configure is recoverable on the next `up`.
    if [[ -n "$backup" ]]; then
      import_backup "$backup" "$fresh" "$regcode"
      if [[ $fresh == 1 ]]; then conf_args+=(--remove-participants); fi
    else
      new_ctf "$reimport" "$regcode"
    fi
    imported=1
    ADMIN_PASSWORD_SET=1  # a freshly imported or new CTFd needs the admin password set
    conf_args+=(--imported --clear-dates --registration-code "$regcode")
  elif [[ -f "$IMPORT_MARKER" ]]; then
    # A prior run imported the backup (or began a new CTF) but never finished configuring it (crash,
    # dropped SSH, rejected preview). Finish that import now instead of treating
    # CTFd as a running event: re-apply the import-time config so the previous
    # event's players and dates never reach a public board.
    warn "a previous import was not configured; finishing it (clearing dates, registration code, removing imported participants)"
    imported=1
    ADMIN_PASSWORD_SET=1  # the imported-but-unconfigured CTFd still needs the admin password set
    local m_fresh m_regcode
    m_fresh="$(sed -n 1p "$IMPORT_MARKER")"
    m_regcode="$(sed -n 2p "$IMPORT_MARKER")"
    [[ $has_regcode == 1 ]] || regcode="$m_regcode"
    conf_args+=(--imported --clear-dates --registration-code "$regcode")
    if [[ $fresh == 1 || "$m_fresh" == 1 ]]; then conf_args+=(--remove-participants); fi
  else
    if [[ $has_regcode == 1 ]]; then conf_args+=(--registration-code "$regcode"); fi
    if [[ $fresh == 1 ]]; then
      warn "--fresh ignored: CTFd already has data and nothing was imported (use --reimport --fresh to start over)"
    fi
  fi

  # The event's times and team size go to CTFd when given on this run ("" clears one),
  # and after an import, whose --clear-dates removed the backup's. Otherwise CTFd's own
  # stay, so a change made in the admin panel during the event isn't undone by an up.
  if [[ $has_estart == 1 || ( $imported == 1 && -n "$CTF_EVENT_START" ) ]]; then conf_args+=(--event-start "$CTF_EVENT_START"); fi
  if [[ $has_eend == 1 || ( $imported == 1 && -n "$CTF_EVENT_END" ) ]]; then conf_args+=(--event-end "$CTF_EVENT_END"); fi
  if [[ $has_efreeze == 1 || ( $imported == 1 && -n "$CTF_EVENT_FREEZE" ) ]]; then conf_args+=(--event-freeze "$CTF_EVENT_FREEZE"); fi
  if [[ $has_tsize == 1 || ( $imported == 1 && -n "$CTF_TEAM_SIZE" ) ]]; then conf_args+=(--team-size "$CTF_TEAM_SIZE"); fi

  log "Configuring CTFd"
  apply_config ${conf_args[@]+"${conf_args[@]}"}
  if [[ $CONFIGURE_RC == 3 ]]; then
    # Rejected before anything changed in CTFd. Put the rest back as well: stop the
    # challenges started above for it, and give CTFd the old preview's plugins.
    stop_started "$running_before"
    PLUGINS_CHANGED=0
    sync_plugins "$old_preview"
    if [[ $PLUGINS_CHANGED == 1 ]]; then
      log "Restarting CTFd with the plugins it had"
      ctfd_compose up -d --build ctfd
      wait_for_ctfd
    fi
    if [[ $imported == 1 ]]; then
      die "CTFd stays offline: it is imported or new but not configured (fix the preview, then ./ctf.sh up)"
    fi
    local kept=""
    if [[ "$has_host$has_domain$has_bind$has_tenant$has_client$has_brand$has_lang$has_estart$has_eend$has_efreeze$has_tsize$has_status" == *1* || -n "$opt_port" ]]; then
      kept="; this run's other options are saved"
    fi
    die "the board, the challenges and the saved preview are as they were$kept (fix the preview, then ./ctf.sh up)"
  fi
  [[ $CONFIGURE_RC == 0 ]] || die "configuring CTFd failed (see above)"
  # The import (if any) is now fully configured; clear the recovery marker and
  # record that this CTF has been configured at least once (azure.sh reads this).
  rm -f "$IMPORT_MARKER"
  : > "$CONFIGURED_MARKER"
  if [[ -n "$CTF_PREVIEW" ]]; then stop_outside_preview "$CTF_PREVIEW"; fi
  save_settings
  if status_on; then write_status_config; fi

  log "Starting $(proxy_service) ($(ctfd_url))"
  ctfd_compose up -d --remove-orphans

  echo
  log "Ready"
  cat <<EOF
  CTFd:      $(ctfd_url)
  Admin:     admin, password in ${ADMIN_PASSWORD_FILE#"$REPO"/}
  Challenges bound to $CTF_BIND, connection info uses host '$CTF_HOST'
  Language:  $CTF_LANG until a player switches with NO | EN in the navbar
EOF
  mode_summary
  cat <<EOF

  Stop:      ./ctf.sh down
  Status:    ./ctf.sh status
EOF
}

# The preview, sign-in, event and status page lines of the up and status summaries.
mode_summary() {
  if [[ -n "$CTF_PREVIEW" ]]; then
    printf '  Preview:   %s, without an account (./ctf.sh up --preview "" ends it)\n' "${CTF_PREVIEW//,/, }"
  fi
  if sso_on; then
    printf '  Sign-in:   Microsoft, Entra ID tenant %s\n' "$CTF_SSO_TENANT"
  fi
  if [[ -n "$CTF_EVENT_START$CTF_EVENT_END$CTF_EVENT_FREEZE$CTF_TEAM_SIZE" ]]; then
    printf '  Event:     start %s, end %s, freeze %s, team size %s (as last given to up)\n' \
      "${CTF_EVENT_START:--}" "${CTF_EVENT_END:--}" "${CTF_EVENT_FREEZE:--}" "${CTF_TEAM_SIZE:--}"
  fi
  if status_on; then
    printf '  Live page: %s (is everything up?)\n' "$(status_url)"
  fi
  return 0
}

cmd_connections() {
  local has_host=0 opt_host=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --host) [[ $# -ge 2 ]] || die "--host needs a value"; opt_host="$2"; has_host=1; shift 2 ;;
      *) die "unknown option for connections: $1" ;;
    esac
  done
  load_settings
  [[ $has_host == 1 ]] && CTF_HOST="$opt_host"
  CTF_HOST="${CTF_HOST:-localhost}"
  CTF_BIND="${CTF_BIND:-127.0.0.1}" CTFD_HTTP_PORT="${CTFD_HTTP_PORT:-80}"
  preflight
  ensure_secrets
  save_settings
  export_compose_env
  if [[ "$CTF_BIND" == 127.0.0.1 && "$CTF_HOST" != localhost && "$CTF_HOST" != 127.0.0.1 ]]; then
    warn "challenges only listen on 127.0.0.1; run './ctf.sh up --host $CTF_HOST' so others can reach them"
  fi
  log "Writing connection info for host '$CTF_HOST'"
  APPLY_CONNECTIONS_ONLY=1 apply_config
  [[ $CONFIGURE_RC == 0 ]] || die "configuring CTFd failed (see above)"
}

cmd_down() {
  load_settings
  preflight
  ensure_secrets
  export_compose_env
  log "Stopping challenges"
  challenges_compose down --remove-orphans
  if [[ -f "$CTFD_DIR/docker-compose.yml" ]]; then
    log "Stopping CTFd (data kept in ${CTFD_DIR#"$REPO"/}/.data)"
    ctfd_compose down --remove-orphans
  fi
}

cmd_status() {
  load_settings
  ensure_secrets
  export_compose_env
  if [[ -f "$CTFD_DIR/docker-compose.yml" ]]; then
    ctfd_compose ps
    echo
  fi
  challenges_compose ps
  echo
  mode_summary
}

cmd_logs() {
  load_settings
  ensure_secrets
  export_compose_env
  case "${1:-}" in
    ctfd|db|cache|nginx|caddy|oauth2-proxy|status) ctfd_compose logs -f --tail 100 "$1" ;;
    "") challenges_compose logs -f --tail 20 ;;
    *) challenges_compose logs -f --tail 100 "$1" ;;
  esac
}

# Recreate challenge containers from their images (no rebuild): that drops whatever
# players changed in them, which a restart keeps. noter5 and its backend go together,
# because the proxy seeds the flag into the backend when it starts.
cmd_reset() {
  [[ $# -gt 0 ]] || die "usage: ./ctf.sh reset <service>... (e.g. meow-ai; names as in ./ctf.sh status)"
  load_settings
  preflight
  ensure_secrets
  export_compose_env
  local svc known services=()
  known="$(challenges_compose config --services)"
  for svc in "$@"; do
    printf '%s\n' "$known" | grep -qx -- "$svc" || die "no challenge service '$svc' in ${CHALLENGES_COMPOSE#"$REPO"/}"
    case "$svc" in
      noter5|noter5-backend) services+=(noter5-backend noter5) ;;
      *) services+=("$svc") ;;
    esac
  done
  log "Recreating ${services[*]}"
  challenges_compose up -d --no-build --no-deps --force-recreate "${services[@]}"
}

# db_sql SQL: run SQL in CTFd's database; prints the rows tab-separated, no header.
db_sql() {
  ctfd_compose exec -T db sh -c \
    'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb -N -B -u"$MARIADB_USER" "$MARIADB_DATABASE" -e "$1"' sh "$1"
}

# backup_db [--if-event]: dump CTFd's database, gzipped SQL, into ctfd-backup/db/, and
# delete dumps there older than 7 days. It holds what changes during an event (players,
# teams, submissions, solves, unlocks, config); the uploaded files come from the
# backup and the repo. --if-event: only from 30 minutes before CTFd's start time to 30
# minutes after its end time, so a timer every 10 minutes dumps during the event only.
# With --if-event a CTF that isn't set up or running here is not an error either: the
# timer then has nothing to do (a new VM before its first up, or after ./ctf.sh down).
backup_db() {
  local target tmp start end now
  if [[ "${1:-}" == --if-event ]]; then
    if [[ ! -f "$CTFD_DIR/docker-compose.yml" ]] ||
      ! ctfd_compose ps --services --status running 2>/dev/null | grep -qx db; then
      echo "no dump: CTFd's database isn't running here"
      return 0
    fi
    start="$(db_sql "SELECT value FROM config WHERE \`key\` = 'start'")" &&
      end="$(db_sql "SELECT value FROM config WHERE \`key\` = 'end'")" ||
      die "could not read CTFd's database (./ctf.sh status)"
    if [[ ! "$start" =~ ^[0-9]+$ || ! "$end" =~ ^[0-9]+$ ]]; then
      echo "no dump: CTFd has no start and end time (./ctf.sh up --event-start ... --event-end ...)"
      return 0
    fi
    now="$(date +%s)"
    if (( now < start - 1800 || now > end + 1800 )); then
      echo "no dump: outside the event"
      return 0
    fi
  fi
  mkdir -p "$DB_BACKUP_DIR"
  target="$DB_BACKUP_DIR/ctfd.$(date +%Y-%m-%d_%H_%M_%S).sql.gz"
  tmp="$target.partial"
  # It holds players' emails and password hashes: readable by this user only.
  if ! (umask 077; ctfd_compose exec -T db sh -c \
      'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb-dump --single-transaction --quick --routines --triggers -u"$MARIADB_USER" "$MARIADB_DATABASE"' |
      gzip > "$tmp"); then
    rm -f "$tmp"
    die "the database dump failed (./ctf.sh status)"
  fi
  mv "$tmp" "$target"
  find "$DB_BACKUP_DIR" -name 'ctfd.*.sql.gz' -type f -mtime +7 -delete 2>/dev/null || true
  echo "wrote ${target#"$REPO"/}"
}

cmd_backup() {
  local db=0 if_event=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --db) db=1; shift ;;
      --if-event) if_event=1; shift ;;
      *) die "unknown option for backup: $1 (see ./ctf.sh --help)" ;;
    esac
  done
  [[ $if_event == 0 || $db == 1 ]] || die "--if-event goes with --db"
  load_settings
  preflight
  ensure_secrets
  export_compose_env
  if [[ $db == 1 ]]; then
    if [[ $if_event == 1 ]]; then backup_db --if-event; else backup_db; fi
    return 0
  fi
  local target out
  mkdir -p "$REPO/ctfd-backup"
  target="$REPO/ctfd-backup/local.$(date +%Y-%m-%d_%H_%M_%S).zip"
  log "Exporting CTFd"
  out="$(ctfd_compose exec -T ctfd python manage.py export_ctf /tmp/export.zip 2>&1)" ||
    die "the export failed: $(printf '%s\n' "$out" | tail -n 5)"
  out="$(ctfd_compose cp ctfd:/tmp/export.zip "$target" 2>&1)" ||
    die "could not copy the export out of the ctfd container: $out"
  ctfd_compose exec -T ctfd rm -f /tmp/export.zip
  echo "wrote ${target#"$REPO"/}"
}

# pick_dump: list the dumps in ctfd-backup/db/, newest first (their names sort by
# time), and ask for one by number. Sets PICKED_DUMP. The time is the one in the
# name, in this machine's time zone; the age next to it needs no time zone.
PICKED_DUMP=""
pick_dump() {
  local all=("$DB_BACKUP_DIR"/ctfd.*.sql.gz) dumps=() max=30 i f ts mtime now age size answer
  [[ -e "${all[0]}" ]] || die "no dumps in ctfd-backup/db/ (./ctf.sh backup --db makes one)"
  [[ -t 0 ]] || die "usage: ./ctf.sh restore-db FILE [--yes] (the dumps are in ctfd-backup/db/)"
  for (( i = ${#all[@]} - 1; i >= 0 && ${#dumps[@]} < max; i-- )); do dumps+=("${all[i]}"); done
  now="$(date +%s)"
  echo "CTFd's database dumps, newest first (times in $(date +%Z)):"
  for (( i = 0; i < ${#dumps[@]}; i++ )); do
    f="${dumps[i]}"
    ts="$(basename "$f" .sql.gz)"; ts="${ts#ctfd.}"
    ts="${ts%%_*} $(printf '%s' "${ts#*_}" | tr _ :)"
    # GNU stat, then BSD stat (macOS).
    mtime="$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo "$now")"
    age=$(( (now - mtime) / 60 ))
    if (( age < 1 )); then age="just now"
    elif (( age < 90 )); then age="$age min ago"
    elif (( age < 2880 )); then age="$(( age / 60 )) h ago"
    else age="$(( age / 1440 )) days ago"; fi
    size=$(( ($(wc -c < "$f") + 1023) / 1024 ))
    printf '  %2d)  %s   %-12s %6s KB\n' "$(( i + 1 ))" "$ts" "$age" "$size"
  done
  if (( ${#all[@]} > max )); then
    echo "  (the $max newest of ${#all[@]}; give an older one as FILE)"
  fi
  read -r -p "Restore which one? Its number (1 is the newest), or Enter to cancel: " answer
  [[ -n "$answer" ]] || die "aborted"
  [[ "$answer" =~ ^[0-9]+$ ]] && (( 10#$answer >= 1 && 10#$answer <= ${#dumps[@]} )) ||
    die "no dump number $answer"
  PICKED_DUMP="${dumps[10#$answer - 1]}"
}

# Put a dump from backup --db back: the database as it is now is dumped first, then
# the proxy stops (nobody plays against a half-restored CTFd), the dump replaces
# every table, CTFd's cache is emptied and CTFd restarts. Without a file, pick_dump
# asks which one; a bare file name is looked up in ctfd-backup/db/.
cmd_restore_db() {
  local file="" yes=0 answer reader
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --yes|-y) yes=1; shift ;;
      -*) die "unknown option for restore-db: $1 (see ./ctf.sh --help)" ;;
      *) [[ -z "$file" ]] || die "restore-db takes one file"; file="$1"; shift ;;
    esac
  done
  if [[ -z "$file" ]]; then
    pick_dump
    file="$PICKED_DUMP"
  elif [[ ! -f "$file" && "$file" != */* && -f "$DB_BACKUP_DIR/$file" ]]; then
    file="$DB_BACKUP_DIR/$file"
  fi
  [[ -f "$file" ]] || die "no such file: $file"
  load_settings
  preflight
  ensure_secrets
  export_compose_env
  if [[ $yes != 1 ]]; then
    [[ -t 0 ]] || die "rerun with --yes to replace CTFd's database with $file"
    read -r -p "Replace CTFd's database with $(basename "$file")? Everything after that dump is lost. Type yes: " answer
    [[ "$answer" == yes ]] || die "aborted"
  fi
  log "Dumping the database as it is now"
  backup_db
  log "Stopping $(proxy_service)"
  ctfd_compose stop "$(proxy_service)" >/dev/null 2>&1 || true
  log "Restoring $(basename "$file")"
  reader=(cat)
  if [[ "$file" == *.gz ]]; then reader=(gzip -dc); fi
  "${reader[@]}" "$file" | ctfd_compose exec -T db sh -c \
    'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb -u"$MARIADB_USER" "$MARIADB_DATABASE"' ||
    die "the restore failed; $(proxy_service) stays stopped (the dump taken just before is in ctfd-backup/db/)"
  # CTFd keeps config, challenges and standings in Redis; drop them with the old data.
  ctfd_compose exec -T cache redis-cli FLUSHALL >/dev/null
  ctfd_compose restart ctfd >/dev/null
  wait_for_ctfd
  log "Starting $(proxy_service) ($(ctfd_url))"
  ctfd_compose up -d --remove-orphans
}

# compose.yml pins linux/amd64 on the challenges that need it; everything else runs
# natively. A global DOCKER_DEFAULT_PLATFORM would force it onto CTFd, MariaDB and
# Redis too, and compose fails when a cached image lacks that platform.
if [[ -n "${DOCKER_DEFAULT_PLATFORM:-}" ]]; then
  warn "ignoring DOCKER_DEFAULT_PLATFORM=$DOCKER_DEFAULT_PLATFORM (platforms are set per service in compose.yml)"
  unset DOCKER_DEFAULT_PLATFORM
fi

case "${1:-}" in
  up) shift; cmd_up "$@" ;;
  down) shift; cmd_down "$@" ;;
  status) shift; cmd_status "$@" ;;
  connections) shift; cmd_connections "$@" ;;
  logs) shift; cmd_logs "$@" ;;
  reset) shift; cmd_reset "$@" ;;
  backup) shift; cmd_backup "$@" ;;
  restore-db) shift; cmd_restore_db "$@" ;;
  -h|--help|help|"") usage ;;
  *) die "unknown command: $1 (see ./ctf.sh --help)" ;;
esac
