FROM python:3.14-alpine

RUN apk update
RUN apk add py-pip gmp python3-dev gcc g++ make libffi-dev openssl-dev
RUN pip install flask==3.1.3 gunicorn==26.2.0 requests==2.34.2 pycryptodome==3.24.0 logzero==1.7.0
ENV LIBRARY_PATH=/lib:/usr/lib

ADD . /app/
WORKDIR /app/

# One AES key for all gunicorn workers (app.py only creates one when this is missing)
# and the admin password init.py logs in with, random per build. Under ctf.sh,
# start.sh writes both from NOTER5_SECRET (one per deployment, in .ctf/) instead, so
# a rebuilt or recreated proxy still matches the backend, whose DB outlives it: a
# new password would add a second "admin" (the backend allows duplicate usernames),
# a new key leaves the notes it holds unreadable (the "MALFORMED ENCRYPT" the
# writeup warns about). Nothing secret is committed to the repo.
RUN python -c "import os; open('/tmp/secret', 'wb').write(os.urandom(16)); open('/tmp/admin-password', 'w').write(os.urandom(16).hex())"

ENV PORT=1024 BIND_ADDR=0.0.0.0

# Empty means the compose setup (backend at http://app:5000/); override the build
# arg, or the BACKEND_URL env var at runtime, if the backend is reached elsewhere.
ARG BACKEND_URL=
ENV BACKEND_URL=${BACKEND_URL}

EXPOSE 1024

ENTRYPOINT /app/start.sh
