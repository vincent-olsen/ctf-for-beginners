import base64
import hashlib
import hmac
import json
import os

from flask import Flask, make_response, render_template, request, send_from_directory

app = Flask(__name__, static_folder="static")

# Set in the Dockerfile / environment, never hard-coded here.
FLAG = os.environ.get("FLAG", "flag{local_dev_flag}")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me").encode()


# --- a tiny JWT implementation (HS256) -------------------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def issue_token(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(JWT_SECRET, f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def verify_token(token: str):
    """Return the payload if the token is valid, else None."""
    try:
        h, p, s = token.split(".")
        header = json.loads(_b64url_decode(h))
        payload = json.loads(_b64url_decode(p))
    except Exception:
        return None

    alg = header.get("alg", "")
    if alg == "none":
        return payload
    if alg == "HS256":
        expected = hmac.new(JWT_SECRET, f"{h}.{p}".encode(), hashlib.sha256).digest()
        if hmac.compare_digest(_b64url(expected), s):
            return payload
    return None


# --- routes -----------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/robots.txt")
def robots():
    return send_from_directory(app.static_folder, "robots.txt")


@app.route("/diagnostics")
def diagnostics():
    token = request.cookies.get("marvin_session")
    payload = verify_token(token) if token else None
    if payload is None:
        # Hand out a fresh guest badge.
        payload = {"role": "guest", "user": "visitor"}
        resp = make_response(render_template("diagnostics.html", role=payload["role"]))
        resp.set_cookie("marvin_session", issue_token(payload))
        return resp
    return render_template("diagnostics.html", role=payload.get("role", "guest"))


@app.route("/admin")
def admin():
    token = request.cookies.get("marvin_session")
    payload = verify_token(token) if token else None
    if payload and payload.get("role") == "admin":
        return render_template("admin.html", flag=FLAG)
    return render_template("denied.html"), 403


if __name__ == "__main__":
    app.run(host=os.environ.get("BIND_ADDR", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)))
