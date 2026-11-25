import base64
import requests
from functools import wraps
from threading import Thread

from logzero import logger
from flask import Flask, render_template, url_for, request, Response, \
    redirect, send_from_directory, make_response


app = Flask(__name__)
logger.info("Starting application.")


@app.route('/')
def index():

    template = render_template('notes.html',
                               admin=isAdmin(request),
                               flag=getFlag(request)
                               )

    resp = make_response(template)

    if not haveCookies(request):
        resp.set_cookie('isAdmin',"0")
        resp.set_cookie('user', base64.b64encode("anon".encode()).decode())

    return resp


def haveCookies(request):
	if 'isAdmin' in request.cookies and 'user' in request.cookies:
		return True
	else:
		return False


def isAdmin(request):
	if not 'isAdmin' in request.cookies or not 'user' in request.cookies:
		return False

	if not request.cookies.get('isAdmin') == "1":
		return False

	admin_encoded = base64.b64encode(b"admin").decode()
	if not request.cookies.get('user') == admin_encoded:
		return False

	return True


def getFlag(request):
	if isAdmin(request):
		return "flag{im_the_adm1n_n0w}"
	else:
		return ""


@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='favicon.ico')
