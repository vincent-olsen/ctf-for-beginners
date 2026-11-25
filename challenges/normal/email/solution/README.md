# email — a GitHub user's email via the commits API

**Category:** misc / OSINT · **Flag:** `flag{detter.er.flagget@gmail.com}`

> ⚠️ This depends on live GitHub state (the account
> [`VDNjVbykxKoXSri`](https://github.com/VDNjVbykxKoXSri)). Re-verify
> before each event: the user and repo still exist, and the commits still expose the
> address below. See the note at the end.

You are given only the username `VDNjVbykxKoXSri`, the GitHub account
<https://github.com/VDNjVbykxKoXSri>. The email is not shown on the
profile page, in any repo, or on the commit pages in the web UI — but a commit
object always records its **author's email**, and the REST API returns it.

### Steps

1. Find the user's repositories:

   ```bash
   curl -s https://api.github.com/users/VDNjVbykxKoXSri/repos | grep '"full_name"'
   # ... VDNjVbykxKoXSri/Second-Public-Repo ...
   ```

2. List that repo's commits and read `commit.author.email`:

   ```bash
   curl -s https://api.github.com/repos/VDNjVbykxKoXSri/Second-Public-Repo/commits \
     | grep -E '"email"'
   ```

   The two most recent commits are authored by `detter.er.flagget@gmail.com`.

   (Equivalent routes: append `.patch` to a commit URL, or `git clone` the repo and
   run `git log --format='%ae'`.)

3. The flag is that address:

   ```
   flag{detter.er.flagget@gmail.com}
   ```

**Do not** use the *events* API (`/users/<user>/events/public`) — GitHub only returns
events from roughly the last 90 days, and this account's activity is older, so that
endpoint comes back empty. The commits API has no such window.

**Lesson:** even when a UI hides it, git commits carry the author's email, and
GitHub's REST API exposes it. This is why people use a `noreply` commit email.

### Before the event
- `https://api.github.com/users/VDNjVbykxKoXSri` returns 200 (not suspended).
- `Second-Public-Repo` still exists and its commits still show
  `detter.er.flagget@gmail.com` as an author email.
- That address (and the backup's other accepted variants) is still an accepted flag.
  If GitHub state has changed, push a fresh commit with the intended author email,
  or update the flag.

## Debrief: what you learn and how to protect against it

**What you learn:** OSINT against a developer. Every git commit stores the
author's name and email address. GitHub hides it in the web UI, but the REST API,
a `.patch` URL or a plain `git clone` shows it. Public information is often one
API call away from what the UI displays.

**The solve in short:**

1. List the user's repos: `https://api.github.com/users/<user>/repos`.
2. List the commits of the repo:
   `https://api.github.com/repos/<user>/<repo>/commits`.
3. Read `commit.author.email`. That address is the flag.

**How to protect against it:**

- In GitHub, Settings → Emails: turn on "Keep my email addresses private" and
  "Block command line pushes that expose my email".
- Set git to use the noreply address:
  `git config --global user.email "<id>+<username>@users.noreply.github.com"`.
- Commits that are already pushed keep the old address. Removing it means
  rewriting history, and forks and clones still have it. Treat an address that
  has been in a public commit as public.
