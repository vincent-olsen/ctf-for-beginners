Flag is located in `/home/ctf/.flag.txt`. This time it is "hidden",
so normal `ls` wont display it, but `ls -a` will reveal hidden files.

We can still use the `cat` command as last time to get the flag:

```bash
cat .flag.txt
```

## Debrief: what you learn and how to protect against it

**What you learn:** files whose name starts with a dot are "hidden" on Linux, but
only by convention: plain `ls` skips them and `ls -a` shows them. Hidden is not the
same as protected.

**The solve in short:**

1. Connect with `nc <host> <port>`.
2. `ls` does not show the flag, so list everything with `ls -a` (or `ls -la`).
3. `cat .flag.txt`.

**How to protect against it:**

- A leading dot protects nothing. What decides who can read a file is its owner
  and permissions (`chmod 600`, owned by another user).
- Dotfiles such as `.env`, `.git/` and `.ssh/` are the first thing an attacker
  looks for. Keep secrets in a secret store, and never leave `.env` or `.git/`
  inside a folder a web server serves.
