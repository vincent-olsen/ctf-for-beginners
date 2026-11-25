from logzero import logger
from functools import wraps
from threading import Thread
from flask import Flask, render_template, g, url_for, request, Response

app = Flask(__name__)
logger.info("Starting application.")


@app.route('/')
def index():
    return render_template('notes.html')

@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='favicon.ico')
