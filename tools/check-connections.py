#!/usr/bin/env python3
"""Check platform/connections.txt against compose.yml.

Every non-comment line of platform/connections.txt has four fields,

    CTFd challenge name | compose.yml service | container port | template

ctf.sh resolves the published host port of "service:container port" when it
writes connection info into CTFd, so a typo here only shows up at deploy time,
as a challenge whose connection info silently stays unset. This check catches
it earlier:

  - the line has four fields and the CTFd name is not used twice;
  - a template of "hidden" needs no service or port (ctf.sh ignores them);
  - a template with "{port}" needs a service that compose.yml defines and a
    container port that service publishes;
  - any other template (e.g. https://noter1.{host}) may use "-" for service and
    port, but a service or port that is given must still be valid.

compose.yml is read through `docker compose config --format json`, so YAML
anchors, merge keys and ${VAR:-default} interpolation resolve exactly as they
do for ctf.sh. Needs the docker CLI with the compose plugin, not a running
daemon.

Usage: tools/check-connections.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "compose.yml"
CONNECTIONS = ROOT / "platform" / "connections.txt"


def published_container_ports():
    """Map every compose service to the set of container ports it publishes."""
    try:
        proc = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        sys.exit("check-connections: the docker CLI is required (docker compose config)")
    if proc.returncode != 0:
        sys.exit(f"check-connections: docker compose config failed:\n{proc.stderr.strip()}")
    services = json.loads(proc.stdout).get("services") or {}
    return {
        name: {int(p["target"]) for p in (svc.get("ports") or []) if p.get("published")}
        for name, svc in services.items()
    }


def main():
    services = published_container_ports()
    errors = []
    seen = {}
    checked = 0

    for lineno, raw in enumerate(CONNECTIONS.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        where = f"{CONNECTIONS.relative_to(ROOT)}:{lineno}"
        fields = [f.strip() for f in line.split("|", 3)]
        if len(fields) != 4:
            errors.append(f"{where}: expected 4 '|'-separated fields, got {len(fields)}")
            continue
        name, service, port, template = fields
        checked += 1

        if not name:
            errors.append(f"{where}: empty CTFd challenge name")
            continue
        if name in seen:
            errors.append(f"{where}: CTFd name '{name}' already used on line {seen[name]}")
        seen.setdefault(name, lineno)

        if template == "hidden":
            continue
        if not template:
            errors.append(f"{where} ({name}): empty template")
            continue

        needs_port = "{port}" in template
        if service == "-" and port == "-":
            if needs_port:
                errors.append(f"{where} ({name}): template uses {{port}} but service and port are '-'")
            continue

        # A service or port is given, so it has to be right (also when the
        # template has no {port}: a stale reference is still a mistake).
        if service == "-" or port == "-":
            errors.append(f"{where} ({name}): service and port must both be given or both be '-'")
            continue
        if service not in services:
            errors.append(f"{where} ({name}): service '{service}' is not in compose.yml")
            continue
        if not port.isdigit():
            errors.append(f"{where} ({name}): container port '{port}' is not a number")
            continue
        if int(port) not in services[service]:
            published = ", ".join(str(p) for p in sorted(services[service])) or "none"
            errors.append(
                f"{where} ({name}): service '{service}' does not publish container port "
                f"{port} (publishes: {published})"
            )

    if errors:
        print("check-connections: FAILED", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    print(f"check-connections: ok ({checked} lines checked against {len(services)} compose services)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
