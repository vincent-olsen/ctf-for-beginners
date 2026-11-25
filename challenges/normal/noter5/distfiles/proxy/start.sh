#!/bin/sh

sleep 10 && python init.py &

gunicorn -w 8 -b "$BIND_ADDR:$PORT" --limit-request-field_size 0 --limit-request-line 0 --access-logfile - --error-logfile - app:app
