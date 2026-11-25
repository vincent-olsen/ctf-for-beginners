import os
import sqlite3

from flask import Flask, render_template, request

DB = os.environ.get("DB_PATH", "/tmp/noter.db")
FLAG = os.environ.get("FLAG", "flag{local_dev_flag}")

SEED_NOTES = [
    ("Welcome", "Search our public notes below. Staff notes are kept elsewhere."),
    ("Shopping", "milk, bread, a rubber duck for debugging"),
    ("TODO", "rotate the database credentials (again)"),
    ("Standup", "yesterday: shipped search. today: parameterise queries. blockers: none"),
]


def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, body TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS secrets (name TEXT, value TEXT)")
    if cur.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0:
        cur.executemany("INSERT INTO notes (title, body) VALUES (?, ?)", SEED_NOTES)
    # The flag lives only in the secrets table; nothing renders it directly.
    cur.execute("DELETE FROM secrets")
    cur.execute("INSERT INTO secrets (name, value) VALUES (?, ?)", ("flag", FLAG))
    con.commit()
    con.close()


app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    q = request.args.get("q", "")
    con = sqlite3.connect(DB)
    sql = "SELECT title, body FROM notes WHERE title LIKE '%" + q + "%'"
    # Blind on purpose: the page never prints the matched rows, only WHETHER any
    # row came back. The injection is still here (the query is built by string
    # concatenation, no escaping), but a UNION can no longer just render the
    # secret - it's a boolean oracle. Make the match depend on the secret and
    # extract it one character at a time. SQL errors are swallowed and read as
    # "no match", so a malformed payload looks false; craft valid SQL.
    matched = False
    try:
        matched = con.execute(sql).fetchone() is not None
    except Exception:
        matched = False
    con.close()
    return render_template("results.html", q=q, matched=matched)


if __name__ == "__main__":
    app.run(host=os.environ.get("BIND_ADDR", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)))
