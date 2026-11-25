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
    con.row_factory = sqlite3.Row
    sql = "SELECT title, body FROM notes WHERE title LIKE '%" + q + "%'"
    results = []
    try:
        results = [(r["title"], r["body"]) for r in con.execute(sql).fetchall()]
    except Exception:
        # Swallow SQL errors: no query echo, no parser message. The injection is
        # still here (the query is built by string concatenation) and a working
        # UNION still renders its rows as notes, but a broken one only says "No
        # notes matched" - never an error handing you the query or the schema.
        # Work the UNION out by trial, not by reading the exception.
        results = []
    con.close()
    return render_template("results.html", q=q, results=results)


if __name__ == "__main__":
    app.run(host=os.environ.get("BIND_ADDR", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)))
