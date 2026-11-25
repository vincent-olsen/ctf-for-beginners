### Double Decode Hard

Reference: [https://ctftime.org/writeup/38211](https://ctftime.org/writeup/38211)

**Provided string in base32 format**

```jsx
FYXC4LROEUZDALRNEUZDALJOFYXC4JJSGAWS4LRFGIYC2LJOFYXCKMRQFUWS2LROEUZDALJOFYXC4JJSGAWS2LJOFYSTEMBOFYXC4LRFGIYC4LJFGIYC4LROFUWSKMRQFYXC4LJNEUZDALJNFYXC4JJSGAXC4LROFUSTEMBNFYXC4LRFGIYC2LROFYSTEMBOFYXC4LRFGIYC4LJFGIYC4LROFYXCKMRQFUWS4LROEUZDALROFYXC2JJSGAXCKMRQFUWS4LROEUZDALJOFYXC4JJSGAXC4LROFYSTEMBOFUSTEMBOFYXC4LJFGIYC2LJOFYXCKMRQFUXC4LROEUZDALJOFUXCKMRQFUWS4LROEUZDALROFYXC4JJSGAXC4LROFYSTEMBOFUSTEMBOFYXC2LJFGIYC4LJNFUWSKMRQFYXC4LJNEUZDALJNFUWS4JJSGAXC4LRNFUSTEMBNFUWS2LJFGIYC2LROFYXCKMRQFYWS2LJNEUZDALROFYXC2JJSGAWS2LROFYSTEMBOFYXC4LRFGIYC2LROFYXCKMRQFUXC4LROEUZDALJOFYXC4JJSGAWS4LROFYSTEMBOFYXC2LJFGIYC4LROFUWSKMRQFYXC2LJNEUZDALROFYXC4JJSGAWS4LROFYSTEMBNFYXC4LRFGIYC4LJFGIYC2LROFYXCKMRQFYXC4LJNEUZDALJOFYXC4JJSGAWS4LRFGIYC4LROFYXCKMRQFUXC4LROEUZDALROFYWS2JJSGAWS2LJNFUSTEMBOFYXC4LRFGIYC2LJNFYXCKMRQFYXC4LJNEUZDALROFYWS2JJSGAXC4LROFYSTEMBOFYWS2LJFGIYC2LROFYXCKMRQFUXC2LRFGIYC2LROFYXCKMRQFYXC4LROEUZDALROFYXC2JJSGAWS2LJOFYSTEMBOFYXC4LRFGIYC4LRNFUWSKMRQFYXC4LJNEUZDALJNFUWS4===
```

Then you need to decode it to URL

**URL encode**

```jsx
.....%20.-%20-....%20-..%20--...%20---..%20-....%20---..%20.....%20.-%20...--%20...--%20--...%20....-%20-....%20-...%20.....%20.-%20.....%20--...%20....-%20.%20--...%20-....%20.....%20.-%20....-%20--...%20-....%20-.-.%20--...%20.....%20.....%20.-%20...--%20.----%20...--%20----.%20...--%20-----%20-....%20.----%20....-%20--...%20.....%20-....%20-....%20-....%20-....%20...--%20...--%20..---%20.....%20-....%20-....%20.-%20-....%20...--%20-....%20-..%20.....%20-....%20...--%20-----%20.....%20---..%20...--%20...--%20.....%20..---%20-....%20-.-.%20-....%20.....%20....-%20---..%20.....%20..---%20...--%20----.
```

Decode it to morse

**Morsecode**

```jsx
..... .- -.... -.. --... ---.. -.... ---.. ..... .- ...-- ...-- --... ....- -.... -... ..... .- ..... --... ....- . --... -.... ..... .- ....- --... -.... -.-. --... ..... ..... .- ...-- .---- ...-- ----. ...-- ----- -.... .---- ....- --... ..... -.... -.... -.... -.... ...-- ...-- ..--- ..... -.... -.... .- -.... ...-- -.... -.. ..... -.... ...-- ----- ..... ---.. ...-- ...-- ..... ..--- -.... -.-. -.... ..... ....- ---.. ..... ..--- ...-- ----.
```

Decode it to hex

**Hexencoded**

```jsx
5a6d78685a33746b5a574e765a476c755a313930614756666332566a636d56305833526c65485239
```

Decode it to base64

**Base64**

```jsx
ZmxhZ3tkZWNvZGluZ190aGVfc2VjcmV0X3RleHR9
```

**Solution**

Execute `echo -n ZmxhZ3tkZWNvZGluZ190aGVfc2VjcmV0X3RleHR9 | base64 -d`

```jsx
flag{decoding_the_secret_text}
```

## Debrief: what you learn and how to protect against it

**What you learn:** the same idea as `decode1` and `decode2` with five layers
(base32, URL encoding, Morse, hex, base64). You learn to recognise each format by
how it looks, and that a tool like CyberChef (the "Magic" operation) does the
recognising for you.

**The solve in short:**

1. Base32-decode (only `A-Z2-7`, ends in `===`).
2. URL-decode (`%20` is a space).
3. Decode the Morse (dots and dashes) to hex digits.
4. Hex-decode to a base64 string.
5. Base64-decode to the flag.

**How to protect against it:**

- More layers cost the attacker a few more seconds. Encoding never becomes
  encryption, however many times you repeat it.
- The defensive side of this: attackers wrap their payloads in nested encodings
  to slip past filters. A filter or WAF has to decode and normalise input before
  it checks it, and the application has to validate the decoded value.
