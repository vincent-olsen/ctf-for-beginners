import re

from fastapi import FastAPI, HTTPException, Header, Body, Query


app = FastAPI(
    title="FlagApiProvider",
    version="2.0.5"
)


with open('flag.txt', 'r') as file:
    FLAG = file.read().strip()


@app.get("/")
def root():
    return {
        "haiku": "Many routes await. In the end the point unfold. Good luck traveler.",
        "next": "Every great accomplishment starts with a /first_step",
    }


@app.get("/first_step", summary="Use a query parameter")
def query_with_parameter(answer: int = Query(None)):
    if answer is None:
        raise HTTPException(
            status_code=400,
            detail="Missing query parameter: answer. The question is: what is the Answer to the Ultimate Question of Life, the Universe, and Everything?",
        )
    if answer != 42:
        raise HTTPException(status_code=422, detail="Wrong Answer to the Ultimate Question of Life, the Universe, and Everything")

    return {
        "details": "This was kind of a training step. Next one is where the magic happens.",
        "next": "/curl_me",
    }


@app.get("/curl_me", summary="Use curl")
def curl_me(user_agent: str = Header(include_in_schema=False)):
    if not user_agent:
        raise HTTPException(status_code=400, detail="Missing User-Agent header. How are you calling this bro")

    if "postman" in user_agent.lower():
            raise HTTPException(status_code=400, detail="Postman is a great tool! At this endpoint, however, curl is required.")

    browsers = ["firefox", "chrome", "safari", "mozilla", "applewebkit", "android"]
    if any(browser in user_agent.lower() for browser in browsers) or "curl" not in user_agent.lower():
        raise HTTPException(status_code=400, detail="This endpoint requires you to use curl. Try running 'curl $URL/curl_me' from a terminal.")

    if not user_agent.lower().startswith("curl/"):
        raise HTTPException(status_code=400, detail="No no, you actually have to use curl on this one. Nice try tho.")

    # check for version (e.g curl/7.81.0)
    if not re.match(r"^curl/\d+\.\d+\.\d+$", user_agent.lower()):
        raise HTTPException(status_code=400, detail="Thats a weird curl you got there bro. Which version is this")

    return {
        "description": "With the power of curl, you are one step closer to being a wizard",
        "next": {
            "endpoint": "/header",
            "value": "let_me_in"
        }
    }


@app.get("/header", summary="Add secret header")
def get_next_step_with_secret_header(x_secret: str = Header(None)):
    if not x_secret:
        raise HTTPException(status_code=400, detail="Missing X-Secret header")
    if x_secret != "let_me_in":
        raise HTTPException(status_code=403, detail="Invalid X-Secret header. See /curl_me.")

    return {
        "progress": "almost there",
        "next": "/flag"
    }


@app.get("/flag")
def get_flag(x_secret: str = Header(None), secret: str = Query(None)):
    if x_secret != "let_me_in":
        # har alltid hatt lyst til å bruke den statuskoden her, yay
        raise HTTPException(status_code=418, detail="This is not the route you are looking for.. yet. Only true travelers can get the flag." )
    if not secret:
        raise HTTPException(status_code=400, detail="Missing query parameter: secret")
    if secret != "9cd8c3a0-19b4-4d32-b12a-fa886fa6e5a8":
        raise HTTPException(status_code=422, detail="Wrong value for secret. See /token")

    return {"finally": FLAG}


@app.post("/token")
def get_token_with_password(password: str = Body(..., embed=True)):
    if password != "ctfhacks":
        raise HTTPException(status_code=403, detail="Wrong password. Must start with 'ctf' and end with 'hacks'.")
    return {"token": "9cd8c3a0-19b4-4d32-b12a-fa886fa6e5a8"}
