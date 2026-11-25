<!--
  The winners page (route "winners"), synced into CTFd by ./ctf.sh up (see
  docs/language.md). The imported backup keeps it hidden; show it in Admin ->
  Pages at the prize-giving. One file for both languages, like the front page:
  its script must run once, so each text is a block per language
  (class="ctf-lang"). Each lane's champion is the first team on its bracket's
  scoreboard, read from the ai_brackets plugin (/ai-brackets/scoreboard); without
  the plugin a card says "To be announced".
-->
<style>
  .winner-card { border: 1px solid rgba(255,255,255,.08); transition: transform .15s, box-shadow .15s; }
  .winner-card:hover { transform: translateY(-2px); box-shadow: 0 0 0 2px rgba(141,255,97,.2), 0 12px 28px rgba(0,0,0,.45); }
  .winner-pill { font-size: .8rem; padding: .2rem .55rem; border-radius: 999px; background: rgba(141,255,97,.12); color: #8dff61; border: 1px solid rgba(141,255,97,.3); }
  .glow { text-shadow: 0 0 6px rgba(141,255,97,.55); }
  .winner-card[data-bracket="ai"] .winner-pill { background: rgba(255,122,0,.12); color: #ffc400; border-color: rgba(255,122,0,.4); }
  .winner-card[data-bracket="ai"] .glow { text-shadow: 0 0 8px rgba(255,90,0,.7); }
  .winner-name { font-size: 1.25rem; font-weight: 700; overflow-wrap: anywhere; }
  .meta { opacity: .8; font-size: .9rem; }
  ul.member-list { margin: .25rem 0 1rem; padding-left: 1.2rem; }
  ul.member-list li { margin: .1rem 0; overflow-wrap: anywhere; }
  @media (prefers-reduced-motion: reduce) {
    .winner-card, .winner-card:hover { transition: none; transform: none; }
  }
</style>

<div class="pt-4 pb-5">
  <div class="text-center mb-4">
    <h1 class="mt-3"><span class="ctf-lang" lang="no">Vinnerne</span><span class="ctf-lang" lang="en">The winners</span></h1>
    <p class="lead mb-0"><span class="ctf-lang" lang="no">To baner, to vinnere.</span><span class="ctf-lang" lang="en">Two lanes, two winners.</span></p>
    <small class="text-muted"><span class="ctf-lang" lang="no">Klassisk og AI-MODUS kårer hver sin mester.</span><span class="ctf-lang" lang="en">Classic and AI-MODUS each crown their own champion.</span></small>
  </div>
  <div class="row g-4 justify-content-center">
    <div class="col-12 col-md-6 col-lg-5">
      <div class="card winner-card h-100" data-bracket="normal">
        <div class="card-header d-flex align-items-center justify-content-between">
          <span class="winner-pill"><span class="ctf-lang" lang="no">Vinner</span><span class="ctf-lang" lang="en">Winner</span></span>
          <span class="text-muted small"><span class="ctf-lang" lang="no">Klassisk</span><span class="ctf-lang" lang="en">Classic</span></span>
        </div>
        <div class="card-body">
          <h3 class="card-title glow mb-2"><span class="ctf-lang" lang="no">Klassisk-mester</span><span class="ctf-lang" lang="en">Classic champion</span></h3>
          <p class="mb-1"><a class="winner-name text-info"><span class="ctf-lang" lang="no">Kunngjøres snart</span><span class="ctf-lang" lang="en">To be announced</span></a></p>
          <ul class="member-list"></ul>
          <p class="winner-score mb-1" hidden><span class="winner-points"></span> <span class="ctf-lang" lang="no">poeng</span><span class="ctf-lang" lang="en">points</span></p>
          <p class="meta mb-0"><span class="ctf-lang" lang="no">Flest poeng i Klassisk-ligaen. Ingen AI.</span><span class="ctf-lang" lang="en">Most points in the Classic bracket. No AI.</span></p>
        </div>
      </div>
    </div>
    <div class="col-12 col-md-6 col-lg-5">
      <div class="card winner-card h-100" data-bracket="ai">
        <div class="card-header d-flex align-items-center justify-content-between">
          <span class="winner-pill"><span class="ctf-lang" lang="no">Vinner</span><span class="ctf-lang" lang="en">Winner</span></span>
          <span class="text-muted small">AI-MODUS</span>
        </div>
        <div class="card-body">
          <h3 class="card-title glow mb-2"><span class="ctf-lang" lang="no">AI-MODUS-mester</span><span class="ctf-lang" lang="en">AI-MODUS champion</span></h3>
          <p class="mb-1"><a class="winner-name text-info"><span class="ctf-lang" lang="no">Kunngjøres snart</span><span class="ctf-lang" lang="en">To be announced</span></a></p>
          <ul class="member-list"></ul>
          <p class="winner-score mb-1" hidden><span class="winner-points"></span> <span class="ctf-lang" lang="no">poeng</span><span class="ctf-lang" lang="en">points</span></p>
          <p class="meta mb-0"><span class="ctf-lang" lang="no">Flest poeng i AI-modus-ligaen. AI forventes.</span><span class="ctf-lang" lang="en">Most points in the AI-modus bracket. AI expected.</span></p>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
// Fills each card with the first team on its bracket's scoreboard. Names are
// what players typed, so they only ever go in as text.
(function () {
  const root = (window.init && window.init.urlRoot) || "";
  document.querySelectorAll(".winner-card[data-bracket]").forEach((card) => {
    fetch(root + "/ai-brackets/scoreboard?bracket=" + card.getAttribute("data-bracket"), { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : null))
      .then((res) => {
        const top = res && Array.isArray(res.data) ? res.data[0] : null;
        if (!top) return;
        const name = card.querySelector(".winner-name");
        name.textContent = top.name;
        if (top.account_url) name.setAttribute("href", top.account_url);
        card.querySelector(".winner-points").textContent = top.score;
        card.querySelector(".winner-score").hidden = false;
        const list = card.querySelector(".member-list");
        (top.members || []).forEach((m) => {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.className = "text-info";
          a.setAttribute("href", root + "/users/" + encodeURIComponent(m.id));
          a.textContent = m.name;
          li.appendChild(a);
          list.appendChild(li);
        });
      })
      .catch(() => {});
  });
})();
</script>
