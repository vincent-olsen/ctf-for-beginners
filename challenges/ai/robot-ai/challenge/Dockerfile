FROM python:3.14-alpine

RUN apk update
RUN apk add py-pip
RUN pip install flask==3.1.3 gunicorn==26.2.0

ADD . /app/
WORKDIR /app/

ENV PORT=5000
ENV BIND_ADDR=0.0.0.0

# The real flag and a strong, non-guessable signing secret. The intended solve
# does NOT need the secret (it abuses alg:none), so a long random secret is fine.
ENV FLAG=flag{alg_n0ne_lets_any_r0bot_in}
ENV JWT_SECRET=8f2c1e6b9a47d035c1fe7742aa90b3d5e6c8f1029b4a7d6e3f5c0b1a2d9e8f7c

# Run unprivileged; the app files stay root's, so the app can't change them.
RUN adduser -D app
USER app

EXPOSE 5000

ENTRYPOINT gunicorn -w 8 -b "${BIND_ADDR}:${PORT}" --access-logfile - --error-logfile - app:app
