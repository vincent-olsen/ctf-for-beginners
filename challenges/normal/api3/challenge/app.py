from time import time
from typing import Dict
from random import randint
from secrets import token_hex
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import APIKeyHeader


FLAG = "flag{scr1pt_g0es_brrrrr}"

TIMEOUT_IN_MILLIS = 3000  # in millis
# An expired key is only dropped this long after it expired, so a player who comes
# back with it by hand still gets the 408 "expire in 3 seconds" message (the clue).
PRUNE_AFTER_MILLIS = 10 * 60 * 1000


app = FastAPI(
    title="FlagApiProvider",
    version="3.1.1",
    docs_url=None,
    #redoc_url=None
)


@dataclass
class ApiKeyTracker:
    expiration_time: int
    call_counter: int
    solved: bool = False


# simple database
db: Dict[str, ApiKeyTracker] = {}

header_scheme = APIKeyHeader(name="Authorization", auto_error=False)


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui_html():
    return {
        "eyyy": "This be gone now",
        "reason": "change of scenery I suppose",
        "try": "/redoc"
    }


@app.get("/")
def root():
    return {
        "details": "Only two endpoints this time. Should be easy enough.",
        "next": "/key",
        "tip": "███ ████ █████",
    }


@app.get("/key", summary="Generate API key")
def get_apikey():
    api_key = token_hex(24)
    time_in_millis = int(time() * 1000)
    expires_at = int(time_in_millis + TIMEOUT_IN_MILLIS)

    # Keys live for 3 seconds. Drop long-expired, unsolved keys so hammering /key
    # (the intended solve, and any flood) can't grow this dict without bound.
    # Solved keys are kept so a replay still gets the "script goes brrr" easter egg.
    # This endpoint runs in a thread pool: list() snapshots the dict in one step
    # (another request may insert meanwhile), and pop() tolerates a key another
    # request already dropped.
    cutoff = time_in_millis - PRUNE_AFTER_MILLIS
    for k, v in list(db.items()):
        if not v.solved and v.expiration_time < cutoff:
            db.pop(k, None)

    db[api_key] = ApiKeyTracker(expiration_time=expires_at, call_counter=0)

    return {
        "api_key": api_key,
        "type": "Bearer",
        "added_at": time_in_millis,
        "next": "/flag"
    }


@app.get("/flag")
def get_flag(auth_header: str = Depends(header_scheme)):
    current_time = int(time() * 1000)

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required. Use Authorization: Bearer <api_key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not "Bearer" in auth_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Authorization scheme. Expected Authorization: Bearer <api_key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    header_parts = auth_header.split(" ")  # Bearer 50a93e44656f0d7ff8c1c07a4220d66b244e26595be4b6

    if len(header_parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Authorization header. Usage: Authorization: Bearer <api_key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = header_parts[-1]

    if not api_key in db:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key. Get yourself a fresh one at /key"
        )

    key: ApiKeyTracker = db[api_key]
    key.call_counter += 1

    if key.solved:
        return {"script_goes": "b" + "r" * randint(3,7)}

    if key.expiration_time < current_time:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Error. The API key has expired. At FlagApiProvider we take security very seriously, so the keys expire in 3 seconds haha"
        )

    if key.call_counter == 1:
        return {
            "detail": "Great! The API key is fresh as a daisy. We just need to verify it a couple of more times.. juuust to be sure.",
            "count": key.call_counter,
            "time_left": f"{key.expiration_time - current_time} ms"
        }

    if key.call_counter == 2:
        return {
            "detail": "Almost there, just need to verify ooone more time",
            "count": key.call_counter,
            "time_left": f"{key.expiration_time - current_time} ms"
        }


    key.solved = True

    return {
        "yay": "🎉🎉🎉🎉🎉🎉",
        "time_left": f"{key.expiration_time - current_time} ms",
        "here_you_go": FLAG
    }

