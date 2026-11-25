/* logrotate-helper -- installed SUID root in the Dockerfile.
 *
 * It "rotates" the web logs by taring them up. This version is HARDENED against
 * the obvious privesc: it resets $PATH to a safe value and calls tar by its
 * ABSOLUTE path, so dropping a fake `tar` earlier on $PATH no longer runs as
 * root -- the textbook PATH-hijack is closed.
 *
 * The bug it does NOT close: it runs the backup through bash (`/bin/bash -c`),
 * and bash still sources the file named by $BASH_ENV when it starts a
 * non-interactive shell. The helper is SUID root and drops to a REAL root uid
 * first (setuid(0)), so bash sees euid==uid==0 and does not drop privileges --
 * meaning a caller who sets BASH_ENV to their own script gets it sourced as
 * root. That is a classic SUID-bash / BASH_ENV privesc, one step up from the
 * PATH hijack this version patches.
 *
 * (Ships intentionally vulnerable; see solution/README.md.)
 */
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    if (setgid(0) != 0 || setuid(0) != 0)
        return 1;
    /* Hardened: a clean $PATH and an absolute tar close the naive PATH hijack. */
    setenv("PATH", "/usr/bin:/bin", 1);
    /* ...but running it through bash -c still honours $BASH_ENV, as root. */
    execl("/bin/bash", "bash", "-c",
          "/usr/bin/tar -czf /var/backups/www.tgz -C /var/www . 2>/dev/null",
          (char *)NULL);
    return 1;
}
