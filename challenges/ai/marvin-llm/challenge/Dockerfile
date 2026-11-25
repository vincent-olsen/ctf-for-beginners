FROM python:3.14-alpine

RUN apk update
RUN apk add py-pip
RUN pip install flask==3.1.3 gunicorn==26.2.0

ADD . /app/
WORKDIR /app/

ENV PORT=5000
ENV BIND_ADDR=0.0.0.0

# The real flag lives only here (and in Marvin's memory at runtime), never in the
# source. There is no source distfile for this one — it's black-box.
ENV FLAG=flag{encode_around_the_output_filter}

# Signs the session cookie that carries the conversation's state. It is an
# environment variable, not something made up at start, so that all gunicorn
# workers (and every event) use the same one. Knowing it buys a player nothing
# that one message to Marvin does not: it only vouches for "he is in a frame".
ENV SESSION_SEED=3cfeedc67675ba57f58a78d798ac04f4b13f2bde68089616ae0ac31b08d9e35c

# Run unprivileged; the app files stay root's, so the app can't change them.
RUN adduser -D app
USER app

EXPOSE 5000

ENTRYPOINT gunicorn -w 8 -b "${BIND_ADDR}:${PORT}" --access-logfile - --error-logfile - app:app
