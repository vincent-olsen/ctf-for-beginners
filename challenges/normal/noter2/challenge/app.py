from logzero import logger
from functools import wraps
from threading import Thread
from flask import Flask, render_template, url_for, request, Response, redirect, send_from_directory

app = Flask(__name__, static_folder='static')
logger.info("Starting application.")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/notes')
def notes():
    return render_template('notes.html')


@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')


@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='favicon.ico')
