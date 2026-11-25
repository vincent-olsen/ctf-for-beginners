from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from pydantic import BaseModel


app = FastAPI(
    title="FlagApiProvider",
    version="1.1.0",
    terms_of_service="https://go.wild.gg/terms",
    license_info={
        "name": "License v1.0",
        "url": "https://who-even.checksthe.url/license"
    }
)


with open('flag.txt', 'r') as file:
    FLAG = file.read().strip()


class Flag(BaseModel):
    id: int
    type: str
    icon: str
    value: str


flags = [
    Flag(id=0, icon="🏁", value="fake{th1s_1s_n0t_th3_fl4g}", type="CHECKER"),
    Flag(id=1, icon="🇳🇴", value="fake{def1n1tely_n0t_th3_fl4g}", type="NORWAY"),
    Flag(id=2, icon="☠️", value="fake{ju5t_anoth3r_ph0ny}", type="PIRATE"),
    Flag(id=3, icon="🚩", value="fake{n0t_th1s_0ne_either}", type="PENNON"),
    Flag(id=4, icon="🌈", value="fake{th1s_1s_n0t_th3_fl4g}", type="PRIDE"),
    Flag(id=5, icon="❓", value=FLAG, type="CTF"),
    Flag(id=6, icon="🏳️", value="fake{c4n_you_bel1eve_1ts_not_th3_fl4g}", type="WHITE"),
]


@app.get("/")
def root():
    return {
        "Greeting": "Welcome to the FlagApiProvider.",
        "current_endpoint": {
            "name": "root",
            "path": "/",
            "is_flag_here": False
        },
        "tip": "Check the auto-generated OpenAPI documentation at /docs or /openapi.json."
    }


#@app.get("/docs")
#def get_openapi_documentation():
#    return openapi.json


@app.get("/flags")
def list_flags():
    flags_without_value = [{
        "id": flag.id,
        "icon": flag.icon,
        "type": flag.type,
    } for flag in flags]

    return flags_without_value


@app.get("/flags/{id}", response_model=Flag)
def get_flag_info_by_id(id: int):
    for flag in flags:
        if flag.id == id:
            return flag

    raise HTTPException(status_code=404, detail="Flag not found")


@app.middleware("http")
async def add_custom_header(request: Request, call_next):
    """Adds a custom header. Just for lættis."""
    response: Response = await call_next(request)
    response.headers["api-name"] = "FlagApiProvider"
    response.headers["cool-api"] = "True"
    return response

