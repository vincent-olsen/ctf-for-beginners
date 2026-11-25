The web application now has some "authentication".
However, there is no login page.

Since the authentication is done on the client side,
we should inspect the page. This can be done with burpsuite,
or simply in the browser.

After looking around, we notice some suspicious cookies:

```yaml
isAdmin: 0
user: YW5vbg==
```

We can easily change the cookie `isAdmin` to 1, since this
is all client side.

The user `YW5vbg==` looks like a base64 encoded string.
By decoding it, we get `anon`. We don't want to be "anon",
we want to be admin. Let's change this to a base64 encoded
string containing `admin` instead:

```
echo -n "admin" | base64
YWRtaW4=
```

Now we have everything we need to "become the admin".
In Firefox, we use the "storage" tab in the DevTool (F12)
to change the cookies.

```yaml
isAdmin: 1
user: YWRtaW4=
```

Simply reload the page and the flag is revealed in the `secret` note.

## Debrief: what you learn and how to protect against it

**What you learn:** cookies are stored in the browser, so the user can change
them. This app decides who is admin from two cookies (`isAdmin=0` and a
base64-encoded user name), which means the user decides. You also meet base64
again: it hides nothing.

**The solve in short:**

1. Open the developer tools (F12) and look at the cookies: `isAdmin: 0` and
   `user: YW5vbg==`.
2. Base64-decode `YW5vbg==`: it is `anon`.
3. Set `isAdmin` to `1` and `user` to the base64 of `admin` (`YWRtaW4=`).
4. Reload the page. The `secret` note with the flag appears.

**How to protect against it:**

- Never trust anything the client sends when deciding who the user is or what
  they may do. Keep the role on the server, in a session looked up by a random
  session id.
- If the state must live in a cookie, sign it (Flask's session cookie, or a JWT
  whose signature is verified) so a changed value is rejected.
- Check authorisation on the server for every request.
- `HttpOnly`, `Secure` and `SameSite` are good cookie flags, but they protect
  against theft by others. They do not stop the owner of the browser from
  editing a cookie.
