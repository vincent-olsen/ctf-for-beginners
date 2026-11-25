Flag can be found in the source as a comment.

Press `F12` in the browser, or right-click -> "View source".

## Debrief: what you learn and how to protect against it

**What you learn:** how to look at what the browser actually received: "View
source" or the developer tools (F12). Everything a server sends is readable by
the user, including HTML comments that are not shown on the page.

**The solve in short:**

1. Open the page and view the source (right-click → "View page source", or F12).
2. The flag is in an HTML comment near the top of the page.

**How to protect against it:**

- Treat everything that reaches the browser as public: HTML comments, JavaScript,
  hidden form fields, source maps. Never put passwords, keys, internal URLs or
  TODO notes there.
- Use server-side template comments (in Jinja `{# ... #}`), which are never sent,
  and strip comments in the production build.
- Add a secret scanner and code review to the pipeline, so a forgotten comment
  is caught before it ships.
