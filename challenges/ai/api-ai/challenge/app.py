import secrets

from fastapi import Body, FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Noteworthy API",
    version="3.0.0",
    description=(
        "A small notes API. Explore it at /docs or /openapi.json. "
        "The flag lives behind an admin-only endpoint — and we locked down the "
        "obvious ways in this time."
    ),
)

# Cosmetic only: the AI-modus look for browsers (skin.py sits next to app.py on
# the server; without it the API behaves exactly the same).
try:
    import skin
except ImportError:
    skin = None
if skin:
    skin.install(app)

with open("flag.txt") as fh:
    FLAG = fh.read().strip()

# The permission the admin endpoint checks for.
ADMIN_PERMISSION = "noteworthy:admin"

# Fields a client can't set through PATCH /api/me.
PROTECTED_FIELDS = {"username", "password", "role", "is_admin"}

# In-memory stores (reset on restart; fine for a challenge).
users: dict[str, dict] = {}
tokens: dict[str, str] = {}


class RegisterIn(BaseModel):
    # v3: registration takes a username and a password, nothing else.
    username: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


def _auth(authorization: str | None):
    token = (authorization or "").removeprefix("Bearer ").strip()
    username = tokens.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="missing or invalid token")
    return username, users[username]


@app.get("/")
def root():
    return {
        "service": "Noteworthy API",
        "docs": "/docs",
    }


@app.post("/api/register")
def register(body: RegisterIn):
    if body.username in users:
        raise HTTPException(status_code=409, detail="username taken")
    # New accounts get the ordinary scopes in the noteworthy:* namespace. The
    # admin scope that /api/admin/flag checks for is deliberately NOT named
    # anywhere in the API — a player has to infer it from this visible pattern
    # (read/write -> admin) and mass-assign it via PATCH /api/me.
    default_perms = ["noteworthy:read", "noteworthy:write"]
    users[body.username] = {
        "password": body.password,
        "role": "user",
        "permissions": list(default_perms),
    }
    token = secrets.token_hex(16)
    tokens[token] = body.username
    return {"token": token, "role": "user", "permissions": list(default_perms)}


@app.post("/api/login")
def login(body: LoginIn):
    u = users.get(body.username)
    if not u or u["password"] != body.password:
        raise HTTPException(status_code=401, detail="bad credentials")
    token = secrets.token_hex(16)
    tokens[token] = body.username
    return {"token": token}


@app.get("/api/me")
def me(authorization: str | None = Header(default=None)):
    username, info = _auth(authorization)
    return {"username": username, "role": info["role"], "permissions": info["permissions"]}


@app.patch("/api/me")
def update_me(
    authorization: str | None = Header(default=None),
    body: dict = Body(..., examples=[{"display_name": "Ada"}]),
):
    """Update your profile."""
    username, info = _auth(authorization)
    for key in body:
        if key in ("role", "is_admin"):
            raise HTTPException(status_code=400, detail=f"'{key}' is read-only")
    for key, value in body.items():
        if key in PROTECTED_FIELDS:
            continue
        info[key] = value
    return {"username": username, "role": info["role"], "permissions": info["permissions"]}


@app.get(
    "/api/admin/flag",
    description="Admin only. Returns the flag to accounts with administrative access.",
)
def admin_flag(authorization: str | None = Header(default=None)):
    _username, info = _auth(authorization)
    if ADMIN_PERMISSION not in info.get("permissions", []):
        raise HTTPException(status_code=403, detail="insufficient permissions")
    return {"flag": FLAG}
