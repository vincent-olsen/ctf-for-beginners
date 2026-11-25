FROM python:3.14-alpine

RUN apk update
RUN apk add py-pip gmp python3-dev gcc g++ make libffi-dev openssl-dev
RUN pip install flask==3.1.3 gunicorn==26.2.0 requests==2.34.2 pycryptodome==3.24.0 logzero==1.7.0
ENV LIBRARY_PATH=/lib:/usr/lib

ADD . /app/
WORKDIR /app/

ENV PORT=5000 BIND_ADDR=0.0.0.0
EXPOSE 5000

RUN python init.py
ENTRYPOINT gunicorn -w 8 -b "${BIND_ADDR}:${PORT}" --access-logfile - --error-logfile - app:app
