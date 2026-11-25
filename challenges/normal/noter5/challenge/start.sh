#!/bin/sh

# The AES key and the admin password: derived from NOTER5_SECRET when ctf.sh passes
# it (kept per deployment in .ctf/noter5-secret), so every build and recreate of
# this proxy matches the notes the backend holds; without it, the ones made at build.
if [ -n "${NOTER5_SECRET:-}" ]; then
  python -c "import hashlib, os
s = os.environ['NOTER5_SECRET'].encode()
open('/tmp/secret', 'wb').write(hashlib.sha256(b'noter5-key:' + s).digest()[:16])
open('/tmp/admin-password', 'w').write(hashlib.sha256(b'noter5-admin:' + s).hexdigest()[:32])"
fi

# Seeds the flag through the proxy once it answers (init.py retries).
python init.py &

gunicorn -w 8 -b "$BIND_ADDR:$PORT" --limit-request-field_size 0 --limit-request-line 0 --access-logfile - --error-logfile - app:app
