/* =========================================================================
   SOLVE LIMITS  -  a challenge that locks once it has been solved
   Linked from CTFd's theme_footer by ctf.sh, after first-blood.js, except in a
   preview (which saves no solve).

   A challenge with `max_solves: N` in its metadata.yml (paper: a flag printed
   on paper and hidden in the venue, N = 1) takes N solves; the
   ctf_solve_limit plugin (platform/plugins/) refuses flags after that and
   lists the limited challenges at /solve-limit/status. On the Challenges page
   this file asks it every 20 seconds while the tab is visible, and for a
   locked challenge marks its tile on the board and, in its window, says who
   found it and switches the flag field off (not for the team that solved it:
   CTFd shows them their solve).

   Team names are other people's text: they only ever go in as textContent.
   Every word comes from i18n.strings.js (window.ctfI18n).
   ========================================================================= */
(function () {
  "use strict";

  var root = document.documentElement;
  if (root.hasAttribute("data-ctf-preview")) return;
  if (!/\/challenges\/?$/.test(location.pathname)) return;

  var I = window.ctfI18n;
  var POLL = 20000;
  var locked = {}; // lower-case challenge name -> its status row, locked ones only

  var css = document.createElement("style");
  css.textContent =
    ".challenge-button.ctf-limit-locked:not(.challenge-solved) { opacity:.55; filter:saturate(.4); }" +
    ".challenge-button.ctf-limit-locked .challenge-inner p::after { content:' \\1F512'; }" +
    ".ctf-limit-note { margin:1rem 0; padding:.75rem 1rem; border:1px solid currentColor; border-radius:.5rem;" +
    " text-align:center; font-weight:600; }" +
    ".ctf-limit-note b { display:block; font-size:1.25em; }";
  document.head.appendChild(css);

  function lc(s) { return String(s || "").trim().toLowerCase(); }
  function urlRoot() {
    return (window.init && window.init.urlRoot) || (window.CTFd && window.CTFd.config && window.CTFd.config.urlRoot) || "";
  }

  function markBoard() {
    var tiles = document.querySelectorAll(".challenge-button");
    for (var i = 0; i < tiles.length; i++) {
      var p = tiles[i].querySelector(".challenge-inner p");
      var on = !!(p && locked[lc(I.sourceText(p))]);
      if (tiles[i].classList.contains("ctf-limit-locked") !== on) tiles[i].classList.toggle("ctf-limit-locked", on);
    }
  }

  function solvedByMe(name) {
    var tiles = document.querySelectorAll(".challenge-button.challenge-solved");
    for (var i = 0; i < tiles.length; i++) {
      var p = tiles[i].querySelector(".challenge-inner p");
      if (p && lc(I.sourceText(p)) === name) return true;
    }
    return false;
  }

  function markWindow() {
    var win = document.getElementById("challenge-window");
    var nameEl = win && win.querySelector(".challenge-name");
    if (!nameEl) return;
    var name = lc(I.sourceText(nameEl)), row = locked[name];
    var note = win.querySelector(".ctf-limit-note");
    if (!row) { if (note) note.remove(); return; }
    var by = row.by.join(", ");
    if (!note) {
      note = document.createElement("div");
      note.className = "ctf-limit-note";
      note.setAttribute("role", "status");
      note.appendChild(document.createElement("span"));
      var who = document.createElement("b");
      who.setAttribute("data-ctf-no-i18n", "");
      note.appendChild(who);
      var desc = win.querySelector(".challenge-desc");
      if (desc && desc.parentNode) desc.parentNode.insertBefore(note, desc);
      else nameEl.parentNode.insertBefore(note, nameEl.nextSibling);
    }
    I.bind(note.firstChild, by ? "limit.found.by" : "limit.found");
    if (note.lastChild.textContent !== by) note.lastChild.textContent = by;
    if (solvedByMe(name)) return;
    var fields = win.querySelectorAll("#challenge-input, #challenge-submit");
    for (var i = 0; i < fields.length; i++) if (!fields[i].disabled) fields[i].disabled = true;
  }

  function apply() { markBoard(); markWindow(); }

  function poll() {
    if (document.hidden) return;
    fetch(urlRoot() + "/solve-limit/status", { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (res) {
        if (!res || !res.data) return;
        var next = {};
        Object.keys(res.data).forEach(function (id) {
          var row = res.data[id];
          if (row && row.locked) next[lc(row.name)] = { by: Array.isArray(row.by) ? row.by.map(String) : [] };
        });
        locked = next;
        apply();
      })
      .catch(function () { /* no plugin, or logged out: nothing is marked */ });
  }

  // The board and the window are drawn (and redrawn) by CTFd: mark them again
  // after each change, once per frame.
  var queued = false;
  new MutationObserver(function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; apply(); });
  }).observe(document.body, { childList: true, subtree: true });

  poll();
  setInterval(poll, POLL);
  document.addEventListener("visibilitychange", poll);
})();
