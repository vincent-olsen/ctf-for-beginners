import hashlib
import hmac
import uuid
from logzero import logger
from functools import wraps
import sqlite3
from flask import Flask, render_template, g, request, Response


SECRET = open('/tmp/secret', 'rb').read()

DATABASE = 'sqlite.db'
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
# Cap request bodies so one player can't fill the container's disk with giant
# notes. 64 KB is far more than any note (or the intended SQLi payload) needs.
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024



def redirect(location):
    """drop-in replacement for flask's redirect that doesn't sanitize the redirect target URL"""
    response = Response(f'Redirecting... to {location}', 302, mimetype="text/html")
    response.headers["Location"] = location
    response.headers["Content-Type"] = 'text/plain'
    response.autocorrect_location_header = False
    return response


def signature(s):
    """generate a hmac signature for a given string"""

    m = hmac.new(SECRET, digestmod=hashlib.sha256)
    m.update(s.encode('ascii'))
    return m.hexdigest()


def get_db():
    """helper function to get a sqlite database connection"""

    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)

    db.row_factory = sqlite3.Row

    return db


@app.teardown_appcontext
def close_connection(exception):
    """helper function to close the database connection"""

    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), get_first=False):
    """Helper function to execute a SQL query like SELECT"""

    cur = get_db().execute(query, args)
    result = cur.fetchall()
    cur.close()

    if not result:
        return None

    if get_first:
        return result[0]

    return result


def commit_db(query, args=()):
    """helper function to do SQl queries like insert into"""

    get_db().cursor().execute(query, args)
    get_db().commit()


def login_required(f):
    """login required decorator to ensure g.user exists"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in g or g.user == None:
            return redirect('/logout')
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def before_request():
    """session middleware. checks if we have a valid session and sets g.user"""

    # request - flask.request
    if 'noter4_session' not in request.cookies:
        return None

    session = request.cookies['noter4_session'].split('.')
    if not len(session) == 2:
        return None

    key, sig = session
    if not hmac.compare_digest(sig, signature(key)):
        return None

    g.user= query_db('select * from users where uuid = ?', [key], get_first=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/logout')
def logout():
    response = redirect("/")
    response.set_cookie('noter4_session', '', expires=0)
    return response


@app.route('/notes')
@login_required
def notes():
    order = request.args.get('order', 'desc')
    rows = query_db(f'select * from notes where user = ? order by timestamp {order}', [g.user['uuid']])
    notes = rows or []
    return render_template('notes.html', user=g.user, notes=notes)


def admin_readonly(f):
    """every player who solves the challenge shares the admin account, so its notes
    (the flag) stay as they are for the next player"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user['username'] == 'admin':
            return redirect('/notes')
        return f(*args, **kwargs)

    return decorated_function


@app.route('/delete_note', methods=['POST'])
@login_required
@admin_readonly
def delete_note():
    user = g.user['uuid']
    note_uuid = request.form['uuid']
    commit_db('delete from notes where uuid = ? and user = ?', [note_uuid, user])
    return redirect(f'/notes?deleted={note_uuid}')


@app.route('/add_note', methods=['POST'])
@login_required
@admin_readonly
def add_note():
    new_note_uuid = uuid.uuid4().hex
    user = g.user['uuid']
    title = request.form['title']
    body = request.form['body']

    commit_db('insert into notes (uuid, user, title, body) values (?, ?, ?, ?)',
        [new_note_uuid, user, title, body])
    return redirect('/notes')


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    pwhash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    # check if username exists
    existing = query_db('select * from users where username = ?', [username], get_first=True)
    if existing:
        return redirect('/?error=Username+already+exists')

    new_user_uuid = uuid.uuid4().hex
    commit_db('insert into users (uuid, username, password) values (?, ?, ?)',
              [new_user_uuid, username, pwhash])
    user = query_db('select * from users where uuid = ?', [new_user_uuid], get_first=True)

    if not user:
        return redirect('/?error=Username+already+exists')

    # create session cookie
    assert isinstance(user, sqlite3.Row)
    key = user['uuid']
    sig = signature(key)
    response = redirect('/notes')
    response.set_cookie('noter4_session', f'{key}.{sig}')
    return response


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    pwhash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    user = query_db("select * from users where username = '%s' and password = '%s'" % (username, pwhash), get_first=True)

    if not user:
        existing = query_db('select * from users where username = ?', [username], get_first=True)
        if existing:
            return redirect('/?error=Invalid+password')
        return redirect('/?error=User+does+not+exist')

    assert isinstance(user, sqlite3.Row)
    key = user['uuid']
    sig = signature(key)
    response = redirect('/notes')
    response.set_cookie('noter4_session', f'{key}.{sig}')
    return response
