import os
import sys
import time
from requests import RequestException, Session
from logzero import logger


url = os.environ.get("PROXY_URL", "http://127.0.0.1:1024")
flag = "flag{hi_my_n4me_i5_h4ckerman}"
# Made at build time (Dockerfile), so a restarted proxy logs in as the same admin
# instead of adding a second admin and a second flag note.
pw = open('/tmp/admin-password').read().strip()


class StaleBackend(Exception):
    pass


def seed():
    """Log in as admin through the proxy and add the flag note unless it's there.
    True once the admin's notes show the flag (the proxy decrypts them)."""
    s = Session()
    s.post(f"{url}/registerlogin",
           data={"username": "admin", "password": pw},
           allow_redirects=False, timeout=5).raise_for_status()
    notes = s.get(f"{url}/notes", allow_redirects=False, timeout=5).text
    if flag in notes:
        return True
    if 'MALFORMED ENCRYPT' in notes:
        raise StaleBackend()
    s.post(f"{url}/add_note",
           data={"title": "secret", "body": flag},
           allow_redirects=False, timeout=5).raise_for_status()
    return flag in s.get(f"{url}/notes", allow_redirects=False, timeout=5).text


# Retried until gunicorn and the backend answer (start.sh runs this alongside them).
for attempt in range(60):
    try:
        if seed():
            logger.info(f"admin's flag note is in place (admin password: {pw})")
            sys.exit(0)
    except StaleBackend:
        logger.error("noter5: the backend's admin notes were encrypted with another proxy key; "
                     "recreate both containers: ./ctf.sh reset noter5")
        sys.exit(1)
    except RequestException as e:
        logger.info(f"waiting for the proxy and backend ({e.__class__.__name__})")
    time.sleep(2)

logger.error(f"noter5: could not add the flag note through {url}; the challenge has no flag. "
             "Check ./ctf.sh logs noter5-backend, then ./ctf.sh reset noter5")
sys.exit(1)
