<!--
  The podium page (route "podium"), synced into CTFd by ./ctf.sh up (see
  docs/ai-mode.md, "The podium page", and docs/language.md). It shows who won:
  each lane's champion with the team's members, and the 2nd and 3rd place, read
  from the ai_brackets plugin (/ai-brackets/winners). The plugin only hands the
  places out when they are the result, so until then the page says so instead:
  "sealed" while the scoreboard is frozen, "no winners yet" while the CTF runs.
  It asks again every 20 seconds and reveals itself when the freeze is lifted.
  Presenter mode (the button at the bottom, or /podium#present) is a full-screen
  podium, AI-MODUS first and then Classic, that reveals one place per click from
  the 3rd up; an admin can run it while the scoreboard is still frozen. The page is created hidden (reachable, but not in
  the navbar; ctfd_admin.py PAGES_CREATED_HIDDEN). One file for both languages,
  like the front page: each text is a block per language (class="ctf-lang").
  Keep the markup free of blank lines (Markdown ends an HTML block at one) and
  keep the blank line before <script>, which starts a block of its own there.
-->
<style>
  .ctf-podium, .ctf-podium-stage { --w-bg:#0b121a; --w-panel:#16212c; --w-line:#2a3c4e; --w-ink:#e6eef5; --w-soft:#c3d1de;
    --w-muted:#9db0c2; --w-accent:#5ab0ff; --w-accent-ink:#07213d; --w-bar:#2a3c4e; --w-glow:none;
    --w-font:system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
  .ctf-podium-lane[data-bracket="ai"], .ctf-podium-stage[data-lane="ai"] { --w-bg:#060403; --w-panel:#120a06; --w-line:#4a2412;
    --w-ink:#ffe9d6; --w-soft:#f2d2b6; --w-muted:#c79a7a; --w-accent:#ffc400; --w-accent-ink:#1a0600; --w-bar:#4a2412;
    --w-glow:0 0 18px rgba(255,90,0,.7); --w-font:ui-monospace, SFMono-Regular, Menlo, Consolas, "Courier New", monospace; }
  .ctf-podium [hidden], .ctf-podium-stage[hidden], .ctf-podium-stage [hidden] { display:none !important; }
  .ctf-podium [data-when] { display:none; }
  .ctf-podium[data-state="loading"] [data-when~="loading"], .ctf-podium[data-state="final"] [data-when~="final"],
  .ctf-podium[data-state="sealed"] [data-when~="sealed"], .ctf-podium[data-state="running"] [data-when~="running"],
  .ctf-podium[data-state="tba"] [data-when~="tba"] { display:revert; }
  .ctf-podium { margin:1.5rem 0 3rem; padding:3.5rem 1.5rem 4rem; border-radius:16px; background:var(--w-bg); color:var(--w-ink);
    font-family:var(--w-font); display:flex; flex-direction:column; gap:2.5rem; text-shadow:none; }
  .ctf-podium p, .ctf-podium h1, .ctf-podium h2, .ctf-podium ul, .ctf-podium ol { margin:0; padding:0; }
  .ctf-podium-head { display:flex; flex-direction:column; align-items:center; gap:.75rem; text-align:center; }
  .ctf-podium-lock { width:56px; height:56px; color:var(--w-muted); }
  .ctf-podium-kicker { font-size:.875rem; letter-spacing:.24em; text-transform:uppercase; color:var(--w-muted); }
  .ctf-podium h1 { font-size:clamp(2.5rem, 7vw, 4.5rem); line-height:1; font-weight:800; letter-spacing:-.02em; color:var(--w-ink); }
  .ctf-podium-lead { font-size:1.25rem; color:var(--w-soft); max-width:45rem; }
  .ctf-podium-lanes { display:flex; flex-wrap:wrap; gap:2rem; align-items:stretch; }
  .ctf-podium-lane { flex:1 1 20rem; min-width:0; box-sizing:border-box; padding:2.5rem; display:flex; flex-direction:column; gap:1.75rem;
    background:var(--w-panel); color:var(--w-ink); font-family:var(--w-font); border:1px solid var(--w-line);
    border-top:4px solid var(--w-accent); border-radius:16px; }
  .ctf-podium-lane[data-bracket="ai"] { border-top-color:#ff7a00; }
  .ctf-podium-lane-head { display:flex; justify-content:space-between; align-items:center; gap:1rem; }
  .ctf-podium-lane-name { font-size:.875rem; font-weight:700; letter-spacing:.2em; text-transform:uppercase; color:var(--w-accent); }
  .ctf-podium-lane-tag { font-size:.875rem; color:var(--w-muted); }
  .ctf-podium-champion { display:flex; flex-direction:column; gap:.75rem; }
  .ctf-podium-trophy { display:block; width:56px; height:56px; color:var(--w-accent); }
  .ctf-podium-lane[data-bracket="ai"] .ctf-podium-trophy { color:#ff7a00; }
  .ctf-podium-label { font-size:.875rem; letter-spacing:.16em; text-transform:uppercase; color:var(--w-soft); }
  .ctf-podium-name-line { font-size:clamp(2rem, 4.2vw, 3.5rem); line-height:1.05; font-weight:800; letter-spacing:-.02em; overflow-wrap:anywhere; }
  .ctf-podium a.ctf-podium-name, .ctf-podium a.ctf-podium-name:hover { color:var(--w-ink); text-decoration:none; text-shadow:var(--w-glow); }
  .ctf-podium-lane[data-bracket="ai"] a.ctf-podium-name, .ctf-podium-lane[data-bracket="ai"] a.ctf-podium-name:hover { color:var(--w-accent); }
  .ctf-podium a[href]:hover { text-decoration:underline; }
  .ctf-podium-score { font-size:1.5rem; font-weight:700; color:var(--w-accent); font-variant-numeric:tabular-nums; }
  .ctf-podium-lane[data-bracket="ai"] .ctf-podium-score { color:#ff7a00; }
  .ctf-podium-score small { font-size:1rem; font-weight:400; color:var(--w-muted); }
  .ctf-podium-none { font-size:1.125rem; color:var(--w-muted); }
  .ctf-podium-bars span { display:block; height:3.5rem; width:78%; border-radius:8px; background:var(--w-bar); }
  .ctf-podium-bars span + span { height:1.5rem; width:34%; margin-top:1.25rem; opacity:.7; }
  .ctf-podium[data-state] ul.ctf-podium-members { list-style:none; display:flex; flex-wrap:wrap; gap:.5rem; }
  .ctf-podium[data-state="final"] ul.ctf-podium-members:empty { display:none; }
  .ctf-podium-members li { padding:.35rem .9rem; border:1px solid var(--w-line); border-radius:999px; font-size:.95rem; }
  .ctf-podium-members a, .ctf-podium-members a:hover { color:var(--w-soft); text-decoration:none; }
  .ctf-podium[data-state="final"] ol.ctf-podium-rows { list-style:none; display:flex; flex-direction:column; gap:.75rem; margin-top:auto;
    padding-top:1.25rem; border-top:1px solid var(--w-line); }
  .ctf-podium-row { display:flex; align-items:center; gap:1rem; }
  .ctf-podium-place { flex:none; width:44px; height:44px; border-radius:10px; background:var(--w-bg); border:1px solid var(--w-line);
    display:flex; align-items:center; justify-content:center; font-size:1.125rem; font-weight:700; color:var(--w-soft); }
  .ctf-podium a.ctf-podium-row-name, .ctf-podium a.ctf-podium-row-name:hover { flex:1; min-width:0; font-size:1.25rem; font-weight:600;
    overflow-wrap:anywhere; color:var(--w-ink); text-decoration:none; }
  .ctf-podium-row-score { font-size:1.125rem; color:var(--w-soft); font-variant-numeric:tabular-nums; }
  .ctf-podium-foot { display:flex; flex-wrap:wrap; justify-content:center; align-items:center; gap:1rem 2rem; text-align:center; }
  .ctf-podium-thanks, .ctf-podium-note { font-size:1rem; color:var(--w-muted); }
  .ctf-podium-note { flex-basis:100%; font-size:.875rem; }
  .ctf-podium a.ctf-podium-button, .ctf-podium button.ctf-podium-button { display:inline-flex; align-items:center; min-height:44px; padding:0 1.25rem;
    border:1px solid var(--w-accent); border-radius:10px; background:transparent; color:var(--w-accent); font:inherit; font-size:1rem;
    font-weight:600; text-decoration:none; cursor:pointer; }
  .ctf-podium a.ctf-podium-button:hover, .ctf-podium button.ctf-podium-button:hover { background:var(--w-accent); color:var(--w-accent-ink); text-decoration:none; }
  .ctf-podium.ctf-podium-fresh .ctf-podium-name-line, .ctf-podium.ctf-podium-fresh .ctf-podium-score { animation:ctf-podium-pop .7s cubic-bezier(.2,.9,.3,1.2) both; }

  .ctf-podium-stage { position:fixed; inset:0; z-index:20000; box-sizing:border-box; padding:5vh 6vw 4vh; display:flex; flex-direction:column;
    gap:3vh; background:var(--w-bg); color:var(--w-ink); font-family:var(--w-font); text-shadow:none; outline:none; }
  .ctf-podium-stage p, .ctf-podium-stage h2 { margin:0; }
  .ctf-podium-stage-head { display:flex; flex-wrap:wrap; justify-content:space-between; align-items:flex-end; gap:1.5rem; }
  .ctf-podium-stage-kicker { font-size:clamp(.8rem, 1vw, 1.1rem); letter-spacing:.24em; text-transform:uppercase; color:var(--w-muted); }
  .ctf-podium-stage h2 { margin-top:.5rem; font-size:clamp(2.5rem, 4.6vw, 6rem); line-height:1; font-weight:800; letter-spacing:-.02em; color:var(--w-accent); }
  .ctf-podium-tabs { display:flex; gap:.5rem; }
  .ctf-podium-tabs button { padding:0 1.1rem; border:1px solid var(--w-line); background:transparent; color:var(--w-muted); font-size:1rem; font-weight:600; }
  .ctf-podium-tabs button[aria-pressed="true"] { border-color:var(--w-accent); color:var(--w-accent); }
  .ctf-podium-podium { flex:1; min-height:0; display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:2.2vw; align-items:end; }
  .ctf-podium-slot { display:flex; flex-direction:column; gap:1.6vh; text-align:center; }
  .ctf-podium-slot[data-place="2"] { grid-column:1; grid-row:1; }
  .ctf-podium-slot[data-place="1"] { grid-column:2; grid-row:1; }
  .ctf-podium-slot[data-place="3"] { grid-column:3; grid-row:1; }
  .ctf-podium-slot-name { font-size:clamp(1.4rem, 2.2vw, 3rem); line-height:1.1; font-weight:700; overflow-wrap:anywhere; color:var(--w-line); }
  .ctf-podium-slot[data-place="1"] .ctf-podium-slot-name { font-size:clamp(1.9rem, 3.4vw, 4.5rem); font-weight:800; letter-spacing:-.02em; }
  .ctf-podium-slot.is-shown .ctf-podium-slot-name { color:var(--w-ink); }
  .ctf-podium-slot.is-rolling .ctf-podium-slot-name { color:var(--w-muted); font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .ctf-podium-slot.is-rolling .ctf-podium-plinth { animation:ctf-podium-roll .16s linear infinite alternate; }
  .ctf-podium-slot.is-landed .ctf-podium-slot-name { animation:ctf-podium-pop .7s cubic-bezier(.2,.9,.3,1.2) both; }
  .ctf-podium-slot.is-landed .ctf-podium-plinth { animation:ctf-podium-flash 1.1s ease-out both; }
  .ctf-podium-slot.is-landed .ctf-podium-slot-score { animation:ctf-podium-pop .7s .15s cubic-bezier(.2,.9,.3,1.2) both; }
  .ctf-podium-bit { position:fixed; z-index:20001; top:-3vh; width:.7vw; height:1.6vw; min-width:8px; min-height:16px; border-radius:2px;
    pointer-events:none; animation:ctf-podium-fall linear both; }
  .ctf-podium-slot[data-place="1"].is-shown .ctf-podium-slot-name { color:var(--w-accent); text-shadow:var(--w-glow); }
  .ctf-podium-slot-score { font-size:clamp(1rem, 1.3vw, 1.6rem); color:var(--w-muted); font-variant-numeric:tabular-nums; }
  .ctf-podium-plinth { height:22vh; display:flex; align-items:center; justify-content:center; background:var(--w-panel);
    border:1px solid var(--w-line); border-bottom:none; border-radius:12px 12px 0 0; font-size:clamp(3rem, 5vw, 6rem); font-weight:800; color:var(--w-soft); }
  .ctf-podium-slot[data-place="1"] .ctf-podium-plinth { height:34vh; border-top:4px solid var(--w-accent); font-size:clamp(4.5rem, 8vw, 9rem); color:var(--w-accent); }
  .ctf-podium-slot[data-place="3"] .ctf-podium-plinth { height:15vh; }
  .ctf-podium-stage-foot { display:flex; flex-wrap:wrap; justify-content:center; align-items:center; gap:1rem 1.5rem; padding-top:2.5vh; border-top:1px solid var(--w-line); }
  .ctf-podium-stage button { min-height:44px; border-radius:12px; font:inherit; cursor:pointer; }
  .ctf-podium-next { min-height:56px !important; padding:0 2rem; border:none; background:var(--w-accent); color:var(--w-accent-ink);
    font-size:1.25rem !important; font-weight:700 !important; }
  .ctf-podium-close { padding:0 1.25rem; border:1px solid var(--w-line); background:transparent; color:var(--w-soft); font-size:1rem; }
  .ctf-podium-stage button:focus-visible, .ctf-podium button:focus-visible, .ctf-podium a:focus-visible { outline:3px solid var(--w-ink); outline-offset:3px; }
  .ctf-podium-keys { font-size:.95rem; color:var(--w-muted); }
  /* The theme's skins restyle every border, heading and link with !important
     (ai-mode.css); the page keeps its own, so these outrank them. */
  html .ctf-podium.ctf-podium[data-state] *, html .ctf-podium-stage.ctf-podium-stage[data-lane] * { border-color:var(--w-line) !important; }
  html .ctf-podium.ctf-podium[data-state] .ctf-podium-lane, html .ctf-podium-stage.ctf-podium-stage[data-lane] .ctf-podium-slot[data-place="1"] .ctf-podium-plinth { border-top-color:var(--w-accent) !important; }
  html .ctf-podium.ctf-podium[data-state] .ctf-podium-lane[data-bracket="ai"] { border-top-color:#ff7a00 !important; }
  html .ctf-podium.ctf-podium[data-state] .ctf-podium-button, html .ctf-podium-stage.ctf-podium-stage[data-lane] .ctf-podium-tabs button[aria-pressed="true"] { border-color:var(--w-accent) !important; }
  html .ctf-podium.ctf-podium[data-state] :is(h1, h2), html .ctf-podium-stage.ctf-podium-stage[data-lane] h2 { font-family:var(--w-font); color:var(--w-ink) !important; text-shadow:none; letter-spacing:-.02em; }
  html .ctf-podium-stage.ctf-podium-stage[data-lane] h2 { color:var(--w-accent) !important; }
  html .ctf-podium.ctf-podium[data-state] a.ctf-podium-name, html .ctf-podium.ctf-podium[data-state] a.ctf-podium-row-name { color:var(--w-ink) !important; text-shadow:var(--w-glow); }
  html .ctf-podium.ctf-podium[data-state] a.ctf-podium-row-name { text-shadow:none; }
  html .ctf-podium.ctf-podium[data-state] .ctf-podium-lane[data-bracket="ai"] a.ctf-podium-name { color:var(--w-accent) !important; }
  html .ctf-podium.ctf-podium[data-state] .ctf-podium-members a { color:var(--w-soft) !important; text-shadow:none; }
  html .ctf-podium.ctf-podium[data-state] a.ctf-podium-button { color:var(--w-accent) !important; text-shadow:none; }
  html .ctf-podium.ctf-podium[data-state] a.ctf-podium-button:hover { color:var(--w-accent-ink) !important; }
  @keyframes ctf-podium-roll { from { transform:translateY(0); } to { transform:translateY(-.6vh); } }
  @keyframes ctf-podium-flash { 0% { background:var(--w-accent); color:var(--w-accent-ink); transform:translateY(2vh); }
    35% { transform:translateY(-1vh); } 100% { transform:none; } }
  @keyframes ctf-podium-fall { to { transform:translate3d(var(--dx), 110vh, 0) rotate(var(--rot)); opacity:.9; } }
  @keyframes ctf-podium-pop { from { opacity:0; transform:translateY(.4em) scale(.92); } to { opacity:1; transform:none; } }
  @media (prefers-reduced-motion: reduce) {
    .ctf-podium.ctf-podium-fresh .ctf-podium-name-line, .ctf-podium.ctf-podium-fresh .ctf-podium-score, .ctf-podium-slot .ctf-podium-slot-name, .ctf-podium-slot .ctf-podium-plinth, .ctf-podium-slot .ctf-podium-slot-score { animation:none !important; }
  }
</style>

<div class="ctf-podium" data-state="loading">
  <header class="ctf-podium-head">
    <span data-when="sealed"><svg class="ctf-podium-lock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"></rect><path d="M8 11V8a4 4 0 0 1 8 0v3"></path><path d="M12 15v2"></path></svg></span>
    <p class="ctf-podium-kicker"><span class="ctf-lang" lang="no">Sluttresultat</span><span class="ctf-lang" lang="en">Final results</span></p>
    <h1><span data-when="loading final tba"><span class="ctf-lang" lang="no">Vinnerne</span><span class="ctf-lang" lang="en">The winners</span></span><span data-when="sealed"><span class="ctf-lang" lang="no">Resultatet er forseglet</span><span class="ctf-lang" lang="en">The results are sealed</span></span><span data-when="running"><span class="ctf-lang" lang="no">Ingen vinnere ennå</span><span class="ctf-lang" lang="en">No winners yet</span></span></h1>
    <p class="ctf-podium-lead" data-when="final"><span class="ctf-lang" lang="no">To baner, to mestere.</span><span class="ctf-lang" lang="en">Two lanes, two champions.</span></p>
    <p class="ctf-podium-lead" data-when="sealed"><span class="ctf-lang" lang="no">Poengtavlen er fryst, så ingen vet ennå hvem som vant. Mesterne vises her under premieutdelingen.</span><span class="ctf-lang" lang="en">The scoreboard is frozen, so nobody knows who won yet. The champions appear here at the prize-giving.</span></p>
    <p class="ctf-podium-lead" data-when="running"><span class="ctf-lang" lang="no">CTF-en pågår fortsatt. Mesterne vises her når den er over.</span><span class="ctf-lang" lang="en">The CTF is still running. The champions appear here when it is over.</span></p>
    <p class="ctf-podium-lead" data-when="tba"><span class="ctf-lang" lang="no">Kunngjøres snart.</span><span class="ctf-lang" lang="en">To be announced.</span></p>
  </header>
  <div class="ctf-podium-lanes">
    <section class="ctf-podium-lane" data-bracket="normal">
      <div class="ctf-podium-lane-head"><span class="ctf-podium-lane-name"><span class="ctf-lang" lang="no">Klassisk</span><span class="ctf-lang" lang="en">Classic</span></span><span class="ctf-podium-lane-tag"><span data-when="final"><span class="ctf-lang" lang="no">Ingen AI</span><span class="ctf-lang" lang="en">No AI</span></span><span data-when="sealed"><span class="ctf-lang" lang="no">Forseglet</span><span class="ctf-lang" lang="en">Sealed</span></span></span></div>
      <div class="ctf-podium-champion">
        <span data-when="final"><svg class="ctf-podium-trophy" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 4h8v5a4 4 0 0 1-8 0V4z"></path><path d="M8 6H5a3 3 0 0 0 3 4"></path><path d="M16 6h3a3 3 0 0 1-3 4"></path><path d="M12 13v4"></path><path d="M10 17h4v3h-4z"></path><path d="M8 20h8"></path></svg></span>
        <p class="ctf-podium-label"><span class="ctf-lang" lang="no">Klassisk-mester</span><span class="ctf-lang" lang="en">Classic champion</span></p>
        <div class="ctf-podium-bars" data-when="loading sealed running tba" aria-hidden="true"><span></span><span></span></div>
        <p class="ctf-podium-none" hidden><span class="ctf-lang" lang="no">Ingen fikk poeng i denne banen.</span><span class="ctf-lang" lang="en">No one scored in this lane.</span></p>
        <h2 class="ctf-podium-name-line" data-when="final"><a class="ctf-podium-name"></a></h2>
        <p class="ctf-podium-score" data-when="final"><span class="ctf-podium-points"></span> <small><span class="ctf-lang" lang="no">poeng</span><span class="ctf-lang" lang="en">points</span></small></p>
      </div>
      <ul class="ctf-podium-members" data-when="final"></ul>
      <ol class="ctf-podium-rows" data-when="final">
        <li class="ctf-podium-row" data-place="2" hidden><span class="ctf-podium-place">2</span><a class="ctf-podium-row-name"></a><span class="ctf-podium-row-score"></span></li>
        <li class="ctf-podium-row" data-place="3" hidden><span class="ctf-podium-place">3</span><a class="ctf-podium-row-name"></a><span class="ctf-podium-row-score"></span></li>
      </ol>
    </section>
    <section class="ctf-podium-lane" data-bracket="ai">
      <div class="ctf-podium-lane-head"><span class="ctf-podium-lane-name">AI-MODUS</span><span class="ctf-podium-lane-tag"><span data-when="final"><span class="ctf-lang" lang="no">AI forventes</span><span class="ctf-lang" lang="en">AI expected</span></span><span data-when="sealed"><span class="ctf-lang" lang="no">Forseglet</span><span class="ctf-lang" lang="en">Sealed</span></span></span></div>
      <div class="ctf-podium-champion">
        <span data-when="final"><svg class="ctf-podium-trophy" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 4h8v5a4 4 0 0 1-8 0V4z"></path><path d="M8 6H5a3 3 0 0 0 3 4"></path><path d="M16 6h3a3 3 0 0 1-3 4"></path><path d="M12 13v4"></path><path d="M10 17h4v3h-4z"></path><path d="M8 20h8"></path></svg></span>
        <p class="ctf-podium-label"><span class="ctf-lang" lang="no">AI-MODUS-mester</span><span class="ctf-lang" lang="en">AI-MODUS champion</span></p>
        <div class="ctf-podium-bars" data-when="loading sealed running tba" aria-hidden="true"><span></span><span></span></div>
        <p class="ctf-podium-none" hidden><span class="ctf-lang" lang="no">Ingen fikk poeng i denne banen.</span><span class="ctf-lang" lang="en">No one scored in this lane.</span></p>
        <h2 class="ctf-podium-name-line" data-when="final"><a class="ctf-podium-name"></a></h2>
        <p class="ctf-podium-score" data-when="final"><span class="ctf-podium-points"></span> <small><span class="ctf-lang" lang="no">poeng</span><span class="ctf-lang" lang="en">points</span></small></p>
      </div>
      <ul class="ctf-podium-members" data-when="final"></ul>
      <ol class="ctf-podium-rows" data-when="final">
        <li class="ctf-podium-row" data-place="2" hidden><span class="ctf-podium-place">2</span><a class="ctf-podium-row-name"></a><span class="ctf-podium-row-score"></span></li>
        <li class="ctf-podium-row" data-place="3" hidden><span class="ctf-podium-place">3</span><a class="ctf-podium-row-name"></a><span class="ctf-podium-row-score"></span></li>
      </ol>
    </section>
  </div>
  <footer class="ctf-podium-foot">
    <p class="ctf-podium-thanks" data-when="final"><span class="ctf-lang" lang="no">Takk for at dere spilte. Hvert flagg telte.</span><span class="ctf-lang" lang="en">Thanks for playing. Every flag counted.</span></p>
    <a class="ctf-podium-button ctf-podium-board" href="/scoreboard"><span class="ctf-lang" lang="no">Se hele poengtavlen</span><span class="ctf-lang" lang="en">See the full scoreboard</span></a>
    <button type="button" class="ctf-podium-button ctf-podium-present" hidden><span class="ctf-lang" lang="no">Presentasjonsmodus</span><span class="ctf-lang" lang="en">Presenter mode</span></button>
    <p class="ctf-podium-note" hidden><span class="ctf-lang" lang="no">Bare administratorer ser Presentasjonsmodus før resultatet er endelig. Den viser sluttresultatet, også det som kom etter frysen.</span><span class="ctf-lang" lang="en">Only admins see Presenter mode before the result is final. It shows the final result, including what came after the freeze.</span></p>
  </footer>
</div>
<div class="ctf-podium-stage" data-lane="ai" role="dialog" aria-modal="true" aria-labelledby="ctf-podium-stage-title" tabindex="-1" hidden>
  <header class="ctf-podium-stage-head">
    <div>
      <p class="ctf-podium-stage-kicker"><span class="ctf-lang" lang="no">Premieutdeling</span><span class="ctf-lang" lang="en">Prize-giving</span></p>
      <h2 id="ctf-podium-stage-title"><span data-lane-name="normal" hidden><span class="ctf-lang" lang="no">Klassisk</span><span class="ctf-lang" lang="en">Classic</span></span><span data-lane-name="ai">AI-MODUS</span></h2>
    </div>
    <div class="ctf-podium-tabs" role="group"><button type="button" data-lane-tab="ai" aria-pressed="true">AI-MODUS</button><button type="button" data-lane-tab="normal" aria-pressed="false"><span class="ctf-lang" lang="no">Klassisk</span><span class="ctf-lang" lang="en">Classic</span></button></div>
  </header>
  <div class="ctf-podium-podium" aria-live="polite">
      <div class="ctf-podium-slot" data-place="2">
        <p class="ctf-podium-slot-name"></p>
        <p class="ctf-podium-slot-score"><span class="ctf-podium-slot-sealed"><span class="ctf-lang" lang="no">forseglet</span><span class="ctf-lang" lang="en">sealed</span></span><span class="ctf-podium-slot-points" hidden><span class="ctf-podium-slot-value"></span> <span class="ctf-lang" lang="no">poeng</span><span class="ctf-lang" lang="en">points</span></span></p>
        <div class="ctf-podium-plinth" aria-hidden="true">2</div>
      </div>
      <div class="ctf-podium-slot" data-place="1">
        <p class="ctf-podium-slot-name"></p>
        <p class="ctf-podium-slot-score"><span class="ctf-podium-slot-sealed"><span class="ctf-lang" lang="no">forseglet</span><span class="ctf-lang" lang="en">sealed</span></span><span class="ctf-podium-slot-points" hidden><span class="ctf-podium-slot-value"></span> <span class="ctf-lang" lang="no">poeng</span><span class="ctf-lang" lang="en">points</span></span></p>
        <div class="ctf-podium-plinth" aria-hidden="true">1</div>
      </div>
      <div class="ctf-podium-slot" data-place="3">
        <p class="ctf-podium-slot-name"></p>
        <p class="ctf-podium-slot-score"><span class="ctf-podium-slot-sealed"><span class="ctf-lang" lang="no">forseglet</span><span class="ctf-lang" lang="en">sealed</span></span><span class="ctf-podium-slot-points" hidden><span class="ctf-podium-slot-value"></span> <span class="ctf-lang" lang="no">poeng</span><span class="ctf-lang" lang="en">points</span></span></p>
        <div class="ctf-podium-plinth" aria-hidden="true">3</div>
      </div>
  </div>
  <footer class="ctf-podium-stage-foot">
    <button type="button" class="ctf-podium-next"><span data-label="3"><span class="ctf-lang" lang="no">Vis 3.-plassen</span><span class="ctf-lang" lang="en">Reveal 3rd place</span></span><span data-label="2" hidden><span class="ctf-lang" lang="no">Vis 2.-plassen</span><span class="ctf-lang" lang="en">Reveal 2nd place</span></span><span data-label="1" hidden><span class="ctf-lang" lang="no">Vis mesteren</span><span class="ctf-lang" lang="en">Reveal the champion</span></span><span data-label="next-normal" hidden><span class="ctf-lang" lang="no">Neste bane: Klassisk</span><span class="ctf-lang" lang="en">Next lane: Classic</span></span><span data-label="next-ai" hidden><span class="ctf-lang" lang="no">Neste bane: AI-MODUS</span><span class="ctf-lang" lang="en">Next lane: AI-MODUS</span></span><span data-label="done" hidden><span class="ctf-lang" lang="no">Ferdig</span><span class="ctf-lang" lang="en">Done</span></span></button>
    <button type="button" class="ctf-podium-close"><span class="ctf-lang" lang="no">Lukk</span><span class="ctf-lang" lang="en">Close</span></button>
    <span class="ctf-podium-keys"><span class="ctf-lang" lang="no">Mellomrom eller →: neste · ←: tilbake · Esc: lukk</span><span class="ctf-lang" lang="en">Space or →: next · ←: back · Esc: close</span></span>
  </footer>
</div>

<script>
// The podium page. Team and player names are what people typed, so they only
// ever go in as text (textContent), never as HTML.
(function () {
  var root = (window.init && window.init.urlRoot) || "";
  var page = document.querySelector(".ctf-podium");
  var stage = document.querySelector(".ctf-podium-stage");
  if (!page || !stage) return;
  // Out of the page's container, so nothing around it can clip a fixed element.
  document.body.appendChild(stage);
  page.querySelector(".ctf-podium-board").setAttribute("href", root + "/scoreboard");

  var BRACKETS = ["normal", "ai"];
  var POLL_MS = 20000;
  var result = null;   // the last answer that carried the places
  var seen = false;    // a state before "final" was shown: the reveal gets its moment
  var timer = null;

  function points(n) {
    return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function ask(reveal) {
    return fetch(root + "/ai-brackets/winners" + (reveal ? "?reveal=1" : ""), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (res) { return res && res.success && res.data ? res.data : null; })
      .catch(function () { return null; });
  }

  function link(a, text, href) {
    a.textContent = text;
    if (href) a.setAttribute("href", href); else a.removeAttribute("href");
  }

  function fillLane(section, teams) {
    var top = teams[0];
    section.querySelector(".ctf-podium-none").hidden = !!top;
    section.querySelector(".ctf-podium-name-line").hidden = !top;
    section.querySelector(".ctf-podium-score").hidden = !top;
    link(section.querySelector(".ctf-podium-name"), top ? top.name : "", top && top.account_url);
    section.querySelector(".ctf-podium-points").textContent = top ? points(top.score) : "";
    var list = section.querySelector(".ctf-podium-members");
    list.textContent = "";
    ((top && top.members) || []).forEach(function (m) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      link(a, m.name, root + "/users/" + encodeURIComponent(m.id));
      li.appendChild(a);
      list.appendChild(li);
    });
    section.querySelectorAll(".ctf-podium-row").forEach(function (row) {
      var team = teams[Number(row.getAttribute("data-place")) - 1];
      row.hidden = !team;
      if (!team) return;
      link(row.querySelector(".ctf-podium-row-name"), team.name, team.account_url);
      row.querySelector(".ctf-podium-row-score").textContent = points(team.score);
    });
    section.querySelector(".ctf-podium-rows").hidden = teams.length < 2;
  }

  function hasPlaces(data) {
    return !!data && BRACKETS.some(function (b) { return (data[b] || []).length > 0; });
  }

  function render(data) {
    var state = data ? data.state : "tba";
    var final = state === "final";
    if (final) {
      result = data;
      BRACKETS.forEach(function (b) {
        fillLane(page.querySelector('.ctf-podium-lane[data-bracket="' + b + '"]'), data[b] || []);
      });
      page.classList.toggle("ctf-podium-fresh", seen);
    } else {
      seen = true;
    }
    page.setAttribute("data-state", state);
    var early = !final && !!data && data.presenter;
    page.querySelector(".ctf-podium-present").hidden = !(early || (final && hasPlaces(data)));
    page.querySelector(".ctf-podium-note").hidden = !early;
    clearTimeout(timer);
    if (!final) timer = setTimeout(load, POLL_MS);
  }

  function load() { return ask(false).then(render); }

  // ---- presenter mode: one lane at a time, one place per click --------------
  // AI-MODUS first, then Classic; each lane keeps how many places it has shown
  // (counted from the last), so the tabs can go back and forth between them.
  var ORDER = ["ai", "normal"];
  var COLORS = { normal: ["#5ab0ff", "#9dd0ff", "#e6eef5", "#2f7fd0"], ai: ["#ff2e00", "#ff7a00", "#ffc400", "#fff3b0"] };
  var GLYPHS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#$%&@{}_";
  var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var teams = {};   // lane -> its top places
  var shown = {};   // lane -> places revealed so far
  var lanes = [];   // the lanes with a team, in ORDER
  var lane = "";
  var roll = null;  // the reveal that is animating: {slot, timer}

  function slotOf(place) {
    return stage.querySelector('.ctf-podium-slot[data-place="' + place + '"]');
  }

  function other() {
    return lanes.filter(function (b) { return b !== lane && shown[b] < teams[b].length; })[0];
  }

  function settle() {
    if (!roll) return;
    clearInterval(roll.timer);
    roll.slot.classList.remove("is-rolling");
    roll = null;
  }

  function draw() {
    settle();
    var list = teams[lane];
    var n = list.length;
    stage.setAttribute("data-lane", lane);
    stage.querySelectorAll("[data-lane-name]").forEach(function (el) {
      el.hidden = el.getAttribute("data-lane-name") !== lane;
    });
    stage.querySelector(".ctf-podium-tabs").hidden = lanes.length < 2;
    stage.querySelectorAll("[data-lane-tab]").forEach(function (el) {
      el.setAttribute("aria-pressed", String(el.getAttribute("data-lane-tab") === lane));
    });
    stage.querySelectorAll(".ctf-podium-slot").forEach(function (slot) {
      var place = Number(slot.getAttribute("data-place"));
      var team = list[place - 1];
      var open = !!team && place > n - shown[lane];
      slot.style.visibility = team ? "" : "hidden";
      slot.classList.remove("is-landed");
      slot.classList.toggle("is-shown", open);
      slot.querySelector(".ctf-podium-slot-name").textContent = open ? team.name : "? ? ?";
      slot.querySelector(".ctf-podium-slot-sealed").hidden = open;
      slot.querySelector(".ctf-podium-slot-points").hidden = !open;
      slot.querySelector(".ctf-podium-slot-value").textContent = open ? points(team.score) : "";
    });
    var next = other();
    var label = shown[lane] < n ? String(n - shown[lane]) : next ? "next-" + next : "done";
    stage.querySelectorAll("[data-label]").forEach(function (el) {
      el.hidden = el.getAttribute("data-label") !== label;
    });
  }

  function confetti(colors) {
    for (var i = 0; i < 90; i++) {
      var bit = document.createElement("span");
      bit.className = "ctf-podium-bit";
      bit.style.left = Math.random() * 100 + "vw";
      bit.style.background = colors[i % colors.length];
      bit.style.setProperty("--dx", (Math.random() * 30 - 15).toFixed(1) + "vw");
      bit.style.setProperty("--rot", Math.round(Math.random() * 1440 - 720) + "deg");
      bit.style.animationDuration = (2.2 + Math.random() * 2.2).toFixed(2) + "s";
      bit.style.animationDelay = (Math.random() * 0.6).toFixed(2) + "s";
      bit.addEventListener("animationend", function () { this.remove(); });
      stage.appendChild(bit);
    }
  }

  // The place's name spins through random characters, then lands letter by
  // letter; the champion spins longer and gets confetti.
  function reveal(place) {
    var slot = slotOf(place);
    var team = teams[lane][place - 1];
    var colors = COLORS[lane];
    draw();
    function land() {
      settle();
      slot.querySelector(".ctf-podium-slot-name").textContent = team.name;
      slot.querySelector(".ctf-podium-slot-sealed").hidden = true;
      slot.querySelector(".ctf-podium-slot-points").hidden = false;
      void slot.offsetWidth;  // restart the landing animation
      slot.classList.add("is-landed");
      if (place === 1 && !calm) confetti(colors);
    }
    if (calm) return land();
    var name = slot.querySelector(".ctf-podium-slot-name");
    var chars = Array.from(team.name);
    var ticks = place === 1 ? 44 : 24;  // 50 ms each
    var tick = 0;
    function spin(fixed) {
      name.textContent = chars.map(function (c, i) {
        return i < fixed || c === " " ? c : GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
      }).join("");
    }
    slot.classList.add("is-rolling");
    slot.querySelector(".ctf-podium-slot-sealed").hidden = false;
    slot.querySelector(".ctf-podium-slot-points").hidden = true;
    spin(0);
    roll = {
      slot: slot,
      timer: setInterval(function () {
        tick++;
        if (tick >= ticks) return land();
        spin(Math.floor(chars.length * Math.max(0, tick - ticks * 0.5) / (ticks * 0.5)));
      }, 50),
    };
  }

  function show(b) {
    lane = b;
    draw();
  }

  function step(by) {
    var n = teams[lane].length;
    if (by < 0) {
      if (shown[lane] > 0) shown[lane]--;
      return draw();
    }
    // A click while a name is still spinning lands it; the next click moves on.
    if (roll) return draw();
    if (shown[lane] < n) {
      shown[lane]++;
      return reveal(n - shown[lane] + 1);
    }
    var next = other();
    return next ? show(next) : close();
  }

  function onKey(e) {
    if (e.key === "Escape") return close();
    var forward = e.key === " " || e.key === "Enter" || e.key === "ArrowRight" || e.key === "PageDown";
    var back = e.key === "ArrowLeft" || e.key === "PageUp";
    if (!forward && !back) return;
    // Space and Enter on a focused button are that button's own click.
    if ((e.key === " " || e.key === "Enter") && e.target && e.target.closest && e.target.closest("button")) return;
    e.preventDefault();
    step(forward ? 1 : -1);
  }

  function open() {
    // An admin's presenter asks for the result itself: before the freeze is
    // lifted it is the only answer that has the places.
    ask(true).then(function (data) {
      data = hasPlaces(data) ? data : result;
      if (!hasPlaces(data)) return;
      teams = {};
      shown = {};
      lanes = ORDER.filter(function (b) { return (data[b] || []).length > 0; });
      lanes.forEach(function (b) { teams[b] = data[b]; shown[b] = 0; });
      lane = lanes[0];
      draw();
      stage.hidden = false;
      document.documentElement.style.overflow = "hidden";
      document.addEventListener("keydown", onKey);
      stage.focus();
      if (stage.requestFullscreen) stage.requestFullscreen().catch(function () {});
    });
  }

  function close() {
    if (stage.hidden) return;
    settle();
    stage.querySelectorAll(".ctf-podium-bit").forEach(function (bit) { bit.remove(); });
    stage.hidden = true;
    document.documentElement.style.overflow = "";
    document.removeEventListener("keydown", onKey);
    if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(function () {});
    page.querySelector(".ctf-podium-present").focus();
  }

  page.querySelector(".ctf-podium-present").addEventListener("click", open);
  stage.querySelector(".ctf-podium-next").addEventListener("click", function () { step(1); });
  stage.querySelector(".ctf-podium-close").addEventListener("click", close);
  stage.querySelectorAll("[data-lane-tab]").forEach(function (tab) {
    tab.addEventListener("click", function () { show(tab.getAttribute("data-lane-tab")); });
  });
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden && page.getAttribute("data-state") !== "final") load();
  });

  load().then(function () {
    if (location.hash === "#present" && !page.querySelector(".ctf-podium-present").hidden) open();
  });
})();
</script>
