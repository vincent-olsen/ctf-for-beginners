The message refers to `robots.txt`, a file where a site lists the paths it doesn't want bots to crawl.

Fetch `/robots.txt` on the challenge site (e.g. `http://<host>:<port>/robots.txt`). It disallows `/secret`.

Visiting `/secret` reveals the flag.

## Debrief: what you learn and how to protect against it

**What you learn:** the same lesson as `noter2`: `robots.txt` asks crawlers to
stay away from certain paths, it is public, and it protects nothing.

**The solve in short:**

1. The description points to robots (Marvin is one).
2. Open `/robots.txt`: it disallows `/secret`.
3. Open `/secret` and read the flag.

**How to protect against it:**

- Put real access control (login and an authorisation check on the server) on
  pages that are not for everyone.
- Keep sensitive paths out of `robots.txt`. Use `noindex` on the page to stay
  out of search results.
- A secret URL is not a secret: it ends up in browser history, logs, referrer
  headers and wordlists.
