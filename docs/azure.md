# Hosting the CTF on Azure

`./azure.sh` runs [hosting.md](hosting.md) on Azure, from your own machine: it creates
the resource group, network, VM and DNS record, installs Docker and the challenge
firewall on the VM, copies this checkout over SSH and runs `./ctf.sh up --domain` there.

```bash
az login
./azure.sh up --domain ctf.tst.example.com          # test deployment, for 30 days
```

```bash
./azure.sh up --env prd --domain ctf.example.com --expires <YYYY-MM-DD> --registration-code <code> \
  --event-start <YYYY-MM-DD>T16:00+01:00 --event-end <YYYY-MM-DD>T19:00+01:00 --team-size 2   # the day before the event
```

The first `up` of a deployment needs `--domain`; the deployment keeps it (its `domain`
tag), so later runs don't. The domain's DNS zone can be in Azure (`up` writes the
record) or anywhere else (`up` prints the record to create).

Like `ctf.sh up`, the deployment sets CTFd up with every challenge from the repo. If
your `ctfd-backup/` holds a CTFd export, the newest one is copied to the VM and
imported instead (see [local-setup.md](local-setup.md#starting-from-a-ctfd-export-instead)).

Every deployment is short-lived. Its resource group carries an `expires-on` tag, and
a job in the group deletes the whole group in the night after that date. A deployment
lives at most 31 days from today; `./azure.sh extend` moves the date, 31 days at a time.

Needs the Azure CLI (logged in), `ssh`, `rsync` and `curl`. It works from macOS and Linux.

## Plan: two deployments, not one

Rather than one VM running for weeks, use two short-lived deployments:

| When | What | Command |
|---|---|---|
| the weeks before | test deployment `rsg-tst-ctf`; the VM stops every night at 23:00 (`--start 0730` starts it on weekday mornings) | `./azure.sh deploy`, `start`, `ssh` |
| a few days before | dress rehearsal on tst: solve every challenge, check `https://status.<domain>`, take a dump on the VM and put it back | `./azure.sh ssh ./ctf-for-n00bs/ctf.sh backup --db`, `./azure.sh restore` |
| the day before | event deployment `rsg-prd-ctf`, with the event's times | `./azure.sh up --env prd --domain <domain> --expires <date> --registration-code <code> --event-start <time> --event-end <time> --team-size 2` |
| the day before | delete the test deployment (or let it expire) | `./azure.sh down` |
| the event, before the start | open the challenges to everyone | `./azure.sh open --env prd` |
| the event, during | the VM dumps CTFd's database every 10 minutes from 30 minutes before the start to 30 after the end | nothing to do; `ctfd-backup/db/` on the VM. If CTFd is damaged: `./azure.sh restore --env prd` |
| the event, after the end | close them, keep the scoreboard | `./azure.sh close --env prd`, `./azure.sh backup --env prd` |
| the night after `--expires` | the event deployment is deleted | or `./azure.sh down --env prd` earlier |

Why two:

- **Each one stays under a month.** Nothing needs to exist between the end of
  testing and the week before the event.
- **The event deployment is a rehearsal.** It is the same command you tested, on a
  fresh VM with current OS packages and Docker.
- **Less exposure.** The challenges hand out shells. They are open to the internet
  only between `open` and `close`, and the VM is only up for the weeks it's used.
- **They can overlap.** Give them different domains (`ctf.tst.example.com` and
  `ctf.example.com`), so both can run during the dry-run week.

If testing needs more than a month, run `./azure.sh extend --env tst +30`. Or tear the
test deployment down and bring it up again later: everything is in git, and a fresh
`up` takes about fifteen minutes.

**Carrying CTFd changes from tst to prd.** Changes made in the CTFd admin UI live in
the tst deployment's database. Commit them to the repo instead: every challenge, page and setting
the prd deployment needs comes from `challenges/` and `platform/` on its first `up`.
For anything you can only change in the admin panel, run `./azure.sh backup --env tst`
and rename the export to `ctfd-backup/<Name>.<YYYY-MM-DD_HH_MM_SS>.zip`: the prd
deployment's first `up` then imports it, and `--fresh` removes the testers' accounts.

## A preview before the event

To let people try a few challenges before the event, run the test deployment as a
preview on its own domain. Only the challenges you name are shown, and nobody needs a
CTFd account: flags are checked, but nothing is saved. The site can sit behind
Microsoft sign-in, and the terminal challenges can be limited to a fixed address
(an office, say).

```bash
./azure.sh up --domain ctf-preview.example.com --preview julius,meow1 --sso-client-id <client id> --player-ip <office IP> --shutdown off --size Standard_B2s
```

| Option | What it does |
|---|---|
| `--domain ctf-preview.example.com` | The preview's own address. `up` writes its alias record in the domain's Azure DNS zone and Caddy gets its certificate. The deployment keeps the domain (its `domain` tag), so later runs don't need the option. Moving a running deployment to another domain deletes the old name's record, if it still points at this deployment. With sign-in, the app registration needs the new redirect URI first ([below](#the-app-registration)). |
| `--preview julius,meow1` | `ctf.sh` hides every other challenge and the pages (the Info page), starts only the preview's containers, makes the board public and turns off registration, the scoreboard and the account pages. The `ctf_preview` plugin ([platform/plugins/](../platform/plugins/ctf_preview/__init__.py)) checks flags for visitors without an account. The site turns into a vintage green-phosphor terminal, with a countdown to the event's start (`CTF_PREVIEW_EVENT_START` in [`preview.js`](../platform/theme/preview.js)) under the page title. A solve is kept in the visitor's browser only and gets an `ACCESS GRANTED` moment. The first page of a browser session opens with a 5-second retro boot screen ([platform/theme/README.md](../platform/theme/README.md)). |
| `--sso-client-id <id>` | Caddy sends every visitor through oauth2-proxy, which signs them in with Entra ID ([ctfd.sso.yml](../platform/ctfd.sso.yml)). The app registration is single tenant, so only accounts in the subscription's tenant get in. `azure.sh` asks for the client secret (or takes `SSO_CLIENT_SECRET`) and passes it to the VM on stdin, where it stays in `.ctf/sso-client-secret` with the client id it belongs to. Enter keeps the VM's, which works only for the client id it was given with: a new app registration needs its own secret once. |
| `--player-ip <office IP>` | The NSG rule `allow-challenges-players` opens the challenge ports to these addresses at all times, but not SSH. A full-tunnel VPN sends its users' traffic through the office, so the office's address covers both. `--player-ip none` removes the rule. |
| `--shutdown off` | The challenges are still closed (players' addresses don't count as `open`), so without it the VM stops at 23:00 and stays off until `./azure.sh start`. To save the nights instead, use `--shutdown 2300 --start 0730`: the VM stops at 23:00 and starts again at 07:30 Monday to Friday (see [Lifetime and cost](#lifetime-and-cost)). |
| `--size Standard_B2s` | Optional: a preview runs one challenge container, far less than the default size is for. |

Sign-in covers the website only: `nc` is plain TCP, with no browser to sign in with,
which is why meow1 is limited by address instead.

The VM keeps the preview and the sign-in, so a later `./azure.sh deploy` leaves them
in place. To get the whole CTF back, end both and remove the players' rule:

```bash
./azure.sh deploy --preview "" --sso-client-id ""
```

```bash
./azure.sh up --domain ctf.tst.example.com --player-ip none --size Standard_D4s_v5
```

Ending the preview puts back exactly what it changed: the challenges it hid and the
four CTFd settings it set.

### The app registration

Sign-in needs an app registration in the subscription's Entra ID tenant, made once,
with the redirect URI `https://<domain>/oauth2/callback` for every domain it serves:

```bash
az login --tenant <tenant id>
az ad app create --display-name ctf-tst --sign-in-audience AzureADMyOrg --web-redirect-uris https://ctf.tst.example.com/oauth2/callback --optional-claims '{"idToken":[{"name":"email","essential":false}]}' --query appId -o tsv
az ad sp create --id <client id>
az ad app permission add --id <client id> --api 00000003-0000-0000-c000-000000000000 --api-permissions 37f7f235-527c-4136-accd-4a02d197296e=Scope 64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0=Scope 14dad69e-099b-42c9-810b-d002981feec1=Scope
az ad app credential reset --id <client id> --display-name ctf-tst --end-date <YYYY-MM-DD> --append --query password -o tsv | pbcopy
```

To serve another domain, add its redirect URI (the list replaces the old one, so it
names all of them):

```bash
az ad app update --id <client id> --web-redirect-uris https://ctf-preview.example.com/oauth2/callback https://ctf.tst.example.com/oauth2/callback
```

The permissions are Microsoft Graph's `openid`, `email` and `profile`, and the
optional `email` claim puts the address in the ID token for the tenant's own users.
If the tenant lets users consent to these themselves, everyone approves once at their
first sign-in. An Entra admin can approve for everyone instead:
`az ad app permission admin-consent --id <client id>`. To let only some people in,
set *Assignment required* on the enterprise application and assign a group.

## What `up` creates

One resource group per environment, in Norway East unless `--location` says otherwise:

| Resource | tst name | Purpose |
|---|---|---|
| Resource group | `rsg-tst-ctf` | everything below; carries the tags and `expires-on` |
| Virtual machine | `srv-tst-ctf` | Ubuntu 24.04, `Standard_D4s_v5` (4 vCPU, 16 GB, x86-64), 64 GB SSD, Trusted Launch, no managed identity |
| Network | `vnet-tst-ctf`, `snet-tst-ctf`, `nic-tst-ctf` | its own network, peered with nothing |
| Network security group | `nsg-tst-ctf` | SSH from the admin IPs; 80/443 from anywhere; challenge ports from the admin and player IPs, or from anywhere once opened |
| Public IP | `pip-tst-ctf` | static, Standard |
| Shutdown schedule | `shutdown-computevm-srv-tst-ctf` | deallocates the VM at 23:00 Oslo time, with an email 30 minutes before |
| Logic App | `logic-tst-ctf-expiry` | runs at 03:00 each night and deletes the group once `expires-on` has passed; its own identity needs Contributor on the group |
| Logic App | `logic-tst-ctf-start` | starts the VM Monday to Friday mornings; disabled unless `--start` is given; its own identity needs Virtual Machine Contributor on the VM, and has it only while `--start` is on |
| DNS record | the domain's name in its Azure DNS zone | an alias record for the public IP; it lives in the zone's own resource group |

Names are `<type>-<env>-ctf`, with Microsoft's standard abbreviations for the types.
The NSG's challenge ports come from `compose.yml`, so a new hosted challenge only
needs its compose service. Run `./azure.sh up` afterwards to update the rule.

Tags on the group: `owner`, `contact` (from your git config or Azure login),
`project=ctf`, `environment`, `domain`, `managed-by=azure.sh`, `created-on` and
`expires-on`.

A **VM, not Container Apps**: the CTF is about 30 containers, most of them raw TCP
services on fixed ports, with Docker networks that block container-to-container
traffic. `ctf.sh` runs all of that unchanged on one VM. It is **deployed from your
machine**, with your own `az login`, so the repo needs no Azure secrets.

If the CTF goes into a subscription that also holds production systems, isolation is
inside the resource group (see [Security](#security)), but tell whoever owns the
subscription before the first `up`.

## Commands

All take `--env tst|prd` (default `tst`).

| Command | What it does |
|---|---|
| `./azure.sh up` | create or update the deployment and start the CTF (safe to rerun; keeps the expiry) |
| `./azure.sh deploy` | copy this checkout to the VM and rerun `./ctf.sh up` there: a challenge fix, no Azure changes |
| `./azure.sh open` | event mode: challenges reachable from the internet, nightly shutdown off |
| `./azure.sh close` | test mode: challenges only from the admin IPs, nightly shutdown back as it was |
| `./azure.sh allow-me` | add this machine's public IP to the admin IPs (SSH, and closed challenges) |
| `./azure.sh status` | expiry, VM state, mode, and `ctf.sh status` from the VM |
| `./azure.sh extend <YYYY-MM-DD>` | set the expiry (or `+N` for N days from today); at most 31 days ahead |
| `./azure.sh stop` / `start` | deallocate or start the VM; the CTF comes back as it was |
| `./azure.sh ssh [CMD]` | shell on the VM, e.g. `./azure.sh ssh docker ps` (options go before `ssh`'s command) |
| `./azure.sh backup` | `./ctf.sh backup` on the VM, copied to `ctfd-backup/local.<timestamp>.zip` here |
| `./azure.sh restore` | lists the VM's database dumps, newest first, asks which one, and puts CTFd's database back as it was then (`./ctf.sh restore-db` on the VM; everything after that dump is lost, and the database as it is now is dumped first). `./azure.sh restore FILE --yes` skips the questions |
| `./azure.sh down` | delete the resource group and the DNS records (`--backup` exports CTFd first) |

Options for `up`: `--domain`, `--days N`/`--expires DATE`, `--admin-ip CIDR,...`,
`--player-ip CIDR,...|none`, `--size`, `--location`, `--shutdown HHMM|off`, `--start HHMM|off`,
`--notify EMAIL|none`, `--registration-code`, `--egress block|allow`,
`--dns-zone-id ID|none`, `--preview NAMES`, `--sso-client-id ID`, `--lang no|en`,
`--event-start TIME`, `--event-end TIME`, `--event-freeze TIME`, `--team-size N`,
`--status on|off`, `--subscription`.
Leave one out and the deployment keeps its current value. `deploy` also takes
`--preview` and `--sso-client-id` (see [A preview before the event](#a-preview-before-the-event)),
`--lang` (the language players see until they switch, see [language.md](language.md)),
and the event's times, team size and `--status`, which go to `./ctf.sh up` on the VM
([hosting.md](hosting.md#4-deploy)). The event's options are named so as not to clash
with `--start`, the VM's morning start.

Every `up` and `deploy` also gives the status page its DNS record, `status.<domain>`
next to the deployment's own (an alias record, gone with the deployment), and has
`bootstrap.sh` install `ctf-backup.timer` on the VM: a dump of CTFd's database every
10 minutes while the event is on, kept in `ctfd-backup/db/` on the VM for 7 days
(`deploy`'s rsync leaves them alone). Security updates keep installing on their own,
but `needrestart` leaves Docker running and the VM never reboots by itself, so nothing
restarts CTFd and the challenges in the middle of the event.
`open`, `close` and `allow-me` also take `--days`/`--expires`, e.g.
`./azure.sh open --env prd --expires <YYYY-MM-DD>`. See `./azure.sh --help`.

The first `up` of a new CTF generates a registration code (printed at the end), so
nobody signs up while you test. `--registration-code ""` opens registration. Until
the first `up` has finished setting CTFd up, every rerun passes the same code again,
along with `--fresh` (for an imported export); later runs pass neither. `ADMIN_PASSWORD=...` sets the CTFd admin password,
like with `ctf.sh`.

Local state lives in `.ctf/azure/` (git-ignored): the SSH key, the chosen subscription,
the DNS zone and record, and the generated registration code. The deployment's
settings live in Azure, so another organiser with access to the subscription can run
`./azure.sh` for the same deployment. They start with `./azure.sh allow-me`, and their
machine's SSH key is added through the VM agent the first time any command connects.

## Lifetime and cost

- **Expiry.** `logic-<env>-ctf-expiry` reads the group's `expires-on` tag every night
  at 03:00 Oslo time, and deletes the group once the date has passed. To keep it
  longer, change the tag with `./azure.sh extend`. Removing the tag in the portal
  switches the deletion off (`status` then says `NOT deleted automatically`). A value
  that isn't exactly `YYYY-MM-DD`, an emptied one included, never deletes the group
  either: most such values make the nightly run fail, which shows in the Logic App's
  run history.
- **Role assignments, made by an Owner.** The expiry job and the morning start each
  run as their Logic App's own system-assigned identity. The expiry job needs
  Contributor on the group; the morning start only Virtual Machine Contributor on the
  VM, and only with `--start`: without it, `up` takes that role away again. Handing a
  role out takes Owner or User Access Administrator. If you have neither, `up` prints
  the command an Owner has to run for each, once per deployment; until then `status` shows
  `NOT deleted automatically` (and the morning start as not working), and you delete
  the deployment yourself with `./azure.sh down`, which needs no Owner. The expiry
  job's identity is the one it has always had, so a group an Owner armed before the
  morning start existed stays armed.
- **Nightly shutdown.** While closed, the VM deallocates at 23:00 and stays off until
  `./azure.sh start`. Stopped, it costs only the disk and the IP. The shutdown is
  always off while the challenges are open, so the VM can't stop mid-event, whatever
  `up` or `allow-me` runs meanwhile; `close` brings back the setting chosen with
  `--shutdown` (kept in the schedule's `auto-shutdown` tag).
- **Morning start (opt-in).** `./azure.sh up --start 0730` starts the VM at 07:30 Oslo
  time, Monday to Friday, so with the nightly shutdown it runs only in the daytime:
  `./azure.sh up --shutdown 2300 --start 0730`. `--start off` turns it off again. It
  needs the role assignment above; weekends stay off until `./azure.sh start`.
- **Rough cost** (pay-as-you-go, Norway East; check the pricing calculator). The
  VM is about USD 0.25 an hour while it runs. The disk and IP are about USD 10 a month,
  running or not. A month of testing with a few evenings a week comes to about USD 20;
  the event deployment about the same. Worst case, if it's left open and forgotten,
  the expiry caps it at one VM for 31 days: under USD 200.

## Security

- **No Azure credentials on the VM.** It has no managed identity, and it sits in its
  own network, peered with nothing. Someone who escapes a container finds nothing to
  reach the rest of the subscription with.
- **NSG.** SSH is allowed only from the admin IPs. 80/443 are always open, because
  Let's Encrypt validates from addresses nobody can allow-list. Challenge ports are
  open only between `open` and `close`, apart from the players' IPs (`--player-ip`),
  which never get SSH.
- **Microsoft sign-in** (`--sso-client-id`) keeps the website to the tenant's
  accounts, with the 80/443 rule unchanged. Its client secret is never on a command
  line or in the repo: it goes to the VM on stdin and lives in `.ctf/` there, readable
  by the admin user only. Give it a short expiry, and keep a copy in a password manager.
- **Firewall on the challenge networks** ([`bootstrap.sh`](../platform/azure/bootstrap.sh),
  hosting.md's step 3, automated and re-applied at every boot). A player's shell can't
  reach the metadata service, the VM agent, or services on the VM. By default it
  can't open connections to the internet either, so nobody can use a meow shell to
  attack others from your IP address. No challenge needs outbound access (`noter5`
  only talks to its backend, inside its own network). `--egress allow` lifts that
  block and keeps the others.
- **Only your checkout goes over.** The code is copied over SSH, so the VM holds no
  GitHub credentials. Of `ctfd-backup/`, only the export `ctf.sh` imports, if any, is
  copied: any others hold past events' participants.
- **The hostname becomes public.** Certificate transparency logs publish it minutes
  after the first certificate, and scanners follow. Hence the registration code and
  the closed challenges while testing.
- **No dangling DNS.** The DNS record is an alias to the public IP resource, so it goes
  empty when the group is deleted and never points at an IP Azure has handed to
  someone else. If Azure refuses the alias, `up` makes a plain A record instead and
  says so; that one stays behind when the group expires, so run `./azure.sh down` from
  the same machine afterwards, which removes it. A record you created by hand must
  be deleted by hand after `down`.
- **Admin IPs are addresses, not people.** At a venue, everyone on its Wi-Fi shares
  your public IP. SSH still requires the key.

## Before the first `up`

- **Subscription:** `az account set --subscription <name>`, or pass `--subscription`.
  `up` shows which one it will use and asks.
- **DNS:** `up` looks for an Azure DNS zone for the domain in every subscription of
  the tenant you can see (for `ctf.tst.example.com`: `example.com`, or
  `tst.example.com` if that is delegated), and creates the record. Without write
  access to one, it prints the A record to create by hand and carries on
  (`--dns-zone-id none` skips the zone).
- **CAA:** the CAA records closest to the domain (on `ctf.tst`, else `tst`, else
  `example.com`) must allow `letsencrypt.org`, or Caddy gets no certificate. `up` warns
  about this when the zone is in Azure.
- **Quota:** `Standard_D4s_v5` needs 4 free vCPUs of the DSv5 family in the region.
  With tst and prd both up, that's 8. Use `--size` for another size.
- **Tenant policies:** some tenants require resource names in a set pattern, or
  tags. `srv-<env>-ctf` exists because one such policy only allowed VMs named
  `srv-<env>-*`; if yours denies a resource, the deployment's error names the policy.

## Troubleshooting

- **SSH times out.** Your public IP has changed: `./azure.sh allow-me`.
- **No certificate.** DNS doesn't point at the VM yet (`dig +short <domain>`), or a
  CAA record blocks Let's Encrypt. Caddy retries by itself: `./azure.sh ssh
  ctf-for-n00bs/ctf.sh logs caddy`. Let's Encrypt issues at most 5 certificates for
  the same name per week, so don't recreate a deployment more often than that.
  `stop`/`start` keeps the certificate.
- **`SkuNotAvailable` or a quota error.** Pick another size with `--size`. For a new
  deployment, another region with `--location` also works.
- **Resizing fails** because the size isn't available on the current hardware:
  `./azure.sh stop`, then `./azure.sh up --size <size>`.
- **`up` was interrupted** (laptop asleep, lost connection): run it again. Every step
  is safe to repeat.
