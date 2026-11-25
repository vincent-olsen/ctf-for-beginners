#!/usr/bin/env bash
# Prepares the Azure VM for ./ctf.sh: Docker, container log rotation, firewall rules for
# the challenge networks (docs/hosting.md steps 1 and 3, automated), the database dumps
# during the event, and security updates that leave Docker running. azure.sh runs it as
# root over SSH on every 'up' and 'deploy'; running it again changes nothing.
#
#   bootstrap.sh <admin user> <egress: block|allow|keep> [checkout folder in the admin's home]
set -euo pipefail

admin_user=${1:?usage: bootstrap.sh <admin user> <block|allow|keep> [checkout folder]}
egress=${2:-keep}
checkout=${3:-ctf-for-n00bs}
export DEBIAN_FRONTEND=noninteractive

# On first boot cloud-init and unattended-upgrades may still hold apt's lock: wait for
# it instead of failing.
cloud-init status --wait >/dev/null 2>&1 || true
echo 'DPkg::Lock::Timeout "600";' > /etc/apt/apt.conf.d/90ctf-lock-timeout

# Security updates keep installing on their own, but nothing they bring may restart
# Docker in the middle of an event: that restarts CTFd and every challenge, and drops
# every player's shell. needrestart (which unattended-upgrades runs) leaves dockerd and
# containerd alone, so they pick up a new library at the next deploy or reboot, and
# the VM never reboots by itself. Docker's own packages come from download.docker.com,
# which unattended-upgrades doesn't take updates from.
mkdir -p /etc/needrestart/conf.d
cat > /etc/needrestart/conf.d/90-ctf.conf <<'EOF'
# Installed by platform/azure/bootstrap.sh: never restart Docker for a library update.
$nrconf{override_rc}{qr(^docker)} = 0;
$nrconf{override_rc}{qr(^containerd)} = 0;
EOF
echo 'Unattended-Upgrade::Automatic-Reboot "false";' > /etc/apt/apt.conf.d/52ctf-no-reboot

if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  echo "Installing Docker"
  curl -fsSL https://get.docker.com | sh
fi
for tool in git rsync; do
  if ! command -v "$tool" >/dev/null; then
    apt-get update -qq && apt-get install -y -qq "$tool"
  fi
done
usermod -aG docker "$admin_user"

# Rotate container logs, so weeks of port scans can't fill the disk. Only containers
# created afterwards pick this up, which on a new VM is all of them.
daemon_json='{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" } }'
if [[ "$(cat /etc/docker/daemon.json 2>/dev/null)" != "$daemon_json" ]]; then
  printf '%s\n' "$daemon_json" > /etc/docker/daemon.json
  systemctl restart docker
fi

# Firewall for the challenge bridges (every ctf-* bridge name in compose.yml),
# re-applied whenever Docker starts, so it survives reboots and the nightly shutdown.
cat > /usr/local/sbin/ctf-firewall <<'EOF'
#!/bin/sh
# Keep a player's shell (meow*, or a popped pwn binary) inside its container network:
# no Azure instance metadata or VM agent endpoints, no services on this VM, and no new
# connections out of the bridge (the internet) unless ALLOW_EGRESS=1. Answering players
# is unaffected: those connections come in, and only new outgoing ones are refused.
# Installed by platform/azure/bootstrap.sh; settings in /etc/default/ctf-firewall.
set -eu
ALLOW_EGRESS=${ALLOW_EGRESS:-0}

add() { # add CHAIN RULE...: insert the rule unless it is there
  chain=$1; shift
  iptables -C "$chain" "$@" 2>/dev/null || iptables -I "$chain" "$@"
}
del() { # del CHAIN RULE...: remove every copy of the rule
  chain=$1; shift
  while iptables -D "$chain" "$@" 2>/dev/null; do :; done
}

# DOCKER-USER may not exist yet: this service is ordered before docker.service so the
# rules are in place before dockerd restarts the challenge containers (otherwise, for
# a few seconds after every reboot/morning start, a shell would face an empty chain).
# dockerd reuses an existing chain and adds its own FORWARD jump to it.
iptables -N DOCKER-USER 2>/dev/null || true

# ctf-+ matches every bridge whose name starts with ctf-, so a new network in
# compose.yml is covered once its bridge is named that way. The wire server also
# answers DNS, which Docker's resolver forwards from inside the containers, so only
# the VM agent's ports are closed there. Traffic within a bridge (noter5 to its
# backend) is not egress; Docker itself drops traffic between two bridges.
add DOCKER-USER -i ctf-+ -d 169.254.169.254 -j DROP
add DOCKER-USER -i ctf-+ -d 168.63.129.16 -p tcp -m multiport --dports 80,32526 -j DROP
add INPUT -i ctf-+ -m conntrack --ctstate NEW -j DROP
if [ "$ALLOW_EGRESS" = 1 ]; then
  del DOCKER-USER -i ctf-+ ! -o ctf-+ -m conntrack --ctstate NEW -j REJECT
else
  add DOCKER-USER -i ctf-+ ! -o ctf-+ -m conntrack --ctstate NEW -j REJECT
fi
EOF
chmod 0755 /usr/local/sbin/ctf-firewall

conf=/etc/default/ctf-firewall
case "$egress" in
  allow) echo 'ALLOW_EGRESS=1' > "$conf" ;;
  block) echo 'ALLOW_EGRESS=0' > "$conf" ;;
  keep) [[ -f "$conf" ]] || echo 'ALLOW_EGRESS=0' > "$conf" ;;
  *) echo "egress must be block, allow or keep, not '$egress'" >&2; exit 2 ;;
esac

cat > /etc/systemd/system/ctf-firewall.service <<'EOF'
[Unit]
Description=Firewall rules for the CTF challenge networks
# Before docker.service so the rules exist before dockerd restarts the challenge
# containers; PartOf so a docker restart re-applies them. Wants (not Requires) keeps
# this soft, and WantedBy both targets so it runs at boot and whenever docker starts.
Wants=docker.service
Before=docker.service
PartOf=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
EnvironmentFile=-/etc/default/ctf-firewall
ExecStart=/usr/local/sbin/ctf-firewall

[Install]
WantedBy=docker.service multi-user.target
EOF
systemctl daemon-reload
systemctl enable --quiet ctf-firewall.service
systemctl restart ctf-firewall.service

# A dump of CTFd's database every 10 minutes while the event is on: ./ctf.sh backup --db
# --if-event does nothing outside CTFd's start and end time (with 30 minutes on either
# side), nor before the first up. The dumps stay in ctfd-backup/db/ on the VM for 7
# days (azure.sh's rsync leaves them alone); ./ctf.sh restore-db puts one back.
admin_home=$(getent passwd "$admin_user" | cut -d: -f6)
cat > /etc/systemd/system/ctf-backup.service <<EOF
[Unit]
Description=Dump CTFd's database while the event is on (ctf.sh backup --db --if-event)
Wants=docker.service
After=docker.service

[Service]
Type=oneshot
User=$admin_user
WorkingDirectory=$admin_home/$checkout
ExecStart=$admin_home/$checkout/ctf.sh backup --db --if-event
EOF
cat > /etc/systemd/system/ctf-backup.timer <<'EOF'
[Unit]
Description=Every 10 minutes, dump CTFd's database if the event is on

[Timer]
OnCalendar=*-*-* *:00/10:00

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --quiet ctf-backup.timer
# restart, not just --now: a timer already running keeps its old schedule otherwise.
systemctl restart ctf-backup.timer
