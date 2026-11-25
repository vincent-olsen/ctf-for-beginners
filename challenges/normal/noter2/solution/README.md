There is no link to the page where the flag resides.
So how do you find it?

You could use a tool that iterates over known directories.
However, the description gives us a hint that the page is
hidden from crawlers. This is usually done with `robots.txt`.

We navigate to <challenge-url>/robots.txt.
This presents us with a list of disallowed sites for bots:

```
User-agent: *
Disallow: /notes
```

Since the note containing the flag is hidden from bots,
the flag is probably at `/notes`
Navigating to the new page reveals the flag.

## Debrief: what you learn and how to protect against it

**What you learn:** what `robots.txt` is. A site uses it to ask search engines
not to crawl certain paths. It is public and it is only a request, so it works as
a list of the places the owner would rather you did not look.

**The solve in short:**

1. The description hints at a page hidden from crawlers.
2. Open `/robots.txt`: it says `Disallow: /notes`.
3. Open `/notes` and read the flag.

**How to protect against it:**

- `robots.txt` is not access control. A page that must be private needs a login
  and an authorisation check on the server.
- Don't list sensitive paths in it. If the goal is only to stay out of search
  results, use a `noindex` meta tag or an `X-Robots-Tag` header on the page
  itself.
- Assume hidden paths get found anyway: tools like `gobuster` and `ffuf` guess
  thousands of common names per minute.
