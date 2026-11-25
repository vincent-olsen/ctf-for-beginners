### Decode Dash

Provided string

```
ZmxhZ3t0aDFzXzFzX3RoM19mbDRnX24wd30=
```

Here we recognise that it's ending in one equal sign, suggesting that it is base64 encoded. So we need to decode it.

`echo 'ZmxhZ3t0aDFzXzFzX3RoM19mbDRnX24wd30=' | base64 -d`

```
flag{th1s_1s_th3_fl4g_n0w}
```

## Debrief: what you learn and how to protect against it

**What you learn:** how to recognise base64 (letters, digits, `+` and `/`, often
ending in `=`), and that encoding is not encryption: there is no key, so anyone
can reverse it.

**The solve in short:**

1. Notice the `=` at the end and the base64 alphabet.
2. Decode it: `echo '...' | base64 -d` (or CyberChef, "From Base64").

**How to protect against it:**

- Never use base64 to "hide" a password or token. It turns up in real systems all
  the time: HTTP Basic auth headers, the payload of a JWT and Kubernetes Secrets
  are all just base64.
- When data has to be secret, encrypt it with a real cipher (AES-GCM,
  ChaCha20-Poly1305) from a standard library, keep the key somewhere else, and
  use TLS in transit.
