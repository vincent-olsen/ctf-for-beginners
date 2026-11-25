# api2 — follow the trail of endpoints

**Category:** web · **Flag:** `flag{h0w_wa5_th3_r0ute_tr4veler}`

Each endpoint names the next one. Set `URL` to the challenge, e.g.
`URL=http://$HOST:$PORT`, and walk the chain:

1. **Root** points at the first step:

   ```bash
   curl "$URL/"
   # "next": "Every great accomplishment starts with a /first_step"
   ```

2. **`/first_step`** wants a query parameter called `answer`. Without it, the error
   asks the question: "what is the Answer to the Ultimate Question of Life, the
   Universe, and Everything?" That's from *The Hitchhiker's Guide to the Galaxy*,
   and the answer is 42:

   ```bash
   curl "$URL/first_step?answer=42"
   # "next": "/curl_me"
   ```

3. **`/curl_me`** checks the `User-Agent`: it must be real `curl` (e.g.
   `curl/8.4.0`), not a browser or Postman. Plain `curl` already sends that, so:

   ```bash
   curl "$URL/curl_me"
   # "next": {"endpoint": "/header", "value": "let_me_in"}
   ```

   (On Windows PowerShell, `curl` is an alias for `Invoke-WebRequest`; use
   `curl.exe` instead.)

4. **`/header`** needs that value in an `X-Secret` header:

   ```bash
   curl "$URL/header" -H "X-Secret: let_me_in"
   # "next": "/flag"
   ```

5. **`/flag`** needs both the `X-Secret` header *and* a `secret` query parameter,
   and it points at `/token` for the value. Get the token first (it's a POST with
   a JSON body; the password "must start with 'ctf' and end with 'hacks'"):

   ```bash
   curl -X POST "$URL/token" -H 'Content-Type: application/json' -d '{"password":"ctfhacks"}'
   # {"token": "9cd8c3a0-19b4-4d32-b12a-fa886fa6e5a8"}
   ```

6. Use the token as `secret`, with the header:

   ```bash
   curl "$URL/flag?secret=9cd8c3a0-19b4-4d32-b12a-fa886fa6e5a8" -H "X-Secret: let_me_in"
   # {"finally": "flag{h0w_wa5_th3_r0ute_tr4veler}"}
   ```

**Lesson:** APIs drive behaviour from query parameters, headers, HTTP methods and
request bodies — read each error message; it tells you exactly what the next call
needs.

## Debrief: what you learn and how to protect against it

**What you learn:** the parts an HTTP request is made of, and how to set each one
with `curl`: query parameters, headers, the `User-Agent`, the method (`POST`) and
a JSON body. And to read error messages, because they say what the server wants
next.

**The solve in short:**

1. `GET /` points to `/first_step`.
2. `/first_step?answer=42` (the error message asks the question) points to
   `/curl_me`.
3. `/curl_me` with curl's own `User-Agent` gives a header name and a value.
4. `/header` with `X-Secret: let_me_in` points to `/flag`, which also needs a
   token.
5. `POST /token` with `{"password":"ctfhacks"}` gives the token.
6. `/flag?secret=<token>` with the `X-Secret` header returns the flag.

**How to protect against it:**

- Everything in a request is chosen by the client. A `User-Agent` check or a
  custom header is not access control, since anyone can send any value.
- Error messages that explain exactly what is missing help an attacker as much
  as a developer. Give clients a generic error and put the details in the server
  log.
- Use real authentication: a token tied to one user, issued after a real login,
  with an expiry. A password the API describes in its own error message is not a
  secret.
