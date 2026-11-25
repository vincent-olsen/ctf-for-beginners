"""AI-modus look for api-ai in a browser. Cosmetic only, not part of the challenge.

app.py loads this if it's present (the players' copy of app.py runs without it):
  - GET / from a browser (Accept: text/html) gets a styled landing page; API
    clients still get the same JSON as before.
  - GET /docs gets FastAPI's Swagger UI in a dark AI-modus frame.
Both follow the effects level picked on the CTFd board (BOOT, below).
"""
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

# The AI-modus effects level the player picked on the CTFd board, the same inline
# bootstrap as the other hosted AI challenges: #fx=<level> from the board's link
# (else the last one, else 2) on <html data-ai-fx>, before paint, and the shared kit
# from CTFd on this host (platform/theme/hosted-fx.css and .js). Without CTFd the
# page looks as it always did.
BOOT = """  <script>
  /* AI-modus effects level (platform/theme/hosted-fx.css): #fx=<level> from the CTFd board, else the last one, else 2 */
  (function () {
    try {
      var d = document.documentElement, ok = { "-1": 1, "1": 1, "2": 1, "3": 1 }, fx = "", keep = [];
      var parts = location.hash.slice(1).split("&");
      for (var i = 0; i < parts.length; i++) {
        if (parts[i].slice(0, 3) === "fx=" && ok[parts[i].slice(3)] === 1) fx = parts[i].slice(3);
        else if (parts[i]) keep.push(parts[i]);
      }
      if (fx) {
        try { localStorage.setItem("ctf-ai-fx", fx); } catch (e) {}
        try { history.replaceState(history.state, "", location.pathname + location.search + (keep.length ? "#" + keep.join("&") : "")); } catch (e) {}
      } else {
        try { fx = localStorage.getItem("ctf-ai-fx") || ""; } catch (e) {}
        if (ok[fx] !== 1) fx = "2";
      }
      d.setAttribute("data-ai-fx", fx);
      var kit = "//" + location.hostname + "/ctf-theme/hosted-fx.", head = document.head || d;
      var css = document.createElement("link"), js = document.createElement("script");
      css.rel = "stylesheet"; css.href = kit + "css";
      css.setAttribute("blocking", "render"); /* no flash of the old look; a slow CTFd holds the page 1.5 s at most */
      css.onload = css.onerror = function () { css.done = 1; };
      setTimeout(function () { if (!css.done) css.removeAttribute("blocking"); }, 1500);
      js.src = kit + "js"; js.defer = true;
      head.appendChild(css); head.appendChild(js);
    } catch (e) {}
  })();
  </script>
"""

KIT = """
    /* AI-modus look, same palette as the CTFd theme (platform/theme/ai-mode.css) */
    :root { --bg:#060403; --panel:#120a06; --line:#4a2412; --fg:#ffe9d6; --soft:#f2d2b6; --muted:#c79a7a;
      --amber:#ffc400; --orange:#ff7a00; --red:#ff2e00; --hot:#ff5a2a; --neon:#39ff14; --cyan:#00e5ff;
      --mono:ui-monospace, SFMono-Regular, Menlo, Consolas, "Courier New", monospace; }
    * { box-sizing:border-box; }
    html { background:var(--bg); color-scheme:dark; }
    body { margin:0; min-height:100vh; color:var(--fg); background:transparent;
      font:16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
    .wrap { position:relative; z-index:1; max-width:720px; margin:0 auto; padding:40px 16px 64px; }
    .bar { display:flex; flex-wrap:wrap; align-items:center; gap:.4rem 1rem; margin-bottom:1rem;
      font:.75rem var(--mono); letter-spacing:.14em; color:var(--muted); }
    .lane { padding:3px 9px; border-radius:6px; font-weight:700; color:#1a0600;
      background:linear-gradient(90deg, #ff2e00, #ff7a00 55%, #ffc400); box-shadow:0 0 14px rgba(255,90,0,.5); }
    .threat { color:var(--hot); font-weight:700; }
    .box { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:20px 22px;
      margin-bottom:14px; box-shadow:0 0 30px rgba(255,90,0,.10); }
    .box.bad { border-color:var(--red); box-shadow:0 0 24px rgba(255,46,0,.25); }
    .box.good { border-color:var(--neon); box-shadow:0 0 24px rgba(57,255,20,.2); }
    h1, h2 { margin:0 0 .6rem; font-family:var(--mono); font-weight:700; line-height:1.15; letter-spacing:.02em;
      background:linear-gradient(0deg, #ff2e00 0%, #ff7a00 38%, #ffc400 68%, #fff3b0 100%); background-size:100% 220%;
      -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; color:var(--orange);
      filter:drop-shadow(0 0 12px rgba(255,90,0,.5)); animation:fire 1.3s ease-in-out infinite alternate; }
    h1 { font-size:clamp(1.6rem, 5vw, 2.3rem); }
    .bad h1 { background:linear-gradient(0deg, #ff2e00, #ff5a2a 60%, #ffb199); -webkit-background-clip:text; background-clip:text; }
    .good h1 { background:linear-gradient(0deg, #1fae00, #39ff14 60%, #d8ffcf); -webkit-background-clip:text; background-clip:text;
      filter:drop-shadow(0 0 12px rgba(57,255,20,.5)); }
    .glitch { position:relative; display:inline-block; }
    .glitch::before, .glitch::after { content:attr(data-text); position:absolute; left:0; top:0; width:100%;
      -webkit-text-fill-color:currentColor; background:none; clip-path:inset(0 0 100% 0); pointer-events:none; }
    .glitch::before { color:var(--cyan); animation:glitch-a 3.1s steps(1) infinite; }
    .glitch::after { color:var(--red); animation:glitch-b 3.1s steps(1) infinite; }
    p { margin:.5rem 0; color:var(--soft); }
    a { color:var(--amber); } a:hover { color:#ffe27a; text-shadow:0 0 8px var(--orange); }
    code, pre, small.sql { font-family:var(--mono); color:var(--neon); background:#020201; border-radius:4px; }
    code { padding:1px 6px; }
    input, button { font:inherit; font-family:var(--mono); min-height:44px; border-radius:8px; }
    input { padding:0 12px; background:#0a0604; color:var(--fg); border:1px solid var(--line); caret-color:var(--amber); }
    input:focus { outline:none; border-color:var(--orange); box-shadow:0 0 0 3px rgba(255,122,0,.3); }
    button { padding:0 18px; border:0; cursor:pointer; font-weight:700; letter-spacing:.06em; color:#1a0600;
      background:linear-gradient(90deg, #ff2e00, #ff7a00 55%, #ffc400); box-shadow:0 0 16px rgba(255,90,0,.45); }
    button:focus-visible, a:focus-visible { outline:3px solid #fff; outline-offset:2px; }
    .rule { margin-top:1.5rem; font:.8rem var(--mono); letter-spacing:.1em; color:var(--muted); }
    .rule b { color:var(--amber); }
    /* scanlines on top; they never take clicks */
    .fx-scanlines { position:fixed; inset:0; z-index:2; pointer-events:none;
      background:repeating-linear-gradient(0deg, rgba(0,0,0,0) 0, rgba(0,0,0,0) 2px, rgba(0,0,0,.24) 3px, rgba(0,0,0,0) 4px); }
    @keyframes fire { from { background-position:0 0; } to { background-position:0 100%; } }
    @keyframes glitch-a { 0%, 84%, 100% { clip-path:inset(0 0 100% 0); transform:none; }
      86% { clip-path:inset(12% 0 58% 0); transform:translate(-4px, -1px); } 89% { clip-path:inset(62% 0 10% 0); transform:translate(3px, 1px); }
      92% { clip-path:inset(34% 0 38% 0); transform:translate(-2px, 0); } }
    @keyframes glitch-b { 0%, 85%, 100% { clip-path:inset(0 0 100% 0); transform:none; }
      87% { clip-path:inset(48% 0 22% 0); transform:translate(4px, 1px); } 90% { clip-path:inset(8% 0 70% 0); transform:translate(-3px, -1px); }
      93% { clip-path:inset(70% 0 4% 0); transform:translate(2px, 0); } }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation:none !important; } }
"""

SCANLINES = '<div class="fx-scanlines" aria-hidden="true"></div>'

LANDING = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
""" + BOOT + """  <title>Noteworthy API</title>
  <style>""" + KIT + """
    ul { margin:.5rem 0 0; padding-left:1.2rem; color:var(--soft); }
  </style>
</head>
<body>
  """ + SCANLINES + """
  <main class="wrap">
    <div class="bar"><span class="lane">AI-MODUS</span><span>ai-web · api-ai</span><span class="threat">THREAT 4/5</span></div>
    <div class="box">
      <h1 class="glitch" data-text="Noteworthy API">Noteworthy API</h1>
      <p>A small notes API, version 3.0.0 — the obvious way in is patched.</p>
      <p>Enumerate the API at <a href="/docs">/docs</a> or <a href="/openapi.json">/openapi.json</a>
         — the flag sits behind an admin-only endpoint.</p>
      <ul><li>Browsers get this page; <code>curl</code> and scripts get the JSON.</li></ul>
    </div>
    <p class="rule"><b>AI expected.</b> Bring your assistant.</p>
  </main>
</body>
</html>
"""

# Swagger UI is light-only; invert it into a dark UI (hue-rotate keeps the
# method colours) and re-invert what must keep its own colours. The frame's
# styles are scoped to .ai-frame so none of them reach Swagger's own markup.
DOCS_STYLE = """<meta charset="utf-8">
  <style>
    :root { --bg:#060403; --line:#4a2412; --muted:#c79a7a; --amber:#ffc400; --orange:#ff7a00; --red:#ff2e00;
      --hot:#ff5a2a; --cyan:#00e5ff; --mono:ui-monospace, SFMono-Regular, Menlo, Consolas, "Courier New", monospace; }
    html { background:var(--bg); }
    body { margin:0; background:transparent; }
    .ai-frame { position:relative; z-index:1; max-width:1460px; margin:0 auto; padding:24px 16px 64px; }
    .ai-frame .bar { display:flex; flex-wrap:wrap; align-items:center; gap:.4rem 1rem; margin-bottom:.75rem;
      font:.75rem var(--mono); letter-spacing:.14em; color:var(--muted); }
    .ai-frame .lane { padding:3px 9px; border-radius:6px; font-weight:700; color:#1a0600;
      background:linear-gradient(90deg, #ff2e00, #ff7a00 55%, #ffc400); box-shadow:0 0 14px rgba(255,90,0,.5); }
    .ai-frame .threat { color:var(--hot); font-weight:700; }
    .ai-frame .docs-head { display:flex; flex-wrap:wrap; align-items:baseline; gap:.5rem 1.25rem; margin-bottom:1rem; }
    .ai-frame .docs-head h1 { position:relative; display:inline-block; margin:0; font:700 clamp(1.5rem, 4vw, 2.2rem)/1.15 var(--mono);
      background:linear-gradient(0deg, #ff2e00 0%, #ff7a00 38%, #ffc400 68%, #fff3b0 100%); background-size:100% 220%;
      -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; color:var(--orange);
      filter:drop-shadow(0 0 12px rgba(255,90,0,.5)); animation:fire 1.3s ease-in-out infinite alternate; }
    .ai-frame .docs-head h1::before, .ai-frame .docs-head h1::after { content:attr(data-text); position:absolute; left:0; top:0;
      width:100%; -webkit-text-fill-color:currentColor; background:none; clip-path:inset(0 0 100% 0); pointer-events:none; }
    .ai-frame .docs-head h1::before { color:var(--cyan); animation:glitch-a 3.1s steps(1) infinite; }
    .ai-frame .docs-head h1::after { color:var(--red); animation:glitch-b 3.1s steps(1) infinite; }
    .ai-frame .rule { margin:0; font:.8rem var(--mono); letter-spacing:.1em; color:var(--muted); }
    .ai-frame .rule b { color:var(--amber); }
    .ai-frame .swagger-ui { border-radius:12px; overflow:hidden; border:1px solid var(--line);
      filter:invert(92%) hue-rotate(180deg) sepia(.12); background:#fff; }
    .ai-frame .swagger-ui img, .ai-frame .swagger-ui .microlight, .ai-frame .swagger-ui .highlight-code {
      filter:invert(100%) hue-rotate(180deg); }
    .ai-frame .swagger-ui .topbar { display:none; }
    .fx-scanlines { position:fixed; inset:0; z-index:2; pointer-events:none;
      background:repeating-linear-gradient(0deg, rgba(0,0,0,0) 0, rgba(0,0,0,0) 2px, rgba(0,0,0,.18) 3px, rgba(0,0,0,0) 4px); }
    @keyframes fire { from { background-position:0 0; } to { background-position:0 100%; } }
    @keyframes glitch-a { 0%, 84%, 100% { clip-path:inset(0 0 100% 0); transform:none; }
      86% { clip-path:inset(12% 0 58% 0); transform:translate(-4px, -1px); } 89% { clip-path:inset(62% 0 10% 0); transform:translate(3px, 1px); }
      92% { clip-path:inset(34% 0 38% 0); transform:translate(-2px, 0); } }
    @keyframes glitch-b { 0%, 85%, 100% { clip-path:inset(0 0 100% 0); transform:none; }
      87% { clip-path:inset(48% 0 22% 0); transform:translate(4px, 1px); } 90% { clip-path:inset(8% 0 70% 0); transform:translate(-3px, -1px); }
      93% { clip-path:inset(70% 0 4% 0); transform:translate(2px, 0); } }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation:none !important; } }
  </style>
"""

DOCS_HEAD = """
  """ + SCANLINES + """
  <main class="ai-frame">
    <div class="bar"><span class="lane">AI-MODUS</span><span>ai-web · api-ai</span><span class="threat">THREAT 4/5</span></div>
    <div class="docs-head"><h1 class="glitch" data-text="Noteworthy API · docs">Noteworthy API · docs</h1>
      <p class="rule"><b>AI expected.</b> Bring your assistant.</p></div>
"""


def docs_page(app) -> str:
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} · docs",
        swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"},
    ).body.decode()
    html = html.replace("<head>", "<head>\n" + BOOT, 1)
    html = html.replace("</head>", DOCS_STYLE + "</head>", 1)
    html = html.replace("<body>", "<body>" + DOCS_HEAD, 1)
    return html.replace("</body>", "  </main>\n</body>", 1)


def install(app) -> None:
    @app.middleware("http")
    async def ai_modus_skin(request, call_next):
        if request.method == "GET":
            if request.url.path == "/docs":
                return HTMLResponse(docs_page(app))
            if request.url.path == "/" and "text/html" in request.headers.get("accept", ""):
                return HTMLResponse(LANDING)
        return await call_next(request)
