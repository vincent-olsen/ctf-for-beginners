FROM python:3.14-alpine

RUN apk update
RUN apk add py-pip
RUN pip install flask==3.1.3 gunicorn==26.2.0

ADD . /app/
WORKDIR /app/

ENV PORT=5000
ENV BIND_ADDR=0.0.0.0

EXPOSE 5000

ENTRYPOINT gunicorn -w 8 -b "${BIND_ADDR}:${PORT}" --access-logfile - --error-logfile - app:app
