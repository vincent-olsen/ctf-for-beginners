In this challenge, there are multiple directories (10), with several files inside (10).
Quick maths: There are 100 files on the server. Each with their own random ASCII art.

We could find the flag manually, but that would take forever.

Luckely in linux there is several ways to tackle this:

```bash
cat */* | grep "flag"
find . -exec grep "flag" {} \;
for i in $(ls); do cat $i/* | grep "flag"; done
```

## Debrief: what you learn and how to protect against it

**What you learn:** how to search many files at once instead of opening them one by
one: wildcards (`*/*`), pipes (`|`), `grep` and `find`. The lesson is to let the
shell do the repetitive work.

**The solve in short:**

1. Connect and look around: 10 directories with 10 files each.
2. Search all of them in one go, e.g. `cat */* | grep flag` or `grep -r flag .`.
3. The matching line is the flag.

**How to protect against it:** there is no bug here, it is a skills task. The
real-world point is that hiding a secret among a lot of noise does not work.

- An attacker who lands on a machine greps for `password`, `token` and `BEGIN
  PRIVATE KEY` across the whole disk in seconds. Don't leave credentials in
  files, use a secret store.
- Run the same search yourself first: secret scanners (gitleaks, trufflehog) find
  what an attacker would find.
