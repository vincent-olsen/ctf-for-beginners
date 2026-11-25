FROM python:3.14-alpine

RUN apk update
RUN apk add py-pip
RUN pip install flask==3.1.3 gunicorn==26.2.0

ADD . /app/
WORKDIR /app/

ENV PORT=5000
ENV BIND_ADDR=0.0.0.0
ENV DB_PATH=/tmp/noter.db

# The real flag; it is only ever stored in the secrets table, never rendered.
ENV FLAG=flag{union_select_your_way_in}

# Run unprivileged; the app files stay root's, so the app can't change them.
RUN adduser -D app
USER app

EXPOSE 5000

# --preload imports the app (and runs init_db) once in the master before the 8
# workers fork, so the DB is seeded exactly once — no per-worker DELETE/INSERT
# race that could serve a request while the secrets table is momentarily empty.
ENTRYPOINT gunicorn -w 8 --preload -b "${BIND_ADDR}:${PORT}" --access-logfile - --error-logfile - app:app
