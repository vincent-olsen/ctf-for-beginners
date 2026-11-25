# Hosting the CTF on a server

On Azure, [`./azure.sh up`](azure.md) does sections 1–4 for you (VM, DNS, firewall,
deploy) and deletes the deployment again after a set date.

The same `ctf.sh` runs the CTF on a public server. `--domain` switches it to hosted
mode:

```bash
./ctf.sh up --domain ctf.example.com --registration-code <code>
```

Compared with a local run, hosted mode:

- serves CTFd at `https://ctf.example.com` through Caddy, with an automatic Let's
  Encrypt certificate (nginx is disabled)
- publishes challenge ports on all interfaces instead of `127.0.0.1`
- writes `ctf.example.com` into every challenge's connection info
  (`nc ctf.example.com 4441`, `http://ctf.example.com:5001`, ...)

`ctf.example.com` is used as the example domain throughout. Like a local run, the
first `up` sets CTFd up with every challenge from the repo
([local-setup.md](local-setup.md#where-ctfds-content-comes-from)); nothing else needs
to be on the server.

## 1. Server

- A Linux VM on **x86-64 (amd64)**, so the pwn binaries run natively. ARM servers
  work but need QEMU (`docker run --privileged --rm tonistiigi/binfmt --install amd64`).
- 4 vCPU, 8 GB RAM and 30 GB disk are comfortable for ~100 players.
- Docker Engine with the compose plugin, plus git:
  ```bash
  curl -fsSL https://get.docker.com | sh
  ```

## 2. DNS

Create an `A` record for `ctf.example.com` pointing to the server's public IP (and an
`AAAA` record for IPv6). Caddy requests the certificate on first start, so DNS must
resolve before you run `ctf.sh`.

## 3. Firewall

Open these inbound ports, and nothing else:

| Port | For |
|---|---|
| 22/tcp | SSH (restrict it to your IP) |
| 80/tcp, 443/tcp, 443/udp | CTFd over HTTPS (80 is needed for the certificate challenge) |
| 4441–4444/tcp | meow1–4 |
| 4446–4449/tcp | meow-ai (AI-modus): 4446 for effects level 2, the default; 4447–4449 for levels −1, 3 and 1 |
| 1241–1243/tcp | overflow1–3 |
| 1246–1249/tcp | pwn-ai (AI-modus): 1246 for effects level 2, the default; 1247–1249 for levels −1, 3 and 1 |
| 5001–5004, 5011–5013/tcp | noter1–4, api1–3 |
| 5006–5010/tcp | robot-ai, noter-ai, api-ai, viking-ai, marvin-llm (AI-modus) |
| 8080/tcp | viking |

The hidden pwn challenges — binary1 (1231), binary2 (1232), overflow4 (1244) and
overflow5/`binary` (1245) — plus marvin (5005) and noter5 (1024) sit in the `extra`
profile in `compose.yml`, which `ctf.sh up` doesn't start, so their ports don't need
to be open. If you release overflow5 (or any of them) during the event, start it and
open its port then.

Docker writes its own iptables rules for published ports, so it bypasses `ufw`.
Enforce the list in your cloud provider's firewall or security group.

The meow challenges hand every player a shell, and a pwn exploit gives one too.
From there, Docker lets them reach the cloud metadata service (`169.254.169.254`,
which hands out the VM's credentials) and every service on the server itself, and
the cloud firewall never sees that traffic. Block both for the challenge bridges
(`ctf-chal`, `ctf-noter5`, named in `compose.yml`):

```bash
for br in ctf-chal ctf-noter5; do
  sudo iptables -I DOCKER-USER -i "$br" -d 169.254.169.254 -j DROP
  sudo iptables -I INPUT -i "$br" -m conntrack --ctstate NEW -j DROP
done
```

The rules are lost on reboot; keep them with `iptables-persistent`
(`sudo netfilter-persistent save`).

## 4. Deploy

On the server:

```bash
git clone <this repository's URL> ctf-for-n00bs
```

```bash
cd ctf-for-n00bs && ADMIN_PASSWORD='<strong password>' ./ctf.sh up --domain ctf.example.com --registration-code '<code>' \
  --event-start 2026-11-18T16:00+01:00 --event-end 2026-11-18T19:00+01:00 --team-size 2
```

- Leave out `--registration-code` for open registration.
- Starting from a CTFd export instead (copied to `ctfd-backup/` on the server, see
  [local-setup.md](local-setup.md#starting-from-a-ctfd-export-instead)): add
  `--fresh`, which removes the imported players, teams, submissions and solves and
  keeps challenges, pages, config and admin accounts. **Always use it on a public
  host**: an export from an earlier event holds its participants' names, emails and
  password hashes. It only acts on a run that imports (the first run, or
  `--reimport`), so rerunning the command during the event leaves players alone.
- `--event-start`, `--event-end` and `--event-freeze` set CTFd's start, end and
  scoreboard freeze time, each with its UTC offset (`+01:00` is Oslo in winter,
  `+02:00` in summer); `--team-size` the most players in a team. `ctf.sh` saves them,
  sets them in CTFd on the run that gives them and on the first run (or after an
  import, which clears the export's own dates), and leaves CTFd's alone otherwise, so a
  change in the admin panel during the event stays. `""` clears one.
- `ADMIN_PASSWORD` is stored in `.ctf/admin-password` and set in CTFd by a
  `./ctf.sh up` that is given it, by the first run (a generated one when you give
  none) and by every `--reimport`. A routine `up` without it leaves
  CTFd's admin password alone, so one changed in the CTFd UI stays; the file then
  no longer matches it. Rerun `up` with a new `ADMIN_PASSWORD` to set both. Only
  `up` applies it: other commands ignore `ADMIN_PASSWORD`.
- `--sso-tenant <id> --sso-client-id <id>` puts Microsoft sign-in (Entra ID, through
  oauth2-proxy) in front of CTFd; the first run with each client id also needs
  `SSO_CLIENT_SECRET=<client secret>`, which is kept in `.ctf/sso-client-secret`
  for that client id only.
  `--preview julius,meow1` shows only those challenges, to visitors without an
  account. Both are described in [azure.md](azure.md#a-preview-before-the-event).

Then, in CTFd at `https://ctf.example.com/admin`:

- **Config → General**: set the description. (Do **not** rely on setting the CTF
  *name* here — `ctf.sh up` rewrites `ctf_name` from the brand folder's `brand.conf`
  on every run; change the name there, or with `--brand`, instead.)
- **Challenges**: check the board. Every challenge is created from its
  `metadata.yml` with its `distfiles/` as downloads; the retired and unreleased
  ones (`state: hidden`) stay hidden until you show them. On later runs a file is
  replaced when the challenge's `distfiles/` has one of the same name with other
  bytes (a rebuilt binary, say); a new file under another name is yours to add
  under the challenge's **Files**.
- **Config → Brackets** and **Custom Fields** are empty (an import also removes an
  export's own), so registering takes a name, an email, a password and the
  registration code, and creating a team a name and a password. What you add there
  stays until the next `--reimport`.

**The status page.** `https://status.ctf.example.com` shows whether CTFd and each running
challenge answer, checked once a minute (Gatus, [`platform/ctfd.status.yml`](../platform/ctfd.status.yml),
64 MB at most). Web challenges count as up while they answer HTTP without a server
error, terminal and pwn ones while their port takes connections. It needs a DNS record
for `status.<domain>` (on Azure `azure.sh` makes it), is open to everyone even behind
Microsoft sign-in, and is on <http://localhost:8081> on the machine itself.
`--status off` leaves it out.

## 5. During the event

| Task | Command |
|---|---|
| status | `./ctf.sh status` |
| reset a broken challenge | `./ctf.sh reset meow3` (recreates it from its image; a restart would keep what players changed) |
| challenge logs | `./ctf.sh logs noter4` |
| CTFd / Caddy logs | `./ctf.sh logs ctfd`, `./ctf.sh logs caddy` |
| is everything up? | `https://status.ctf.example.com` |
| dump the database now | `./ctf.sh backup --db` (a few KB, under a second) |
| put a dump back | `./ctf.sh restore-db` (lists the dumps, newest first, and asks which one), or `./ctf.sh restore-db ctfd.<timestamp>.sql.gz`; on Azure, `./azure.sh restore` from your own machine |
| deploy a challenge fix | `git pull && ./ctf.sh up` |

Containers restart automatically if they crash or the server reboots. `ctf.sh`
writes the bind address to `.env` next to `compose.yml`, so plain `docker compose`
commands in the repo folder publish on the same interface.

**The scoreboard on the big screen.** Open `/scoreboard?board=all` on the
projector's machine, logged in as the admin or as anyone who may see the
scoreboard, and click **Sound off** under the title to turn the sound on (once per
browser; after a reload, click anywhere on the page). **Test** next to it plays
the first-blood show with an example, for the volume. From then on the first team
to solve each challenge gets its moment there, and the table and graph follow
every solve within seconds
([platform/theme/README.md](../platform/theme/README.md#first-blood)).

**Backups during the event.** `./ctf.sh backup --db` dumps CTFd's database (players,
teams, submissions, solves, unlocks, config) to `ctfd-backup/db/ctfd.<timestamp>.sql.gz`,
git-ignored and readable by you only, and deletes dumps older than 7 days. With
`--if-event` it dumps only from 30 minutes before CTFd's start time to 30 minutes
after its end time: run that from a timer every 10 minutes (on Azure, `bootstrap.sh`
installs the systemd timer `ctf-backup.timer`). `./ctf.sh restore-db FILE` dumps the
database as it is, stops the proxy, loads FILE, empties CTFd's cache and starts
everything again. Uploaded files aren't in a dump; they come from the repo and don't
change during an event.

If CTFd ever comes up empty after it has been configured (a wiped database), `up`
stops instead of starting a new CTF over it: put a dump back with `restore-db`, or
start over with `--reimport`.

## 6. After the event

```bash
./ctf.sh backup
```

This writes `ctfd-backup/local.<timestamp>.zip`, the whole event: scoreboard,
players and solves. It holds this event's participants, so git ignores it and
`ctf.sh` never imports it by default. To start a later CTF from it, rename it, e.g.
`ctfd-backup/My CTF 2027.2027-03-01_18_00_00.zip`. Then:

```bash
./ctf.sh down
```

## Optional: HTTPS for the web challenges

By default, web challenges are plain HTTP on their own port
(`http://ctf.example.com:5001`). To serve them as `https://noter1.ctf.example.com` instead:

1. Add DNS records for the subdomains, or one wildcard `*.ctf.example.com`.
2. Uncomment and extend the blocks in [`platform/Caddyfile`](../platform/Caddyfile).
3. Change the templates in [`platform/connections.txt`](../platform/connections.txt):
   ```
   noter1 | - | - | https://noter1.{host}
   ```
4. Run `./ctf.sh up` again.

## Security notes

- Challenge containers can't reach each other directly: the shared network has
  inter-container traffic disabled. noter5 and its backend share a separate
  network, and the backend isn't published. Step 3's rules stop a player's shell
  from reaching the cloud metadata service and the host; they do **not** block
  general outbound internet, which stays open on a plain host. (On Azure,
  `platform/azure/bootstrap.sh` also blocks outbound internet by default — see
  [azure.md](azure.md) and `--egress`.)
- Each challenge is capped at 256 processes, 512 MB of memory and one CPU, to
  contain fork bombs and runaway exploits. CTFd and MariaDB get twice the default
  CPU weight, so they're served first when the challenges keep the VM busy.
- In the shared shells (meow, the pwn challenges), `/tmp` is mode 1733: every player
  can create files there, but nobody can list it, so nobody finds another player's
  work (meow-ai's solve writes `/tmp/tar`).
- CTFd's app port (8000), MariaDB and Redis are never published. Only Caddy faces
  the internet, and `ctf.sh` starts it only after CTFd is set up and configured,
  so CTFd's setup page is never public.
- The flags, and the writeups, are in this repository, so anyone can look them up.
  For an event where that matters, change the flags in a private copy first (each
  challenge's `metadata.yml` and the flag in its `challenge/`; `tools/check-flags.py`
  checks that they agree).

## Switching back to local

```bash
./ctf.sh down && ./ctf.sh up --domain "" --host localhost
```
