# noter5 — make the server decrypt the flag for you

**Category:** web · **Flag:** `flag{hi_my_n4me_i5_h4ckerman}`

Same notes app as noter4, but with a banner: *"Data is encrypted with
AwesomeEncryptionService"*, and it is two services — a **proxy** (the one you reach)
in front of a **backend**. The proxy encrypts note bodies with AES before storing
them in the backend, and decrypts any `ENCRYPTED:...` blob it finds in a response.
Both sources are attached (white-box).

### 1. Find the encrypted flag

Register any account and open `/activity`. The first entry is the admin creating a
note that contains the flag. The log base64-wraps the stored content (so the proxy
does *not* decrypt it in place). Base64-decode that blob and you get the encrypted
flag note:

```
ENCRYPTED:<nonce>:<ciphertext>:<tag>
```

AES with a key you don't have — cracking it directly is hopeless.

### 2. Let the proxy decrypt it for you

The trick: you don't need the key, because the proxy decrypts `ENCRYPTED:...` blobs
on the way *out*. Reading `encrypt_params` in the proxy source shows it encrypts
every submitted field **except** a few identifiers — `username` is on that
do-not-encrypt list. So:

- Register a new account whose **username is the encrypted flag blob** (`ENCRYPTED:...`).
  The proxy passes the username through unchanged, and the backend stores it verbatim.
- Load a page that shows your username (the notes page / the top-left corner). On the
  way back, the proxy spots the `ENCRYPTED:...` in your username and decrypts it — so
  your displayed username *is* the flag.

### Automated

`solution.py` does all of it against the proxy URL:

```bash
python3 solution.py http://$HOST:$PORT      # the proxy (host port 1024 locally)
# flag{hi_my_n4me_i5_h4ckerman}
```

**Lesson:** a decryption oracle is as good as the key. The service happily decrypts
anything it recognises as its own ciphertext, and an unencrypted field (the
username) is enough to smuggle the flag's ciphertext back through that oracle.

## Debrief: what you learn and how to protect against it

**What you learn:** strong encryption does not help when the service decrypts for
anyone who asks. The proxy decrypts every `ENCRYPTED:...` value it sees in a
response, which makes it a decryption oracle: you never need the AES key, you get
the server to use it for you. On the way you also use a broken access control
(the activity log shows everyone's entries).

**The solve in short:**

1. Register and open `/activity`. The first entry is the admin's note, base64
   encoded.
2. Base64-decode it to get the encrypted flag: `ENCRYPTED:...`.
3. The source shows that `username` is one of the fields the proxy does not
   encrypt. Register a new user whose username is that `ENCRYPTED:...` value.
4. Open a page that shows your username. The proxy decrypts it on the way out,
   and your username is displayed as the flag.

**How to protect against it:**

- Decrypt only the specific fields you encrypted yourself, for a user who is
  allowed to see them. Never search a whole response for something that looks
  like ciphertext.
- Bind each ciphertext to its context. AES-GCM takes "associated data": put the
  owner and the field name there, and a ciphertext that is moved to another user
  or field fails to decrypt.
- Fix the access control: a user should only see their own activity.
- Validate input: a username should not be allowed to look like the system's
  own ciphertext format.
