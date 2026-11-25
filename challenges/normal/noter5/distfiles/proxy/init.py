import os
import uuid
from requests import Session


url = os.environ.get("PROXY_URL", "http://127.0.0.1:1024")
flag = "flag{REDACTED}"
pw = uuid.uuid4().hex


s = Session()

s.post(f"{url}/registerlogin",
       data={"username": "admin","password":pw},
       allow_redirects=False)

s.post(f"{url}/add_note",
       data={"title": "secret", "body":f"{flag}"},
       allow_redirects=False)

