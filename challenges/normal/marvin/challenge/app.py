from flask import Flask, render_template, send_from_directory

app = Flask(__name__, static_folder='static')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')


@app.route('/secret')
def secret():
    return render_template('secret.html')
