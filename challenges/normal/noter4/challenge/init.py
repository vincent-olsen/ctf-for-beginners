import uuid
import sqlite3
import hashlib

from logzero import logger

# make sure we have a secret for the app
try:
    SECRET = open('/tmp/secret', 'rb').read()
    logger.info(f'found secret file: {SECRET}')
except FileNotFoundError:
    SECRET = uuid.uuid4().bytes
    with open('/tmp/secret', 'wb') as f:
        f.write(SECRET)


# init database
with open('schema.sql', 'r') as f:
    db = sqlite3.connect('sqlite.db')
    db.cursor().executescript(f.read())
    db.commit()

    username = "admin"
    password = uuid.uuid4().hex
    pwhash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    logger.info(f"Creating new user {username} with password {password}")

    admin_uuid = uuid.uuid4().hex
    query = "insert into users (uuid, username, password) values (?, ?, ?)"
    args = [admin_uuid, username, pwhash]

    db.cursor().execute(query, args)
    db.commit()

    note_uuid = uuid.uuid4().hex
    title = "secret"
    body = "flag{inj3ct_me_d4ddy}"

    query = "insert into notes (uuid, user, title, body) values (?, ?, ?, ?)"
    args = [note_uuid, admin_uuid, title, body]

    db.cursor().execute(query, args)
    db.commit()
