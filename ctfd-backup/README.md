# ctfd-backup/

CTFd exports and database dumps you take of a running CTF. You don't need anything
here to run the CTF: `./ctf.sh up` sets CTFd up from the repo. Everything in this
folder except this file is git-ignored: an export or a dump holds the participants
of an event (names, emails, password hashes, IP addresses), so it stays on the
organiser's machine and never goes into the repository.

- `<CTF name>.<YYYY-MM-DD_HH_MM_SS>.zip`: a CTFd export (Admin → Config → Backup →
  Export). If there is one, a new CTF starts from the one with the newest timestamp
  instead of from the repo; `./ctf.sh up --backup FILE` picks another.
- `local.<timestamp>.zip`: what `./ctf.sh backup` writes, e.g. after an event.
  Never imported until you rename it to the pattern above.
- `db/ctfd.<timestamp>.sql.gz`: what `./ctf.sh backup --db` writes, for
  `./ctf.sh restore-db`. Deleted after 7 days.

See [docs/local-setup.md](../docs/local-setup.md#starting-from-a-ctfd-export-instead).
