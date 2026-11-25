Flag is somewhere on the server. 
This time, manually looking in each file is not doable.

Lets use `find` to locate it.
We know it is a file named `flag.txt` based on the description.
We should search in `/`.

```bash
find / -name "flag.txt"

find: '/proc/tty/driver': Permission denied
/var/lib/dpkg/info/flag.txt
find: '/var/lib/apt/lists/partial': Permission denied
find: '/var/cache/apt/archives/partial': Permission denied
find: '/var/cache/ldconfig': Permission denied
find: '/root': Permission denied
```

The only file we have permission to open also contains the flag:

```bash
cat /var/lib/dpkg/info/flag.txt
```

## Debrief: what you learn and how to protect against it

**What you learn:** how to find a file anywhere on the filesystem with `find`, and
how to read its output: the `Permission denied` lines show where you are not
allowed, the remaining line is the hit.

**The solve in short:**

1. Connect. The description says the file is called `flag.txt`.
2. Search from the root: `find / -name flag.txt 2>/dev/null` (`2>/dev/null` hides
   the permission errors).
3. `cat /var/lib/dpkg/info/flag.txt`.

**How to protect against it:**

- An unusual location is not protection. The file is readable by every user, so
  it is found in one command. Only ownership and permissions (`chmod 600`,
  `root`-owned) keep it away from other users.
- Check a server for files that are readable or writable by everyone
  (`find / -perm -o+r -type f`, `-perm -o+w`) and give service accounts only the
  access they need.
