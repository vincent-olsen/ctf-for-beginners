#!/usr/bin/env bash
# Run the CTF on a VM in Azure (docs/azure.md): resource group, network, VM
# and DNS record, then ./ctf.sh up --domain on the VM. A deployment is short-lived: a
# nightly job deletes its resource group once the expires-on date has passed.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${CTF_STATE_DIR:-$REPO/.ctf}/azure"
KEY="$STATE/id_ed25519"
BICEP="$REPO/platform/azure/main.bicep"
BOOTSTRAP="$REPO/platform/azure/bootstrap.sh"
WORKLOAD=ctf
ADMIN_USER=ctfadmin
REMOTE_DIR=ctf-for-n00bs # on the VM, in the admin user's home
DEFAULT_LOCATION=norwayeast
DEFAULT_SIZE=Standard_D4s_v5
DEFAULT_SHUTDOWN=2300
DEFAULT_START=0730
DEFAULT_DAYS=30
MAX_DAYS=31

usage() {
  cat <<EOF
usage: ./azure.sh <command> [options]

Runs the CTF on a VM in Azure (docs/azure.md). Each environment is one resource group,
rsg-<env>-ctf, deleted automatically in the night after its expiry date.

commands:
  up            create or update the deployment and start the CTF on it (safe to rerun)
  deploy        copy this checkout to the VM and rerun ./ctf.sh up there (a challenge fix)
  open          event mode: challenges reachable from the internet, no nightly shutdown
  close         test mode: challenges only for the admin addresses, nightly shutdown (unless off)
  allow-me      add this machine's public IP to the admin addresses
  status        expiry, VM, mode and the CTF's containers
  extend DATE   move the expiry to DATE (YYYY-MM-DD, or +N for N days from today)
  start | stop  start or deallocate the VM (while stopped, only the disk and IP cost)
  ssh [CMD]     shell on the VM, or run CMD there
  backup        export CTFd to ctfd-backup/local.<timestamp>.zip in this checkout
  restore [FILE]
                put CTFd's database back as it was at one of the VM's dumps: lists them,
                newest first, and asks which one (or FILE: a dump's name on the VM)
  down          delete the deployment: its resource group and DNS records

options:
  --env tst|prd             environment (default: tst): tst to test, prd for the event
  --subscription NAME|ID    Azure subscription (default: az's current one, then remembered)
  --yes                     don't ask for confirmation

options for up (left out, the deployed value is kept):
  --domain NAME             address of CTFd, e.g. ctf.example.com (needed by a new deployment)
  --days N | --expires DATE expiry (a new deployment: $DEFAULT_DAYS days; at most $MAX_DAYS days ahead)
  --admin-ip CIDR[,CIDR]    addresses for SSH and closed challenges (this machine's IP is added)
  --player-ip CIDR[,CIDR]|none
                            addresses that always reach the challenges, but not SSH (an
                            office and its VPN, say)
  --size SIZE               VM size (default: $DEFAULT_SIZE)
  --location REGION         region of a new deployment (default: $DEFAULT_LOCATION)
  --shutdown HHMM|off       nightly shutdown in Oslo time while closed (default: $DEFAULT_SHUTDOWN)
  --start HHMM|off          start the VM Monday to Friday at HHMM Oslo time (default: off)
  --notify EMAIL|none       who gets the shutdown warning (default: your Azure account)
  --registration-code CODE  CTFd registration code ("" = open; a new CTF gets a random one)
  --egress block|allow      new connections out of challenge containers (default: block)
  --dns-zone-id ID|none     Azure DNS zone for the record (default: found automatically)
  --preview NAMES           only these challenges (e.g. julius,meow1), playable without a
                            CTFd account ("" ends the preview)
  --sso-client-id ID        sign in with Microsoft before reaching CTFd: the Entra ID app
                            registration in the subscription's tenant; asks for its client
                            secret ("" turns sign-in off)
  --lang no|en              the language players see until they switch with NO | EN
                            (default: en)
  --event-start TIME        CTFd's start time with its UTC offset, e.g. 2026-11-18T16:00+01:00
  --event-end TIME          CTFd's end time, the same way (the VM dumps CTFd's database
                            every 10 minutes from 30 minutes before the start to 30 after the end)
  --event-freeze TIME       when the scoreboard freezes, the same way
  --team-size N             most players in a team ("" clears any of these four)
  --status on|off           the status page at https://status.<domain> (default: on; its DNS
                            record is made either way)

deploy also takes --registration-code, --egress, --preview, --sso-client-id, --lang,
--event-start, --event-end, --event-freeze, --team-size and --status; open, close and
allow-me take --days and --expires; down takes --backup (export first). The VM keeps
--preview, --sso-client-id, --lang, the event's times, team size and --status for later runs.

Environment: ADMIN_PASSWORD sets CTFd's admin password (default: generated on the VM).
             SSO_CLIENT_SECRET is the client secret for --sso-client-id (default: asked).
EOF
}

log()  { printf '\033[1;34m==>\033[0m \033[1m%s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

need() {
  local c
  for c in "$@"; do
    if ! command -v "$c" >/dev/null; then
      [[ "$c" == az ]] && die "the Azure CLI is not installed: https://learn.microsoft.com/cli/azure/install-azure-cli"
      die "$c is not installed"
    fi
  done
}

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
random_hex() { head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'; }

confirm() {
  [[ $YES == 1 ]] && return 0
  [[ -t 0 ]] || die "$1 Rerun with --yes to confirm."
  local answer
  read -r -p "$1 [y/N] " answer
  [[ "$answer" == [yY] || "$answer" == [yY][eE][sS] ]]
}

# --- dates (UTC; GNU date on Linux, BSD date on macOS) -------------------------

if date -u -d @0 +%s >/dev/null 2>&1; then
  epoch_of() { date -u -d "$1 00:00:00" +%s 2>/dev/null; }
  date_of() { date -u -d "@$1" +%F; }
else
  epoch_of() { date -u -j -f '%Y-%m-%d %H:%M:%S' "$1 00:00:00" +%s 2>/dev/null; }
  date_of() { date -u -r "$1" +%F; }
fi
today() { date -u +%F; }
plus_days() { date_of $(( $(epoch_of "$(today)") + $1 * 86400 )); }
days_until() { echo $(( ( $(epoch_of "$1") - $(epoch_of "$(today)") ) / 86400 )); }

valid_date() {
  local e
  [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && e="$(epoch_of "$1")" && [[ "$(date_of "$e")" == "$1" ]]
}

# A deployment lives at most MAX_DAYS from today; extend it again for longer.
check_expiry() {
  valid_date "$1" || die "not a date: $1 (use YYYY-MM-DD)"
  local n
  n="$(days_until "$1")"
  (( n >= 0 )) || die "$1 is in the past"
  (( n <= MAX_DAYS )) || die "$1 is $n days away; a deployment lives at most $MAX_DAYS days from today (extend it again later)"
}

valid_hhmm() { [[ "$1" =~ ^([01][0-9]|2[0-3])[0-5][0-9]$ ]]; }
hhmm() { printf '%s:%s' "${1:0:2}" "${1:2:2}"; }

# --- values -------------------------------------------------------------------

# Values are checked for quotes, backslashes and control characters before they get
# here (json_safe), so quoting them is enough.
json_str() { printf '"%s"' "$1"; }

json_safe() {
  local v
  for v in "$@"; do
    case "$v" in *[\\\"]* | *[[:cntrl:]]*) die "can't pass this value to Azure: $v" ;; esac
  done
}

# Free text (a git user.name) loses quotes and backslashes rather than failing.
plain() { printf '%s' "${1//[\\\"]/}"; }

json_list() {
  local out="" x
  for x in "$@"; do out+="${out:+, }$(json_str "$x")"; done
  printf '[%s]' "$out"
}

# cidr_list "a,b c": IPv4 addresses and CIDRs, normalized (/32 added) and deduplicated.
cidr_list() {
  local out="" x words=()
  IFS=', ' read -r -a words <<< "$*"
  for x in ${words[@]+"${words[@]}"}; do
    [[ -n "$x" ]] || continue
    [[ "$x" == */* ]] || x="$x/32"
    [[ "$x" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}/[0-9]{1,2}$ ]] || die "not an IPv4 address or CIDR: $x"
    case ",$out," in *",$x,"*) ;; *) out="${out:+$out,}$x" ;; esac
  done
  printf '%s' "$out"
}

my_ip() {
  local url ip
  for url in https://api.ipify.org https://ipv4.icanhazip.com https://ifconfig.me/ip; do
    ip="$(curl -4 -fsS --max-time 6 "$url" 2>/dev/null | tr -d '[:space:]')" || continue
    if [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then printf '%s' "$ip"; return 0; fi
  done
  return 1
}

# Host ports compose.yml publishes, merged into ranges (1241-1246) for the NSG rule.
challenge_port_ranges() {
  sed -nE 's/.*[$][{]CTF_BIND[^}]*[}]:([0-9]+):[0-9]+.*/\1/p' "$REPO/compose.yml" | sort -n -u |
    awk 'NR == 1 { s = e = $1; next }
         $1 == e + 1 { e = $1; next }
         { print (s == e ? s : s "-" e); s = e = $1 }
         END { if (NR) print (s == e ? s : s "-" e) }'
}

# The domain is the deployment's: given with --domain on its first up, then kept in the
# resource group's domain tag.
need_domain() {
  [[ -n "$DOMAIN" ]] || die "$RG has no domain yet: ./azure.sh up --env $ENV --domain NAME (the address of CTFd, e.g. ctf.example.com)"
}
default_owner() { git config user.name 2>/dev/null || printf '%s' "$AZ_USER"; }
default_email() {
  if [[ "$AZ_USER" == *@* ]]; then printf '%s' "$AZ_USER"; else git config user.email 2>/dev/null || true; fi
}

# --- state ---------------------------------------------------------------------
# Azure holds the settings (tags, NSG rules, the shutdown schedule); .ctf/azure keeps
# the SSH key and a few local notes per environment.

load_state() {
  SUB="" DNS_ZONE_ID="" DNS_NAME="" DNS_IP="" REGCODE="" REGCODE_PENDING=0
  if [[ -f "$STATE/$ENV.env" ]]; then
    # shellcheck source=/dev/null
    . "$STATE/$ENV.env"
  fi
}

save_state() {
  mkdir -p "$STATE"
  printf '%s=%q\n' SUB "$SUB" DNS_ZONE_ID "$DNS_ZONE_ID" DNS_NAME "$DNS_NAME" DNS_IP "$DNS_IP" \
    REGCODE "$REGCODE" REGCODE_PENDING "$REGCODE_PENDING" > "$STATE/$ENV.env"
}

forget_local() {
  rm -f "$STATE/$ENV.env" "$STATE/$ENV.known_hosts" "$STATE/$ENV.ssh_config" "$STATE/$ENV.parameters.json"
}

select_subscription() {
  local want=${OPT_SUBSCRIPTION:-$SUB} q="join('|', [id, name, tenantId, user.name])" line
  if [[ -n "$want" ]]; then
    line="$(az account show --subscription "$want" --query "$q" -o tsv 2>/dev/null)" ||
      die "no subscription '$want' for this login (az login, or see az account list)"
  else
    line="$(az account show --query "$q" -o tsv 2>/dev/null)" || die "not logged in to Azure: run az login"
  fi
  IFS='|' read -r SUB SUB_NAME TENANT AZ_USER <<< "$line"
}

set_names() {
  NAME="$ENV-$WORKLOAD"
  RG="rsg-$NAME" VM="srv-$NAME" NSG="nsg-$NAME" PIP="pip-$NAME"
  RG_ID="/subscriptions/$SUB/resourceGroups/$RG"
  PIP_ID="$RG_ID/providers/Microsoft.Network/publicIPAddresses/$PIP"
  SCHEDULE_ID="$RG_ID/providers/Microsoft.DevTestLab/schedules/shutdown-computevm-$VM"
  EXPIRY_ID="$RG_ID/providers/Microsoft.Logic/workflows/logic-$NAME-expiry"
  START_ID="$RG_ID/providers/Microsoft.Logic/workflows/logic-$NAME-start"
  VM_ID="$RG_ID/providers/Microsoft.Compute/virtualMachines/$VM"
  SSH_CONFIG="$STATE/$ENV.ssh_config" KNOWN_HOSTS="$STATE/$ENV.known_hosts" HOST_ALIAS="ctf-$ENV"
}

azs() { az "$@" --subscription "$SUB" --only-show-errors; }

# Run the az read "$@" and print its output. A missing resource prints nothing (the
# deployment doesn't have it yet). Any other failure (network, throttling, an expired
# login) stops the script: read as "nothing there", it would redeploy defaults over
# the real settings, e.g. close the challenges or drop the organisers' IPs.
az_read() {
  local out err rc=0
  err="$(mktemp)"
  out="$("$@" 2>"$err")" || rc=$?
  # Azure's codes for it: (NotFound), (ResourceNotFound), (ResourceGroupNotFound), ...
  if (( rc != 0 )) && ! grep -qE 'NotFound\)|Code: [A-Za-z]*NotFound' "$err"; then
    cat "$err" >&2; rm -f "$err"
    die "could not read the deployment from Azure (above); nothing was changed, try again"
  fi
  rm -f "$err"
  (( rc != 0 )) || printf '%s' "$out"
}

# --- reading the deployment ----------------------------------------------------

# CUR_LOCATION CUR_DOMAIN CUR_EXPIRES CUR_OWNER CUR_CONTACT; fails without the group.
load_rg() {
  local out
  CUR_LOCATION="" CUR_DOMAIN="" CUR_EXPIRES="" CUR_OWNER="" CUR_CONTACT=""
  out="$(az_read azs group show -n "$RG" -o tsv --query \
    "join('|', [location, tags.domain || '', tags.\"expires-on\" || '', tags.owner || '', tags.contact || ''])")" ||
    exit 1
  [[ -n "$out" ]] || return 1
  IFS='|' read -r CUR_LOCATION CUR_DOMAIN CUR_EXPIRES CUR_OWNER CUR_CONTACT <<< "$out"
}

# CUR_SIZE CUR_KEY POWER PUBLIC_IP; fails without the VM.
load_vm() {
  local out
  CUR_SIZE="" CUR_KEY="" POWER="" PUBLIC_IP=""
  out="$(az_read azs vm show -d -g "$RG" -n "$VM" -o tsv --query \
    "join('|', [hardwareProfile.vmSize, powerState || '', publicIps || '', osProfile.linuxConfiguration.ssh.publicKeys[0].keyData])")" ||
    exit 1
  [[ -n "$out" ]] || return 1
  IFS='|' read -r CUR_SIZE POWER PUBLIC_IP CUR_KEY <<< "$out"
}

# The source prefixes of NSG rule $1, comma-separated; nothing without the rule.
nsg_sources() {
  local out
  out="$(az_read azs network nsg rule show -g "$RG" --nsg-name "$NSG" -n "$1" -o tsv \
    --query '[sourceAddressPrefix, sourceAddressPrefixes[]][]')" || exit 1
  printf '%s\n' "$out" | grep -v '^$' | paste -s -d, - || true
}

# CUR_ADMIN CUR_PLAYERS CUR_OPEN CUR_SHUTDOWN_ON CUR_SHUTDOWN_PREF CUR_SHUTDOWN CUR_NOTIFY
# CUR_START. CUR_SHUTDOWN_ON is the schedule's status (always Disabled while open);
# CUR_SHUTDOWN_PREF its auto-shutdown tag, on or off, the setting to use while closed.
# CUR_START is the morning start's auto-start tag, HHMM or off (empty: no such job yet).
load_config() {
  local out
  CUR_ADMIN="$(nsg_sources allow-ssh-admin)" || exit 1
  CUR_PLAYERS="$(nsg_sources allow-challenges-players)" || exit 1
  out="$(nsg_sources allow-challenges)" || exit 1
  case ",$out," in
    ,,) CUR_OPEN="" ;;
    *,Internet,* | *,\*,* | *,0.0.0.0/0,*) CUR_OPEN=1 ;;
    *) CUR_OPEN=0 ;;
  esac
  out="$(az_read az resource show --ids "$SCHEDULE_ID" --only-show-errors -o tsv --query \
    "join('|', [properties.status, tags.\"auto-shutdown\" || '', properties.dailyRecurrence.time, properties.notificationSettings.emailRecipient || ''])")" ||
    exit 1
  IFS='|' read -r CUR_SHUTDOWN_ON CUR_SHUTDOWN_PREF CUR_SHUTDOWN CUR_NOTIFY <<< "$out"
  CUR_START="$(az_read az resource show --ids "$START_ID" --only-show-errors -o tsv --query \
    "tags.\"auto-start\" || ''")" || exit 1
}

# What to deploy: an option, else the deployed value, else the default.
resolve_settings() {
  DOMAIN="$(lower "${OPT_DOMAIN:-$CUR_DOMAIN}")"
  need_domain
  if [[ -n "$OPT_LOCATION" && -n "$CUR_LOCATION" && "$(lower "$OPT_LOCATION")" != "$(lower "$CUR_LOCATION")" ]]; then
    die "$RG is in $CUR_LOCATION and can't move (./azure.sh down first)"
  fi
  LOCATION="$(lower "${CUR_LOCATION:-${OPT_LOCATION:-$DEFAULT_LOCATION}}")"
  VM_SIZE="${OPT_SIZE:-${CUR_SIZE:-$DEFAULT_SIZE}}"
  ADMIN_CIDRS="$(cidr_list "${OPT_ADMIN:-$CUR_ADMIN}")"
  if [[ $HAS_PLAYERS == 1 ]]; then
    PLAYER_CIDRS=""
    [[ "$OPT_PLAYERS" == none ]] || PLAYER_CIDRS="$(cidr_list "$OPT_PLAYERS")"
  else
    PLAYER_CIDRS="$(cidr_list "${CUR_PLAYERS:-}")"
  fi
  OPEN="${CUR_OPEN:-0}"

  # SHUTDOWN_ON is the setting for while closed; main.bicep turns the schedule off
  # while open, whatever it says. A schedule from before the auto-shutdown tag is off
  # while closed only when someone turned it off.
  SHUTDOWN_TIME="${CUR_SHUTDOWN:-$DEFAULT_SHUTDOWN}" SHUTDOWN_ON=true
  if [[ "$CUR_SHUTDOWN_PREF" == off ]] ||
    [[ -z "$CUR_SHUTDOWN_PREF" && "$CUR_SHUTDOWN_ON" == Disabled && "$CUR_OPEN" != 1 ]]; then
    SHUTDOWN_ON=false
  fi
  case "$OPT_SHUTDOWN" in
    "") ;;
    off) SHUTDOWN_ON=false ;;
    *) valid_hhmm "$OPT_SHUTDOWN" || die "--shutdown takes HHMM (e.g. 2300) or off"
       SHUTDOWN_TIME=$OPT_SHUTDOWN SHUTDOWN_ON=true ;;
  esac

  START_TIME=$DEFAULT_START START_ON=false
  if valid_hhmm "$CUR_START"; then START_TIME=$CUR_START START_ON=true; fi
  case "$OPT_START" in
    "") ;;
    off) START_ON=false ;;
    *) valid_hhmm "$OPT_START" || die "--start takes HHMM (e.g. 0730) or off"
       START_TIME=$OPT_START START_ON=true ;;
  esac

  if [[ -n "$OPT_NOTIFY" ]]; then
    NOTIFY=$OPT_NOTIFY
    [[ "$NOTIFY" != none ]] || NOTIFY=""
  elif [[ -n "$CUR_SHUTDOWN_ON" ]]; then
    NOTIFY=$CUR_NOTIFY
  else
    NOTIFY="$(default_email)"
  fi
  OWNER="$(plain "${CUR_OWNER:-$(default_owner)}")"
  CONTACT="$(plain "${CUR_CONTACT:-$(default_email)}")"
  NOTIFY="$(plain "$NOTIFY")"

  if [[ -n "$OPT_EXPIRES" ]]; then
    check_expiry "$OPT_EXPIRES"
    EXPIRES=$OPT_EXPIRES
  elif [[ -n "$CUR_EXPIRES" ]]; then
    EXPIRES=$CUR_EXPIRES
    valid_date "$EXPIRES" || die "$RG has an unreadable expires-on tag '$EXPIRES'; set one with ./azure.sh extend"
    # Keep the deployed date, but don't accept a past or out-of-range one silently.
    local n_exp; n_exp="$(days_until "$EXPIRES")"
    if (( n_exp <= 0 )); then
      warn "$RG's expires-on tag $EXPIRES is today or past; the nightly job deletes it tonight. Set a new date with ./azure.sh extend --env $ENV."
    elif (( n_exp > MAX_DAYS )); then
      warn "$RG's expires-on tag $EXPIRES is $n_exp days away, beyond the $MAX_DAYS-day cap; set a nearer date with ./azure.sh extend --env $ENV."
    fi
  else
    EXPIRES="$(plus_days "$DEFAULT_DAYS")"
  fi
}

# --- Azure ---------------------------------------------------------------------

ensure_ssh_key() {
  if [[ ! -f "$KEY" ]]; then
    (umask 077; mkdir -p "$STATE")
    ssh-keygen -q -t ed25519 -N '' -C "ctf-azure $(whoami)@$(hostname)" -f "$KEY"
  fi
}

# merge_rg_tags KEY=VALUE...: set these tags on the group and keep its others. Through
# the group itself (resourcegroups/write), not "az tag update": that needs
# Microsoft.Resources/tags/write, which a role that may create the group can lack.
merge_rg_tags() {
  local sets=() kv
  for kv in "$@"; do sets+=(--set "tags.$kv"); done
  azs group update -n "$RG" "${sets[@]}" -o none
}

ensure_resource_group() {
  local tags=(owner="$OWNER" contact="$CONTACT" project=ctf environment="$ENV" domain="$DOMAIN"
    managed-by=azure.sh expires-on="$EXPIRES")
  if [[ "$(azs group exists -n "$RG")" == true ]]; then
    merge_rg_tags "${tags[@]}"
  else
    log "Creating resource group $RG in $LOCATION"
    azs group create -n "$RG" -l "$LOCATION" --tags "${tags[@]}" created-on="$(today)" -o none
  fi
}

# Move the expiry of the existing group to $1 (checked already).
set_expiry() {
  merge_rg_tags expires-on="$1"
  log "$RG expires $1 (was ${CUR_EXPIRES:-unset}) and is deleted in the night after"
}

# Deploy platform/azure/main.bicep with the resolved settings and VM_KEY; sets
# PUBLIC_IP, EXPIRY_PRINCIPAL and START_PRINCIPAL.
deploy_infra() {
  local params="$STATE/$ENV.parameters.json" name out ports=() admin=() players=() p
  name="ctf-$ENV-$(date -u +%Y%m%d-%H%M%S)"
  while IFS= read -r p; do ports+=("$p"); done < <(challenge_port_ranges)
  [[ ${#ports[@]} -gt 0 ]] || die "found no challenge ports in compose.yml"
  IFS=',' read -r -a admin <<< "$ADMIN_CIDRS"
  [[ ${#admin[@]} -gt 0 ]] || die "no admin addresses (--admin-ip)"
  if [[ -n "$PLAYER_CIDRS" ]]; then IFS=',' read -r -a players <<< "$PLAYER_CIDRS"; fi
  json_safe "$ENV" "$LOCATION" "$VM_SIZE" "$VM_KEY" "$SHUTDOWN_TIME" "$START_TIME" "$NOTIFY" "$OWNER" "$CONTACT" \
    "${admin[@]}" ${players[@]+"${players[@]}"} "${ports[@]}"
  mkdir -p "$STATE"
  cat > "$params" <<EOF
{
  "\$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "env": { "value": $(json_str "$ENV") },
    "workload": { "value": $(json_str "$WORKLOAD") },
    "location": { "value": $(json_str "$LOCATION") },
    "vmSize": { "value": $(json_str "$VM_SIZE") },
    "adminUsername": { "value": $(json_str "$ADMIN_USER") },
    "sshPublicKey": { "value": $(json_str "$VM_KEY") },
    "adminSourcePrefixes": { "value": $(json_list "${admin[@]}") },
    "playerSourcePrefixes": { "value": $(json_list ${players[@]+"${players[@]}"}) },
    "challengePorts": { "value": $(json_list "${ports[@]}") },
    "challengesOpen": { "value": $([[ $OPEN == 1 ]] && echo true || echo false) },
    "autoShutdownTime": { "value": $(json_str "$SHUTDOWN_TIME") },
    "autoShutdownEnabled": { "value": $SHUTDOWN_ON },
    "autoStartTime": { "value": $(json_str "$START_TIME") },
    "autoStartEnabled": { "value": $START_ON },
    "notificationEmail": { "value": $(json_str "$NOTIFY") },
    "tags": { "value": {
      "owner": $(json_str "$OWNER"),
      "contact": $(json_str "$CONTACT"),
      "project": "ctf",
      "environment": $(json_str "$ENV"),
      "managed-by": "azure.sh"
    } }
  }
}
EOF
  log "Deploying the Azure resources (the first time takes a few minutes)"
  azs deployment group create -g "$RG" -n "$name" -f "$BICEP" -p @"$params" -o none
  out="$(azs deployment group show -g "$RG" -n "$name" -o tsv --query \
    "join('|', [properties.outputs.publicIp.value, properties.outputs.expiryPrincipalId.value, properties.outputs.startPrincipalId.value])")"
  IFS='|' read -r PUBLIC_IP EXPIRY_PRINCIPAL START_PRINCIPAL <<< "$out"
}

# Let the jobs act: the nightly expiry deletes the group, the morning start starts the
# VM. Each Logic App runs as its own system-assigned identity: the expiry job needs
# Contributor on the group, the morning start only Virtual Machine Contributor on the
# VM, and only while --start is on (a disabled job keeps no role). Handing a role out,
# or taking one back, takes Owner or User Access Administrator. Without them the
# deployment still works, but nothing deletes it or starts it in the morning. Sets
# EXPIRY_ARMED and START_ARMED.
arm_jobs() {
  local cmds=() what=()
  EXPIRY_ARMED=0 START_ARMED=0
  if arm_job "$EXPIRY_ID" "$EXPIRY_PRINCIPAL" "logic-$NAME-expiry" Contributor "$RG_ID"; then
    EXPIRY_ARMED=1
  else
    what+=("the expiry job can't delete $RG")
    [[ -z "$ROLE_CMD" ]] || cmds+=("$ROLE_CMD")
  fi
  # Contributor on the group is what the morning start was given before.
  drop_roles "$START_PRINCIPAL" "$RG_ID" "logic-$NAME-start"
  if [[ $START_ON != true ]]; then
    drop_roles "$START_PRINCIPAL" "$VM_ID" "logic-$NAME-start"
  elif arm_job "$START_ID" "$START_PRINCIPAL" "logic-$NAME-start" "Virtual Machine Contributor" "$VM_ID"; then
    START_ARMED=1
  else
    what+=("the morning start (--start) can't start the VM")
    [[ -z "$ROLE_CMD" ]] || cmds+=("$ROLE_CMD")
  fi
  [[ ${#cmds[@]} -gt 0 ]] || return 0
  local msg
  msg="$(printf '%s, and ' "${what[@]}")"
  msg="${msg%, and }: handing out the role needs Owner or User Access Administrator.
  Ask an Owner of the subscription to run this once:
$(printf '    %s\n' "${cmds[@]}")"
  [[ $EXPIRY_ARMED == 1 ]] || msg+="
  Until then, delete it yourself by $EXPIRES: ./azure.sh down --env $ENV"
  warn "$msg"
}

# arm_job LOGIC_APP_ID PRINCIPAL LABEL ROLE SCOPE: give that Logic App's identity ROLE
# on SCOPE, or return 1 with the command an Owner needs to run in ROLE_CMD.
arm_job() {
  local n out
  ROLE_CMD=""
  if job_armed "$1" "$5"; then return 0; fi
  [[ -n "$2" ]] || { warn "the deployment reported no identity for $3"; return 1; }
  ROLE_CMD="az role assignment create --assignee-object-id $2 --assignee-principal-type ServicePrincipal --role '$4' --scope $5"
  for n in 1 2 3 4 5 6; do
    if out="$(az role assignment create --assignee-object-id "$2" \
      --assignee-principal-type ServicePrincipal --role "$4" --scope "$5" \
      --only-show-errors -o none 2>&1)"; then
      return 0
    fi
    case "$out" in
      *RoleAssignmentExists* | *"already exists"*) return 0 ;;
      *AuthorizationFailed* | *"does not have authorization"*) break ;;
    esac
    sleep 10 # a new managed identity takes a moment to reach Entra ID
  done
  return 1
}

# drop_roles PRINCIPAL SCOPE LABEL: remove that identity's role assignments on SCOPE
# itself, if it has any; warns with the command for an Owner when that is refused.
drop_roles() {
  local ids
  [[ -n "$1" ]] || return 0
  ids="$(az role assignment list --scope "$2" --only-show-errors -o tsv \
    --query "[?principalId=='$1'].id" 2>/dev/null)" || return 0
  [[ -n "$ids" ]] || return 0
  # shellcheck disable=SC2086 # one id per word
  az role assignment delete --ids $ids --only-show-errors -o none 2>/dev/null ||
    warn "$3 keeps a role it no longer needs; an Owner can remove it with:
    az role assignment delete --ids $(echo $ids)"
}

# job_armed LOGIC_APP_ID [SCOPE]: does that Logic App's identity have a role on SCOPE
# (the group by default)?
job_armed() {
  local pid n
  pid="$(az resource show --ids "$1" --query identity.principalId -o tsv --only-show-errors 2>/dev/null)" || return 1
  [[ -n "$pid" ]] || return 1
  n="$(az role assignment list --scope "${2:-$RG_ID}" --only-show-errors -o tsv \
    --query "length([?principalId=='$pid'])" 2>/dev/null)" || return 1
  [[ "$n" =~ ^[1-9] ]]
}

# Start the VM unless it runs; BOOTING=1 when it has yet to come up.
ensure_running() {
  local p
  p="$(azs vm show -d -g "$RG" -n "$VM" --query powerState -o tsv)"
  [[ "$p" == "VM running" ]] && return 0
  log "Starting $VM (${p#VM })"
  azs vm start -g "$RG" -n "$VM" -o none
  BOOTING=1
}

# --- DNS -------------------------------------------------------------------------

# The Azure DNS zone holding DOMAIN: the longest zone name it ends with, among the
# zones in every subscription of this tenant you can read.
find_dns_zone() {
  local sub name id best="" len=0
  for sub in $(az account list --query "[?state=='Enabled' && tenantId=='$TENANT'].id" -o tsv 2>/dev/null); do
    while IFS=$'\t' read -r name id; do
      name="$(lower "$name")"
      if [[ -n "$name" && "$DOMAIN" == *".$name" && ${#name} -gt $len ]]; then best=$id len=${#name}; fi
    done < <(az network dns zone list --subscription "$sub" --query '[].[name, id]' -o tsv --only-show-errors 2>/dev/null || true)
  done
  printf '%s' "$best"
}

# ZSUB ZRG ZONE REL, and ZARGS for az network dns, from DNS_ZONE_ID and DOMAIN.
parse_zone() {
  ZSUB="$(printf '%s' "$DNS_ZONE_ID" | sed -nE 's|^/subscriptions/([^/]+)/.*|\1|p')"
  ZRG="$(printf '%s' "$DNS_ZONE_ID" | sed -nE 's|.*/resource[gG]roups/([^/]+)/.*|\1|p')"
  ZONE="$(lower "${DNS_ZONE_ID##*/}")"
  REL="${DOMAIN%."$ZONE"}"
  [[ -n "$ZSUB" && -n "$ZRG" && -n "$ZONE" && "$REL" != "$DOMAIN" ]] ||
    die "DNS zone $DNS_ZONE_ID doesn't hold $DOMAIN (--dns-zone-id)"
  ZARGS=(--subscription "$ZSUB" -g "$ZRG" -z "$ZONE" --only-show-errors)
}

# IPv4 addresses in the JSON of an A record set, comma-separated.
record_ips() { printf '%s' "$1" | sed -nE 's/.*"ipv4Address": *"([0-9.]+)".*/\1/p' | paste -s -d, - || true; }

# Read the A record for DOMAIN into RECORD_IPS and RECORD_TARGET (an alias's resource),
# and set RECORD_OURS: alias (to this deployment's IP), plain (an A record for
# PUBLIC_IP only, made when the alias couldn't be), stale (the plain record made for
# an earlier deployment's IP, DNS_IP) or empty. Fails without a record.
read_record() {
  local json
  RECORD_IPS="" RECORD_TARGET="" RECORD_OURS=""
  json="$(az network dns record-set a show "${ZARGS[@]}" -n "$REL" -o json 2>/dev/null)" && [[ -n "$json" ]] || return 1
  RECORD_TARGET="$(az network dns record-set a show "${ZARGS[@]}" -n "$REL" --query targetResource.id -o tsv 2>/dev/null || true)"
  RECORD_IPS="$(record_ips "$json")"
  if [[ -n "$RECORD_TARGET" ]]; then
    if [[ "$(lower "$RECORD_TARGET")" == "$(lower "$PIP_ID")" ]]; then RECORD_OURS="alias"; fi
  elif [[ -n "$RECORD_IPS" && "$RECORD_IPS" == "$PUBLIC_IP" ]]; then
    RECORD_OURS="plain"
  elif [[ -n "$RECORD_IPS" && "$DOMAIN" == "$DNS_NAME" && "$RECORD_IPS" == "$DNS_IP" ]]; then
    RECORD_OURS="stale"
  fi
}

# Set DNS_ZONE_ID to the zone for DOMAIN: --dns-zone-id as given (none: DNS by hand),
# else the remembered zone while it still holds DOMAIN, else a fresh search. Only a
# found zone is remembered, so a later run looks again.
dns_zone() {
  [[ -z "$OPT_DNS_ZONE" && "$DNS_ZONE_ID" != none ]] || return 0
  if [[ -n "$DNS_ZONE_ID" && "$DOMAIN" != *".$(lower "${DNS_ZONE_ID##*/}")" ]]; then DNS_ZONE_ID=""; fi
  if [[ -z "$DNS_ZONE_ID" ]]; then
    log "Looking for the Azure DNS zone of $DOMAIN"
    DNS_ZONE_ID="$(find_dns_zone)"
    save_state
  fi
}

# Remember the record, so down removes it even after the group has expired.
remember_record() { DNS_NAME=$DOMAIN DNS_IP=$PUBLIC_IP; save_state; }

dns_by_hand() {
  warn "$1
  Create this record where its DNS is hosted:
    $DOMAIN.  300  IN  A  $PUBLIC_IP
  and delete it after ./azure.sh down: a name left pointing at a released Azure IP can be taken over."
}

# Point DOMAIN at the public IP with an alias record: it follows the IP resource, and
# empties itself when the resource group is deleted, so nothing is left pointing at an
# address Azure hands to someone else. Nothing here stops the run: without a record
# CTFd only lacks its certificate until one is made.
ensure_dns() {
  local err
  dns_zone
  if [[ -z "$DNS_ZONE_ID" || "$DNS_ZONE_ID" == none ]]; then
    dns_by_hand "found no Azure DNS zone for $DOMAIN you can edit."
    return 0
  fi
  parse_zone
  if az network dns record-set cname show "${ZARGS[@]}" -n "$REL" -o none 2>/dev/null; then
    warn "$DOMAIN is a CNAME in $ZONE; left alone. Point it at $PUBLIC_IP yourself."
    return 0
  fi
  if read_record; then
    if [[ $RECORD_OURS == alias ]]; then
      remember_record
      check_caa
      return 0
    fi
    if [[ -z $RECORD_OURS && -n "$RECORD_IPS$RECORD_TARGET" ]]; then # someone else's
      confirm "$DOMAIN points at ${RECORD_IPS:-${RECORD_TARGET##*/}} now. Point it at this deployment ($PUBLIC_IP)?" ||
        { warn "left $DOMAIN alone; CTFd won't get a certificate until it points at $PUBLIC_IP"; return 0; }
      warn "repointing $DOMAIN from ${RECORD_IPS:-${RECORD_TARGET##*/}}"
    fi
  fi
  log "Pointing $DOMAIN at $PUBLIC_IP (alias record in $ZONE)"
  if ! err="$(az network dns record-set a create "${ZARGS[@]}" -n "$REL" --ttl 300 --target-resource "$PIP_ID" -o none 2>&1)"; then
    err="${err%%$'\n'*}"
    if [[ $RECORD_OURS == plain ]]; then
      warn "$DOMAIN stays a plain A record for $PUBLIC_IP; an alias record failed: $err"
    elif az network dns record-set a create "${ZARGS[@]}" -n "$REL" --ttl 300 -o none 2>/dev/null &&
      az network dns record-set a add-record "${ZARGS[@]}" -n "$REL" --ipv4-address "$PUBLIC_IP" -o none 2>/dev/null; then
      warn "made $DOMAIN a plain A record for $PUBLIC_IP; an alias record failed: $err
  A plain record stays when the group is deleted: run ./azure.sh down --env $ENV from here even after it expired."
    else
      dns_by_hand "couldn't write $DOMAIN in $ZONE (--dns-zone-id none skips the zone): $err"
      return 0
    fi
  fi
  remember_record
  check_caa
}

# Caddy's certificate comes from Let's Encrypt; a CAA record naming only others blocks
# it. The CAA record that counts is the closest one at or above the name.
check_caa() {
  local name=$REL caa
  while :; do
    caa="$(az network dns record-set caa show "${ZARGS[@]}" -n "$name" -o json 2>/dev/null || true)"
    if [[ -n "$caa" ]]; then
      if printf '%s' "$caa" | grep -q '"tag": *"issue"' && ! printf '%s' "$caa" | grep -qi 'letsencrypt\.org'; then
        if [[ $name == @ ]]; then name=$ZONE; else name="$name.$ZONE"; fi
        warn "$name has a CAA record without letsencrypt.org, so Caddy gets no certificate for $DOMAIN. Add to it: 0 issue \"letsencrypt.org\""
      fi
      return 0
    fi
    [[ $name != @ ]] || return 0
    if [[ $name == *.* ]]; then name=${name#*.}; else name=@; fi
  done
}

# Delete DOMAIN's record if it points at this deployment (PUBLIC_IP, or PIP_ID).
remove_dns() {
  [[ -n "$DOMAIN" ]] || return 0
  dns_zone
  if [[ -z "$DNS_ZONE_ID" || "$DNS_ZONE_ID" == none ]]; then
    warn "delete the DNS record for $DOMAIN where its DNS is hosted, if you made one"
    return 0
  fi
  parse_zone
  read_record && [[ -n "$RECORD_IPS$RECORD_TARGET" ]] || return 0
  if [[ -n $RECORD_OURS ]]; then
    az network dns record-set a delete "${ZARGS[@]}" -n "$REL" --yes -o none
    log "Removed $DOMAIN from $ZONE"
  else
    warn "left $DOMAIN in $ZONE alone: it doesn't point at this deployment"
  fi
}

# status_dns FUNCTION NAME: run ensure_dns or remove_dns for the status page's name,
# status.NAME (platform/ctfd.status.yml), next to NAME's own record. In a subshell like
# remove_old_dns, so DOMAIN and the record remembered for down stay NAME's, and a
# failure only warns: CTFd works without it, only the status page lacks its name. An
# alias record empties itself with the deployment, so down after an expiry needs no
# memory of it.
status_dns() {
  local rc
  [[ -n "$2" ]] || return 0
  set +e
  ( set -e
    save_state() { :; }
    remember_record() { :; }
    DOMAIN="status.$2"
    "$1" )
  rc=$?
  set -e
  (( rc == 0 )) || warn "the DNS record for status.$2 failed; the status page needs it to point at ${PUBLIC_IP:-the VM}"
}

# After a move to another --domain: delete the old name's record if it still points
# at this deployment (remove_dns leaves anyone else's alone). The old name's zone is
# looked up afresh (ctf.tst.example.com can sit in a tst.example.com zone, not the new
# name's example.com). In a subshell, so DOMAIN stays the new name, the zone remembered
# is the new name's, and a failure only warns. Not as "( ... ) || warn": bash runs
# a subshell there with set -e off, so a failed delete would carry on as if done.
remove_old_dns() {
  local rc
  set +e
  ( set -e
    save_state() { :; }
    DOMAIN=$CUR_DOMAIN OPT_DNS_ZONE=""
    [[ "$DNS_ZONE_ID" == none ]] || DNS_ZONE_ID=""
    remove_dns
    DOMAIN="status.$CUR_DOMAIN"
    remove_dns )
  rc=$?
  set -e
  (( rc == 0 )) || warn "delete $CUR_DOMAIN's DNS record if nothing else uses it"
}

# --- the VM ------------------------------------------------------------------------

write_ssh_config() {
  [[ -n "$PUBLIC_IP" ]] ||
    PUBLIC_IP="$(azs network public-ip show -g "$RG" -n "$PIP" --query ipAddress -o tsv)"
  ensure_ssh_key
  cat > "$SSH_CONFIG" <<EOF
# Written by azure.sh. Also usable directly: ssh -F <this file> $HOST_ALIAS
Host $HOST_ALIAS
  HostName $PUBLIC_IP
  User $ADMIN_USER
  IdentityFile "$KEY"
  IdentitiesOnly yes
  UserKnownHostsFile "$KNOWN_HOSTS"
  StrictHostKeyChecking accept-new
  ServerAliveInterval 30
  ConnectTimeout 10
EOF
}

vm() { ssh -F "$SSH_CONFIG" "$HOST_ALIAS" "$@"; }

# Try $1 times. 0: logged in, 2: reachable but the key is refused (3 times in a row,
# or on the last try), 1: unreachable.
wait_for_ssh() {
  local out denied=0 i
  for (( i = 1; ; i++ )); do
    if out="$(ssh -F "$SSH_CONFIG" -o BatchMode=yes -o ConnectTimeout=8 "$HOST_ALIAS" true 2>&1)"; then return 0; fi
    if [[ "$out" == *"Permission denied"* ]]; then denied=$((denied + 1)); else denied=0; fi
    (( denied < 3 )) || return 2
    (( i < $1 )) || break
    sleep 5
  done
  (( denied == 0 )) || return 2
  return 1
}

# Every command that uses SSH comes through here first. $1: tries (default 6).
connect_ssh() {
  local rc=0 tries=${1:-6}
  if [[ $BOOTING == 1 ]]; then tries=30; fi # a new or just-started VM takes a minute or two
  wait_for_ssh "$tries" || rc=$?
  if [[ $rc == 2 ]]; then
    # Deployed from another machine: add this machine's key through the VM agent.
    log "Adding this machine's SSH key to $VM" >&2
    azs vm user update -g "$RG" -n "$VM" -u "$ADMIN_USER" --ssh-key-value "$(cat "$KEY.pub")" -o none
    rc=0
    wait_for_ssh 24 || rc=$?
  fi
  case $rc in
    0) ;;
    2) die "$VM refuses the SSH key ${KEY#"$REPO"/}" ;;
    *) die "no SSH on $PUBLIC_IP. Is this machine's IP allowed? ./azure.sh allow-me --env $ENV" ;;
  esac
}

bootstrap_vm() {
  log "Preparing the VM (Docker, firewall for the challenge networks, database dumps)"
  vm "sudo bash -s -- $ADMIN_USER ${OPT_EGRESS:-keep} $REMOTE_DIR" < "$BOOTSTRAP"
}

# Copy the working tree, not a git ref, so a local fix can be tried before it's
# committed. The VM's own state (.ctf/, .env, local backups) is left in place. Of
# ctfd-backup/, only the export ctf.sh imports goes: the others hold past events'
# participants, and a VM that hands out shells has no use for them.
sync_repo() {
  local newest backups=()
  if [[ -n "$(git -C "$REPO" status --porcelain 2>/dev/null | head -n1)" ]]; then
    warn "deploying uncommitted changes from this checkout"
  fi
  # The backup ./ctf.sh up imports (newest_backup, shared in tools/challenge.sh), by name.
  newest="$(newest_backup)"
  newest="${newest##*/}"
  # A literal name for rsync's pattern matching.
  if [[ -n "$newest" ]]; then backups+=(--include="/ctfd-backup/$(printf '%s' "$newest" | sed 's/[][*?]/\\&/g')"); fi
  log "Copying the checkout to the VM"
  # .claude/ holds this tool's git-ignored worktrees (each a full checkout with its
  # own .ctf/ secrets and past-event backups). It must never reach a VM that hands
  # out shells, so exclude it wholesale; .ctf/, .env and the backups are excluded
  # at the root and nested copies live under .claude/, now covered too.
  rsync -az --delete \
    --exclude=/.git/ --exclude=/.claude/ --exclude=/.ctf/ --exclude=/.env --exclude='/ctfd-backup/local.*' \
    --exclude=/ctfd-backup/db/ \
    ${backups[@]+"${backups[@]}"} --exclude='/ctfd-backup/*.zip' \
    --exclude=__pycache__/ --exclude=.DS_Store --exclude=.idea/ --exclude=.venv/ \
    --exclude=node_modules/ --exclude='/challenges/*/git-ai/challenge/build/' \
    -e "ssh -F '$SSH_CONFIG'" "$REPO/" "$HOST_ALIAS:$REMOTE_DIR/"
  # Excluded files are kept on the VM (the database dumps in ctfd-backup/db/ among them);
  # remove the older exports an earlier sync copied.
  vm "cd $REMOTE_DIR/ctfd-backup 2>/dev/null || exit 0; for f in *.zip; do
    case \$f in local.* | $(printf '%q' "${newest:-/}")) ;; *) rm -f -- \"\$f\" ;; esac; done"
}

remote_ctf_up() {
  local args=(up --domain "$DOMAIN") probe=0
  REGCODE_NEW=0
  if [[ $HAS_REGCODE == 1 ]]; then REGCODE=$OPT_REGCODE; fi
  # Does the VM already run a configured CTF? ctf.sh writes .ctf/configured once an
  # up has finished configuring CTFd, and .ctf/import-pending while an import is
  # imported but not yet configured, so a first run that died after its import is
  # retried as new (--fresh and a registration code) from any checkout. A VM set up
  # by a ctf.sh that didn't write .ctf/configured has only .ctf/admin-password: that
  # counts as configured unless an import is pending, so a running event never gets
  # a new registration code.
  # ssh exits 255 when it can't connect: that is not "no CTF yet", which would put
  # a new registration code on a running CTF.
  vm "cd $REMOTE_DIR/.ctf 2>/dev/null && { test -f configured || { test -s admin-password && test ! -e import-pending; }; }" || probe=$?
  (( probe != 255 )) || die "could not reach the VM over SSH to check for an existing CTF; nothing was changed, try again"
  if [[ "$REGCODE_PENDING" == 1 ]] || (( probe != 0 )); then
    # A new CTF: ctf.sh imports the export (or sets CTFd up from the repo without one),
    # and only then sets the registration code and removes an export's players (--fresh). Both are passed until that run has
    # succeeded (REGCODE_PENDING), with the code chosen by the first attempt. A new CTF
    # gets a code, so nobody signs up while it's being tested.
    if [[ $HAS_REGCODE != 1 && "$REGCODE_PENDING" != 1 ]]; then REGCODE="ctf-$(random_hex 4)"; fi
    REGCODE_PENDING=1 REGCODE_NEW=1
    args+=(--fresh --registration-code "$REGCODE")
  elif [[ $HAS_REGCODE == 1 ]]; then
    args+=(--registration-code "$REGCODE")
  fi
  # ctf.sh keeps these on the VM, so later runs without them don't change them.
  if [[ $HAS_PREVIEW == 1 ]]; then args+=(--preview "$OPT_PREVIEW"); fi
  if [[ -n "$OPT_LANG" ]]; then args+=(--lang "$OPT_LANG"); fi
  if [[ $HAS_ESTART == 1 ]]; then args+=(--event-start "$OPT_ESTART"); fi
  if [[ $HAS_EEND == 1 ]]; then args+=(--event-end "$OPT_EEND"); fi
  if [[ $HAS_EFREEZE == 1 ]]; then args+=(--event-freeze "$OPT_EFREEZE"); fi
  if [[ $HAS_TSIZE == 1 ]]; then args+=(--team-size "$OPT_TSIZE"); fi
  if [[ -n "$OPT_STATUS" ]]; then args+=(--status "$OPT_STATUS"); fi
  if [[ $HAS_SSO == 1 ]]; then args+=(--sso-tenant "$TENANT" --sso-client-id "$OPT_SSO_CLIENT"); fi
  save_state
  log "Running ./ctf.sh ${args[*]} on the VM (the first build takes several minutes)"
  # ADMIN_PASSWORD and the sign-in's client secret travel on stdin, not on a command line.
  printf '%s\n%s\n' "${ADMIN_PASSWORD:-}" "${SSO_SECRET:-}" | vm "cd $REMOTE_DIR || exit 1;
    IFS= read -r pw; if [ -n \"\$pw\" ]; then export ADMIN_PASSWORD=\"\$pw\"; fi; unset pw;
    IFS= read -r sso; if [ -n \"\$sso\" ]; then export SSO_CLIENT_SECRET=\"\$sso\"; fi; unset sso;
    exec ./ctf.sh $(printf '%q ' "${args[@]}") </dev/null"
  if [[ "$REGCODE_PENDING" == 1 ]]; then REGCODE_PENDING=0; save_state; fi
}

# The client secret for --sso-client-id: SSO_CLIENT_SECRET, else asked for (not shown).
# Empty keeps the secret the VM has.
ask_sso_secret() {
  SSO_SECRET="${SSO_CLIENT_SECRET:-}"
  [[ -z "$SSO_SECRET" ]] || return 0
  [[ -t 0 ]] || die "set SSO_CLIENT_SECRET to the client secret of app registration $OPT_SSO_CLIENT"
  read -r -s -p "Client secret of app registration $OPT_SSO_CLIENT (Enter keeps the VM's, if it has this app's): " SSO_SECRET
  echo >&2
}

do_backup() {
  local out file
  log "Exporting CTFd on the VM"
  out="$(vm "cd $REMOTE_DIR && ./ctf.sh backup")" || die "the export failed: $out"
  file="$(printf '%s\n' "$out" | sed -n 's/^wrote //p' | tail -n1)"
  [[ -n "$file" ]] || die "ctf.sh backup didn't report a file: $out"
  mkdir -p "$REPO/ctfd-backup"
  scp -q -F "$SSH_CONFIG" "$HOST_ALIAS:$REMOTE_DIR/$file" "$REPO/ctfd-backup/"
  log "Saved $file (git-ignored: it holds the participants)"
}

# Load the deployment for commands that need a running VM.
require_vm() {
  load_rg || die "no deployment $RG in subscription $SUB_NAME (./azure.sh up --env $ENV)"
  load_vm || die "$RG has no VM $VM (./azure.sh up --env $ENV)"
  DOMAIN="$CUR_DOMAIN"
  need_domain
}

require_running() {
  require_vm
  [[ "$POWER" == "VM running" ]] || die "$VM is ${POWER#VM } (./azure.sh start --env $ENV)"
  write_ssh_config
  connect_ssh 3
}

# --- commands ------------------------------------------------------------------------

cmd_up() {
  need az ssh ssh-keygen rsync curl
  select_subscription
  set_names
  local ip=""
  CUR_SIZE="" CUR_KEY="" CUR_ADMIN="" CUR_PLAYERS="" CUR_OPEN="" CUR_SHUTDOWN_ON="" CUR_SHUTDOWN_PREF="" CUR_SHUTDOWN="" CUR_NOTIFY="" CUR_START=""
  if load_rg; then
    load_vm || true
    load_config
  else
    confirm "Create $RG in subscription '$SUB_NAME' ($SUB) as $AZ_USER?" || die "aborted"
    # A group that expired on its own leaves its notes behind; they're not this one's.
    REGCODE="" REGCODE_PENDING=0
  fi
  resolve_settings
  if [[ -n "$CUR_DOMAIN" && "$DOMAIN" != "$CUR_DOMAIN" ]]; then
    log "Moving from $CUR_DOMAIN to $DOMAIN"
  fi
  if ip="$(my_ip)"; then
    ADMIN_CIDRS="$(cidr_list "$ADMIN_CIDRS,$ip")"
  else
    [[ -n "$ADMIN_CIDRS" ]] || die "couldn't find this machine's public IP; pass --admin-ip"
    warn "couldn't find this machine's public IP; SSH is allowed from $ADMIN_CIDRS only"
  fi
  ensure_ssh_key
  # Azure fixes an existing VM's key; another machine's key is added over SSH instead.
  VM_KEY="${CUR_KEY:-$(awk '{ print $1 " " $2 }' "$KEY.pub")}"
  save_state

  ensure_resource_group
  deploy_infra
  arm_jobs
  ensure_dns
  status_dns ensure_dns "$DOMAIN"
  if [[ -n "$CUR_DOMAIN" && "$DOMAIN" != "$CUR_DOMAIN" ]]; then remove_old_dns; fi
  if [[ -z "$CUR_SIZE" ]]; then # a new VM: new host keys, and it's still booting
    rm -f "$KNOWN_HOSTS"
    BOOTING=1
  fi
  write_ssh_config
  ensure_running
  connect_ssh
  bootstrap_vm
  sync_repo
  remote_ctf_up

  local pw mode stop start expiry
  pw="$(vm "cat $REMOTE_DIR/.ctf/admin-password" 2>/dev/null || echo '?')"
  if [[ $OPEN == 1 ]]; then
    mode="OPEN to the internet (./azure.sh close --env $ENV after the event)"
  else
    mode="only from ${ADMIN_CIDRS}${PLAYER_CIDRS:+,$PLAYER_CIDRS} (./azure.sh open --env $ENV for the event)"
  fi
  if [[ $SHUTDOWN_ON == true && $OPEN != 1 ]]; then
    stop="every night at $(hhmm "$SHUTDOWN_TIME") Oslo time (./azure.sh start --env $ENV wakes it)"
  else
    stop="no nightly shutdown"
  fi
  start="no morning start"
  if [[ $START_ON == true ]]; then
    start="Monday to Friday at $(hhmm "$START_TIME") Oslo time"
    [[ $START_ARMED == 1 ]] || start+=", NOT yet: see the warning above"
  fi
  expiry="deleted automatically the night after"
  [[ $EXPIRY_ARMED == 1 ]] || expiry="NOT deleted automatically, see the warning above"
  echo
  log "Ready"
  cat <<EOF
  CTFd:          https://$DOMAIN  (admin / $pw)
  Challenges:    $mode
  VM stops:      $stop
  VM starts:     $start
  Expires:       $EXPIRES, $expiry
EOF
  if [[ "$OPT_STATUS" != off ]]; then echo "  Status page:   https://status.$DOMAIN"; fi
  show_regcode
  echo "  Shell:         ./azure.sh ssh --env $ENV"
}

# The registration code a new CTF got on this run.
show_regcode() {
  [[ $REGCODE_NEW == 1 ]] || return 0
  if [[ -n "$REGCODE" ]]; then
    echo "  Registration:  code $REGCODE (change it with ./azure.sh deploy --registration-code ...)"
  else
    echo "  Registration:  open to anyone"
  fi
}

cmd_deploy() {
  need az ssh rsync
  select_subscription
  set_names
  require_vm
  ensure_running
  write_ssh_config
  connect_ssh
  bootstrap_vm
  sync_repo
  remote_ctf_up
  log "Deployed to https://$DOMAIN"
  show_regcode
}

# Reload everything and redeploy the template after the caller changed a setting.
load_all() {
  load_rg || die "no deployment $RG in subscription $SUB_NAME (./azure.sh up --env $ENV)"
  load_vm || die "$RG has no VM $VM (./azure.sh up --env $ENV)"
  load_config
  [[ -n "$CUR_ADMIN" ]] || die "$RG is incomplete; run ./azure.sh up --env $ENV"
  resolve_settings
  VM_KEY=$CUR_KEY
  # Only up writes the group's tags; the expiry is the one that matters here.
  if [[ -n "$OPT_EXPIRES" && "$EXPIRES" != "$CUR_EXPIRES" ]]; then set_expiry "$EXPIRES"; fi
}

cmd_open() {
  need az
  select_subscription
  set_names
  load_all
  local n
  n="$(days_until "$EXPIRES")"
  if (( n < 1 )); then
    warn "$RG expires $EXPIRES and is deleted in the night after; ./azure.sh extend --env $ENV first if the event runs past that"
  fi
  confirm "Open $RG's challenges (shells, exploitable services) to the whole internet?" || die "aborted"
  OPEN=1 # main.bicep also turns the nightly shutdown off while open
  deploy_infra
  ensure_running
  log "Challenges are open, and the VM no longer stops at night. ./azure.sh close --env $ENV afterwards."
}

cmd_close() {
  need az
  select_subscription
  set_names
  load_all
  OPEN=0
  deploy_infra
  if [[ $SHUTDOWN_ON == true ]]; then
    log "Challenges only from $ADMIN_CIDRS; the VM stops every night at $(hhmm "$SHUTDOWN_TIME") Oslo time"
  else
    log "Challenges only from $ADMIN_CIDRS"
  fi
}

cmd_allow_me() {
  need az curl
  select_subscription
  set_names
  load_all
  local ip
  ip="$(my_ip)" || die "couldn't find this machine's public IP"
  case ",$ADMIN_CIDRS," in *",$ip/32,"*) log "$ip is allowed already"; return 0 ;; esac
  ADMIN_CIDRS="$(cidr_list "$ADMIN_CIDRS,$ip")"
  deploy_infra
  log "Allowed $ip"
}

cmd_status() {
  need az
  select_subscription
  set_names
  if ! load_rg; then
    echo "No deployment $RG in subscription $SUB_NAME."
    return 0
  fi
  load_vm || true
  load_config
  local expires=$CUR_EXPIRES chal stop start n armed=0
  if job_armed "$EXPIRY_ID"; then armed=1; fi
  if [[ -z "$CUR_EXPIRES" ]]; then
    # The expiry job skips a group without the tag.
    expires="none, so NOT deleted automatically (./azure.sh extend --env $ENV sets a date)"
  else
    if valid_date "$CUR_EXPIRES"; then
      n="$(days_until "$CUR_EXPIRES")"
      if (( n >= 0 )); then expires="$CUR_EXPIRES, in $n days"; else expires="$CUR_EXPIRES, passed"; fi
    fi
    if [[ $armed == 1 ]]; then expires+=", then deleted automatically"; else expires+=", NOT deleted automatically"; fi
  fi
  if [[ $CUR_OPEN == 1 ]]; then chal="OPEN to the internet"; else chal="only from ${CUR_ADMIN:-nobody}"; fi
  if [[ $CUR_OPEN != 1 && -n "$CUR_PLAYERS" ]]; then chal+=", and players from $CUR_PLAYERS"; fi
  if [[ "$CUR_SHUTDOWN_ON" == Enabled ]]; then
    stop="every night at $(hhmm "$CUR_SHUTDOWN") Oslo time"
  elif [[ $CUR_OPEN == 1 && -n "$CUR_SHUTDOWN" && "$CUR_SHUTDOWN_PREF" != off ]]; then
    stop="off while open; every night at $(hhmm "$CUR_SHUTDOWN") Oslo time after close"
  else
    stop="off"
  fi
  start="off"
  if valid_hhmm "$CUR_START"; then
    start="Monday to Friday at $(hhmm "$CUR_START") Oslo time"
    job_armed "$START_ID" "$VM_ID" || start+=", NOT working until an Owner grants the role (./azure.sh up prints it)"
  fi
  # allow-me and up only add this machine's IP; the admin list never shrinks on its
  # own. Surface its size so stale addresses (old cafes, hotels, CGNAT) are visible;
  # prune by re-running with --admin-ip listing only the ones to keep.
  local admin="${CUR_ADMIN:-nobody}" n_admin=0
  if [[ -n "$CUR_ADMIN" ]]; then
    n_admin=$(( $(printf '%s' "$CUR_ADMIN" | tr -cd ',' | wc -c) + 1 ))
    (( n_admin <= 1 )) || admin+=" ($n_admin addresses; prune with ./azure.sh up --env $ENV --admin-ip <keep,...>)"
  fi
  cat <<EOF
$RG in $SUB_NAME ($CUR_LOCATION)
  CTFd:        https://${CUR_DOMAIN:-?}
  Expires:     $expires
  VM:          $VM, ${CUR_SIZE:-missing}, ${POWER#VM }, ${PUBLIC_IP:-no IP}
  Challenges:  $chal
  SSH from:    $admin
  Shutdown:    $stop
  Start:       $start
EOF
  if [[ "$POWER" == "VM running" ]]; then
    write_ssh_config
    echo
    # A subshell, so status still ends normally when connect_ssh dies (it says why).
    if (connect_ssh 1); then
      ssh -F "$SSH_CONFIG" -o BatchMode=yes "$HOST_ALIAS" "cd $REMOTE_DIR && ./ctf.sh status" ||
        warn "./ctf.sh status failed on the VM"
    fi
  fi
}

cmd_extend() {
  need az
  local d=${ARGS[0]:-}
  [[ -n "$d" ]] || die "usage: ./azure.sh extend YYYY-MM-DD|+DAYS [--env $ENV]"
  if [[ "$d" =~ ^\+[0-9]{1,4}$ ]]; then d="$(plus_days "$((10#${d#+}))")"; fi
  check_expiry "$d"
  select_subscription
  set_names
  load_rg || die "no deployment $RG in subscription $SUB_NAME"
  set_expiry "$d"
}

cmd_start() {
  need az
  select_subscription
  set_names
  require_vm
  log "Starting $VM"
  azs vm start -g "$RG" -n "$VM" -o none
  log "Started; CTFd and the challenges are back within a minute at https://$DOMAIN"
}

cmd_stop() {
  need az
  select_subscription
  set_names
  require_vm
  log "Stopping (deallocating) $VM"
  azs vm deallocate -g "$RG" -n "$VM" -o none
  log "Stopped. ./azure.sh start --env $ENV brings the CTF back as it was."
}

cmd_ssh() {
  need az ssh
  select_subscription
  set_names
  require_running
  local tty=()
  if [[ ${#ARGS[@]} -eq 0 ]] || [[ -t 0 && -t 1 ]]; then tty=(-t); fi
  exec ssh -F "$SSH_CONFIG" ${tty[@]+"${tty[@]}"} "$HOST_ALIAS" ${ARGS[@]+"${ARGS[@]}"}
}

cmd_backup() {
  need az ssh scp
  select_subscription
  set_names
  require_running
  do_backup
}

# restore [FILE]: ./ctf.sh restore-db on the VM, which lists the dumps the timer made
# and asks which one, dumps the database as it is, and loads the chosen one. It asks
# here, through ssh -t, so nothing about the dumps (players' emails and password
# hashes) leaves the VM.
cmd_restore() {
  need az ssh
  [[ ${#ARGS[@]} -le 1 ]] || die "restore takes one dump (see ./azure.sh --help)"
  local remote="cd $REMOTE_DIR && ./ctf.sh restore-db" tty=()
  if [[ ${#ARGS[@]} -eq 1 ]]; then
    remote+=" $(printf '%q' "${ARGS[0]}")"
  elif [[ ! -t 0 || ! -t 1 ]]; then
    die "restore asks which dump in a terminal; without one, name it: ./azure.sh restore FILE --yes"
  fi
  if [[ $YES == 1 ]]; then
    remote+=" --yes"
  elif [[ ! -t 0 || ! -t 1 ]]; then
    die "rerun with --yes to replace CTFd's database with ${ARGS[0]}"
  fi
  select_subscription
  set_names
  require_running
  if [[ -t 0 && -t 1 ]]; then tty=(-t); fi
  log "CTFd's database on $VM ($DOMAIN)"
  exec ssh -F "$SSH_CONFIG" ${tty[@]+"${tty[@]}"} "$HOST_ALIAS" "$remote"
}

cmd_down() {
  need az
  select_subscription
  set_names
  if ! load_rg; then
    log "No deployment $RG in subscription $SUB_NAME"
    # It expired on its own: an alias record is empty now, but a plain A record still
    # points at the released IP.
    if [[ -n "$DNS_NAME" ]]; then
      DOMAIN=$DNS_NAME PUBLIC_IP=$DNS_IP
      remove_dns
      status_dns remove_dns "$DNS_NAME"
    fi
    forget_local
    return 0
  fi
  DOMAIN=${CUR_DOMAIN:-$DNS_NAME}
  load_vm || true
  if [[ -z "$PUBLIC_IP" && "$DOMAIN" == "$DNS_NAME" ]]; then PUBLIC_IP=$DNS_IP; fi
  if [[ $OPT_BACKUP == 1 ]]; then
    [[ "$POWER" == "VM running" ]] || die "$VM is ${POWER#VM }; start it for the backup (./azure.sh start --env $ENV)"
    need ssh scp
    write_ssh_config
    connect_ssh 3
    do_backup
  fi
  if [[ $YES != 1 ]]; then
    [[ -t 0 ]] || die "rerun with --yes to delete $RG"
    local answer
    read -r -p "Delete $RG and everything in it, CTFd's data too? Type $RG to confirm: " answer
    [[ "$answer" == "$RG" ]] || die "aborted"
  fi
  remove_dns
  status_dns remove_dns "$DOMAIN"
  log "Deleting $RG (a few minutes)"
  azs group delete -n "$RG" --yes -o none
  forget_local
  log "Deleted $RG"
}

# --- main --------------------------------------------------------------------------

cmd=${1:-}
[[ $# -gt 0 ]] && shift
ENV=tst YES=0 HAS_REGCODE=0 OPT_BACKUP=0 BOOTING=0 HAS_PLAYERS=0 HAS_PREVIEW=0 HAS_SSO=0
OPT_SUBSCRIPTION="" OPT_DOMAIN="" OPT_EXPIRES="" OPT_ADMIN="" OPT_SIZE="" OPT_LOCATION=""
OPT_SHUTDOWN="" OPT_START="" OPT_NOTIFY="" OPT_REGCODE="" OPT_EGRESS="" OPT_DNS_ZONE=""
OPT_PLAYERS="" OPT_PREVIEW="" OPT_SSO_CLIENT="" SSO_SECRET="" OPT_LANG=""
OPT_ESTART="" OPT_EEND="" OPT_EFREEZE="" OPT_TSIZE="" OPT_STATUS=""
HAS_ESTART=0 HAS_EEND=0 HAS_EFREEZE=0 HAS_TSIZE=0
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env | --subscription | --domain | --days | --expires | --admin-ip | --size | --location | \
      --shutdown | --start | --notify | --registration-code | --egress | --dns-zone-id | --player-ip | \
      --preview | --sso-client-id | --lang | --event-start | --event-end | --event-freeze | \
      --team-size | --status)
      [[ $# -ge 2 ]] || die "$1 needs a value" ;;
  esac
  case "$1" in
    --env) ENV=$2; shift 2 ;;
    --subscription) OPT_SUBSCRIPTION=$2; shift 2 ;;
    --domain) OPT_DOMAIN=$2; shift 2 ;;
    --days)
      [[ "$2" =~ ^[0-9]{1,4}$ ]] || die "--days takes a number"
      OPT_EXPIRES="$(plus_days "$((10#$2))")"; shift 2 ;;
    --expires) OPT_EXPIRES=$2; shift 2 ;;
    --admin-ip) OPT_ADMIN="$(cidr_list "$2")"; shift 2 ;;
    --size) OPT_SIZE=$2; shift 2 ;;
    --location) OPT_LOCATION=$2; shift 2 ;;
    --shutdown) OPT_SHUTDOWN=$2; shift 2 ;;
    --start) OPT_START=$2; shift 2 ;;
    --notify) OPT_NOTIFY=$2; shift 2 ;;
    --registration-code) OPT_REGCODE=$2; HAS_REGCODE=1; shift 2 ;;
    --egress)
      [[ "$2" == block || "$2" == allow ]] || die "--egress takes block or allow"
      OPT_EGRESS=$2; shift 2 ;;
    --dns-zone-id) OPT_DNS_ZONE=$2; shift 2 ;;
    --player-ip)
      [[ "$2" == none ]] || cidr_list "$2" >/dev/null
      OPT_PLAYERS=$2; HAS_PLAYERS=1; shift 2 ;;
    --preview) OPT_PREVIEW=$2; HAS_PREVIEW=1; shift 2 ;;
    --sso-client-id) OPT_SSO_CLIENT=$2; HAS_SSO=1; shift 2 ;;
    --lang)
      [[ "$2" == no || "$2" == en ]] || die "--lang takes no (Norwegian) or en (English)"
      OPT_LANG=$2; shift 2 ;;
    --event-start) OPT_ESTART=$2; HAS_ESTART=1; shift 2 ;;
    --event-end) OPT_EEND=$2; HAS_EEND=1; shift 2 ;;
    --event-freeze) OPT_EFREEZE=$2; HAS_EFREEZE=1; shift 2 ;;
    --team-size)
      [[ -z "$2" || "$2" =~ ^[1-9][0-9]*$ ]] || die "--team-size takes a number of players, or \"\" to clear it"
      OPT_TSIZE=$2; HAS_TSIZE=1; shift 2 ;;
    --status)
      [[ "$2" == on || "$2" == off ]] || die "--status takes on or off"
      OPT_STATUS=$2; shift 2 ;;
    --backup) OPT_BACKUP=1; shift ;;
    --yes | -y) YES=1; shift ;;
    -h | --help) usage; exit 0 ;;
    --) shift; ARGS+=("$@"); break ;;
    -*) [[ "$cmd" == ssh ]] || die "unknown option: $1 (see ./azure.sh --help)"
      ARGS+=("$@"); break ;;
    *) [[ "$cmd" == ssh ]] && { ARGS+=("$@"); break; }
      ARGS+=("$1"); shift ;;
  esac
done
[[ "$ENV" == tst || "$ENV" == prd ]] || die "--env is tst or prd"
case "$cmd" in extend | ssh | restore) ;; *) [[ ${#ARGS[@]} -eq 0 ]] || die "unexpected argument: ${ARGS[0]}" ;; esac
# Checked here, before anything in Azure changes, with the same functions
# (tools/challenge.sh) ctf.sh on the VM checks them with again.
. "$REPO/tools/challenge.sh"
if [[ $HAS_PREVIEW == 1 ]]; then OPT_PREVIEW="$(preview_list "$OPT_PREVIEW")" || exit 1; fi
if [[ $HAS_ESTART == 1 ]]; then check_event_time --event-start "$OPT_ESTART"; fi
if [[ $HAS_EEND == 1 ]]; then check_event_time --event-end "$OPT_EEND"; fi
if [[ $HAS_EFREEZE == 1 ]]; then check_event_time --event-freeze "$OPT_EFREEZE"; fi
if [[ $HAS_SSO == 1 && -n "$OPT_SSO_CLIENT" ]]; then
  is_guid "$OPT_SSO_CLIENT" || die "--sso-client-id takes the app registration's client id (a GUID)"
  case "$cmd" in up | deploy) ask_sso_secret ;; esac
fi

load_state
[[ -z "$OPT_DNS_ZONE" ]] || DNS_ZONE_ID=$OPT_DNS_ZONE

case "$cmd" in
  up) cmd_up ;;
  deploy) cmd_deploy ;;
  open) cmd_open ;;
  close) cmd_close ;;
  allow-me) cmd_allow_me ;;
  status) cmd_status ;;
  extend) cmd_extend ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  ssh) cmd_ssh ;;
  backup) cmd_backup ;;
  restore) cmd_restore ;;
  down) cmd_down ;;
  -h | --help | help | "") usage ;;
  *) die "unknown command: $cmd (see ./azure.sh --help)" ;;
esac
