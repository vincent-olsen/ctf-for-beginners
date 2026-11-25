FROM python:3.14-alpine

RUN apk update
RUN apk add py-pip
RUN pip install flask==3.1.3 gunicorn==26.2.0 requests==2.34.2 logzero==1.7.0

ENV LIBRARY_PATH=/lib:/usr/lib

ADD . /app/
WORKDIR /app/

ENV PORT=5000
ENV BIND_ADDR=0.0.0.0

# Run unprivileged; the app files stay root's, so the app can't change them.
RUN adduser -D app
USER app

EXPOSE 5000

ENTRYPOINT gunicorn -w 8 -b "${BIND_ADDR}:${PORT}" --access-logfile - --error-logfile - app:app
