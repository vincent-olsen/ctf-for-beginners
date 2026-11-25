### decode2

Provided String

```makefile
TVpXR0NaMzNORlBXR1lMT0w1WkdLWUxFTDUyR1FNTFRQVT09PT09PQ==
```

Here you will see that it's ending in two equal signs, suggesting that it's base64. So we decode it.

`echo 'TVpXR0NaMzNORlBXR1lMT0w1WkdLWUxFTDUyR1FNTFRQVT09PT09PQ==' | base64 -d`

Then we get the following

```
MZWGCZ33NFPWGYLOL5ZGKYLEL52GQMLTPU======
```

Here you will see that it's ending in six equal signs, suggesting that it's base32. So we decode it again

`echo 'MZWGCZ33NFPWGYLOL5ZGKYLEL52GQMLTPU======' | base32 -d`

and we get

```
flag{i_can_read_th1s}
```

You can also execute the command `echo 'TVpXR0NaMzNORlBXR1lMT0w1WkdLWUxFTDUyR1FNTFRQVT09PT09PQ==' | base64 -d | base32 -d` 

## Debrief: what you learn and how to protect against it

**What you learn:** encodings can be stacked, and each one has a fingerprint.
Base64 uses upper and lower case and ends in at most two `=`; base32 uses only
`A-Z` and `2-7` and can end in up to six `=`. You peel them one layer at a time.

**The solve in short:**

1. Base64-decode the string. The result is upper case only and ends in `======`.
2. Base32-decode that.
3. Or in one go: `echo '...' | base64 -d | base32 -d`.

**How to protect against it:**

- Two encodings on top of each other are exactly as secret as one: not at all.
  Without a key there is nothing to keep an attacker out.
- Use real encryption for data that must be secret (see `decode1`).
