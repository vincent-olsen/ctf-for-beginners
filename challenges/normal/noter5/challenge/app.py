import os
import re
import time
import uuid
import hmac
import base64
import socket
import asyncio
import hashlib
import sqlite3
import binascii
import requests

from logzero import logger
from datetime import datetime
from functools import wraps
from urllib.parse import unquote

from Crypto.Cipher import AES
from threading import Thread
from flask import Flask, make_response, render_template, g, url_for, request, Response, copy_current_request_context, jsonify


try:
    SECRET = open('/tmp/secret', 'rb').read()
except FileNotFoundError:
    SECRET = uuid.uuid4().bytes
    with open('/tmp/secret', 'wb') as f:
        f.write(SECRET)

# Defaults to the compose backend; override with the BACKEND_URL env var if elsewhere.
BACKEND_URL = os.environ.get("BACKEND_URL") or "http://app:5000/"

app = Flask(__name__)
# Cap request bodies so one player can't fill the container's disk with giant
# notes (bodies are proxied to the backend and logged to /activity, ~4x each).
# 64 KB is far more than any note or the intended solve needs.
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024


def decrypt(val):
    encrypted = base64.b64decode(val[10:].encode())
    b64_nonce, b64_ciphertext, b64_tag = encrypted.split(b':')
    nonce = base64.b64decode(b64_nonce)
    ciphertext = base64.b64decode(b64_ciphertext)
    tag = base64.b64decode(b64_tag)
    cipher = AES.new(SECRET, AES.MODE_EAX, nonce)
    data = cipher.decrypt_and_verify(ciphertext, tag)
    return data


def encrypt(val):
    cipher = AES.new(SECRET, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(val.encode())
    encrypted = f'{base64.b64encode(cipher.nonce).decode()}:{base64.b64encode(ciphertext).decode()}:{base64.b64encode(tag).decode()}'
    b64 = base64.b64encode(encrypted.encode()).decode()
    return f'ENCRYPTED:{b64}'


def encrypt_params(param):
    # We don't want to encrypt identifiers.
    # This is a default set of typical ID values.
    IGNORE = ['uuid', 'id', 'pk', 'username', 'password']
    encrypted_param = {}
    for key in param:
        val = param.get(key,'')
        if key in IGNORE:
            encrypted_param[key] = val
        else:
            encrypted_param[key] = encrypt(val)
    
    return encrypted_param


def decrypt_data(data):
    encrypted_content = re.findall(rb'ENCRYPTED:[A-Za-z0-9+/]+=*', data)
    for encrypted in encrypted_content:
        try:
            data = data.replace(encrypted, decrypt(encrypted.decode()))
        except ValueError:  # bad base64, wrong number of parts, or a failed MAC check
            data = data.replace(encrypted, b'MALFORMED ENCRYPT')

    return data


def inject_ad(data):
    AD = b"""
        <div class="opacity-90 shadow-md w-full md:w-1/2 m-auto mt-10 mb-10 bg-blue-300 px-5 py-5 rounded rounded-xl flex flex-row ">
            <div class="ml-5">
                <i class="text-white text-4xl fas fa-user-shield"></i>
            </div>
            <div class="flex-grow ml-5 text-center">
                Data is encrypted with <span class="font-bold">AwesomeEncryptionService</span><br>
            </div>
        </div>
    </body>"""
    return data.replace(b'</body>', AD)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['POST', 'GET'])
def proxy(path):
    # contact backend server
    proxy_request = None
    query = request.query_string.decode()
    headers = {'Cookie': request.headers.get('Cookie', None) }

    if request.method=='GET':
        proxy_request = requests.get(f'{BACKEND_URL}{path}?{query}',
                            headers=headers,
                            allow_redirects=False)
    elif request.method=='POST':
        headers['Content-type'] = request.content_type
        proxy_request = requests.post(f'{BACKEND_URL}{path}?{query}', 
                            data=encrypt_params(request.form),
                            headers=headers,
                            allow_redirects=False)
    
    if not proxy_request:
        return 'error'
    
    response_data = decrypt_data(proxy_request.content)
    injected_data = inject_ad(response_data)
    resp = make_response(injected_data)
    resp.status = proxy_request.status_code

    if proxy_request.headers.get('Location', None):
        resp.headers['Location'] = proxy_request.headers.get('Location')
    if proxy_request.headers.get('Set-Cookie', None):
        resp.headers['Set-Cookie'] = proxy_request.headers.get('Set-Cookie')
    if proxy_request.headers.get('Content-Type', None):
        resp.content_type = proxy_request.headers.get('Content-Type')

    return resp
