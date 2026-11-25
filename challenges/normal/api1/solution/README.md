# api1 — reading the API docs

**Category:** web · **Flag:** `flag{th1s_1s_a_nic3_fl4g}`

A FastAPI service. The root page tells you where to look:

```bash
curl http://$HOST:$PORT/
```

> `"tip": "Check the auto-generated OpenAPI documentation at /docs or /openapi.json."`

FastAPI publishes a machine-readable description of every route at
`/openapi.json`. Fetch it to see the two flag endpoints:

```bash
curl http://$HOST:$PORT/openapi.json
```

- `GET /flags` lists the flags but hides their `value`.
- `GET /flags/{id}` returns one flag **with** its value.

List them and pick the real one (type `CTF`, icon `❓`; the others are `fake{...}`):

```bash
curl http://$HOST:$PORT/flags
```

It is id `5`:

```bash
curl http://$HOST:$PORT/flags/5
```

```json
{"id":5,"type":"CTF","icon":"❓","value":"flag{th1s_1s_a_nic3_fl4g}"}
```

**Lesson:** an API's own OpenAPI/Swagger docs (`/docs`, `/openapi.json`) spell out
every endpoint; `/flags` omits the value, but `/flags/{id}` hands it over.

## Debrief: what you learn and how to protect against it

**What you learn:** how to explore a REST API. Frameworks like FastAPI publish
their own documentation (`/docs`, `/openapi.json`) that lists every endpoint. You
also see a classic API mistake: the list endpoint hides the sensitive field, but
the endpoint for a single object returns it.

**The solve in short:**

1. `GET /` points to the docs.
2. `GET /openapi.json` shows `/flags` and `/flags/{id}`.
3. `GET /flags` lists the flags without values. The real one is id 5.
4. `GET /flags/5` returns it with the value.

**How to protect against it:**

- Require authentication and check authorisation on every endpoint, for every
  object. An endpoint is not private because nothing links to it.
- Decide which fields a client may see in one place (a response model) and use
  it on all endpoints, so the list and the detail view cannot disagree.
- Turn off or protect the interactive docs in production (in FastAPI:
  `docs_url=None, openapi_url=None`). This reduces what an attacker gets for
  free, but it is not the fix. In the OWASP API Security Top 10 this is broken
  authorisation (API1 and API3).
