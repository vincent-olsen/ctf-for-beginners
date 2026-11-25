/* AI-modus early bootstrap - runs in <head> before paint so there is no flash.
   The full behaviour (lane control, board filter, effects) is in ai-mode.js. */
(function () {
  // A preview (ctf.sh up --preview) has only the Classic lane.
  var preview = document.documentElement.hasAttribute("data-ctf-preview");
  try {
    if (!preview && localStorage.getItem("ctf-ai-mode") === "on") {
      document.documentElement.setAttribute("data-ai-mode", "on");
    }
  } catch (e) {}
  // The AI Slop-o-meter's level (ai-mode.js): -1 WEB 1.0, 1 CALM, 2 BURN (the
  // default) or 3 AI HORROR, on <html> before the first paint so the page starts
  // with the right layers. The old Effects button stored "off": that is level 1.
  var fx = "2";
  try {
    var saved = localStorage.getItem("ctf-ai-fx");
    if (saved === "off") fx = "1";
    else if (/^(-1|1|2|3)$/.test(saved || "")) fx = saved;
  } catch (e) {}
  document.documentElement.setAttribute("data-ai-fx", fx);

  // One look only: force CTFd's dark palette (the toggle is hidden in ai-mode.css).
  // The Classic skin and the front-page countdown only style the dark theme, so a
  // light background would leave them unreadable. Pinning localStorage keeps
  // CTFd's own color_mode_switcher on dark across OS theme changes too.
  try { localStorage.setItem("theme", "dark"); } catch (e) {}
  document.documentElement.setAttribute("data-bs-theme", "dark");

  // Per-bracket scoreboard: on /scoreboard, CTFd's own page asks for
  // /api/v1/scoreboard and /api/v1/scoreboard/top/<n>; send those to the
  // ai_brackets plugin (platform/plugins/) for the board the page shows: the
  // one picked in its All | Classic | AI-MODUS tabs (ai-mode.js), which start on
  // the selected lane's. "All" lists every team once per lane it plays in, each
  // with that lane's score (the plugin's bracket=all), and the lane goes after
  // the name here, "Team (Klassisk)" and "Team (AI-MODUS)", so the table and the
  // graph's legend tell the two apart. The names are in the page's language as
  // it was when they were fetched; ai-mode.js fetches again when it changes.
  // CTFd's JS keeps its own reference to window.fetch, taken when its modules
  // load, so the wrapper has to be in place before then, which is why it lives
  // here.
  //  - Any plugin failure falls back to the stock, combined scoreboard (both
  //    lanes added together); after a 404 (no plugin) the plugin isn't asked
  //    again.
  //  - The bracket comes from data-ctf-board ("all", "normal" or "ai"): set here
  //    from ?board= in the address, then by ai-mode.js with the tabs. Without it,
  //    from data-ai-mode, the lane.
  //  - Latest wins: a lane switch or CTFd's 5-minute refresh can overlap an earlier
  //    request, so every caller of an endpoint gets the answer to the latest
  //    request for it, whichever order the responses arrive in.
  //  - window.ctfAiBoard and an "ai-board" event on document tell ai-mode.js
  //    which board, and which source, is on screen: "plugin", or "stock" (CTFd's
  //    own, combined, as a fallback).
  try {
    if (!/\/scoreboard\/?$/.test(location.pathname) || !window.fetch) return;
    // A board asked for in the address (ai-mode.js keeps the picked tab there).
    var asked = /[?&]board=(all|normal|ai)(?:&|$)/.exec(location.search);
    if (asked && !preview) document.documentElement.setAttribute("data-ctf-board", asked[1]);
    var nativeFetch = window.fetch;
    var SCOREBOARD_API = /^(.*?)\/api\/v1\/scoreboard(\/top\/\d+)?(?:\?(.*))?$/;
    var board = window.ctfAiBoard = { plugin: null, bracket: null, source: null };
    var latest = {}; // endpoint -> promise of the latest request's result

    // The All board's answer with each entry's lane after its name. Both
    // endpoints keep their entries in data, a list or an object by place.
    var withLanes = function (r) {
      return r.clone().json().then(function (body) {
        var data = body && body.data, i18n = window.ctfI18n;
        if (data && typeof data === "object") {
          Object.keys(data).forEach(function (k) {
            var e = data[k];
            if (!e || typeof e.name !== "string") return;
            if (e.ai_bracket !== "normal" && e.ai_bracket !== "ai") return;
            e.name = i18n.t("board.entry", {
              name: e.name, lane: i18n.t(e.ai_bracket === "ai" ? "lane.ai" : "lane.classic")
            });
          });
        }
        return new Response(JSON.stringify(body), {
          status: r.status, statusText: r.statusText, headers: r.headers
        });
      }).catch(function () { return r; });
    };

    var settle = function (kind, p) {
      function follow() { return settle(kind, latest[kind]); }
      return p.then(function (res) {
        if (latest[kind] !== p) return follow();
        board.bracket = res.bracket;
        board.source = res.source;
        try {
          document.dispatchEvent(new CustomEvent("ai-board", {
            detail: { bracket: res.bracket, source: res.source }
          }));
        } catch (e) {}
        // Each caller gets its own copy; the original body is never read.
        return res.response.clone();
      }, function (err) {
        if (latest[kind] !== p) return follow();
        throw err;
      });
    };

    window.fetch = function (input, init) {
      var m = typeof input === "string" ? input.match(SCOREBOARD_API) : null;
      if (!m) return nativeFetch.apply(this, arguments);
      var self = this, args = arguments;
      var root = document.documentElement;
      var bracket = root.getAttribute("data-ctf-board");
      if (bracket !== "all" && bracket !== "normal" && bracket !== "ai") {
        bracket = root.getAttribute("data-ai-mode") === "on" ? "ai" : "normal";
      }
      function stock() {
        return nativeFetch.apply(self, args).then(function (r) {
          return { response: r, bracket: bracket, source: "stock" };
        });
      }
      var p;
      if (board.plugin === false) {
        p = stock();
      } else {
        var url = m[1] + "/ai-brackets/scoreboard" + (m[2] || "") +
          "?bracket=" + bracket + (m[3] ? "&" + m[3] : "");
        p = nativeFetch.call(self, url, init).then(function (r) {
          if (r.ok) {
            board.plugin = true;
            var shown = bracket === "all" ? withLanes(r) : Promise.resolve(r);
            return shown.then(function (res) {
              return { response: res, bracket: bracket, source: "plugin" };
            });
          }
          if (r.status === 404) board.plugin = false;
          return stock();
        }, function () { return stock(); });
      }
      var kind = m[2] || "";
      latest[kind] = p;
      return settle(kind, p);
    };
  } catch (e) {}
})();

// Wrong-flag feedback (all lanes and a preview). CTFd's challenge window reuses
// one alert for every answer, so a second wrong flag looks exactly like the
// first. This hook sees each answer and tells ai-mode.js and preview.js with a
// "ctf-attempt" event on document: {status, before, id, name, points}, where
// before is how many wrong answers in a row the window was already showing (0 for
// none), and id, name and points are the challenge's, as sent and as the window
// showed them when the flag went off (null when unknown). Like the scoreboard
// wrapper above, it has to be in place before CTFd's modules take their copy of
// window.fetch.
//
// It also keeps the window from going blank. CTFd draws the answer from
// response.data, and an answer without it (a refused request, an error page, a
// sign-in that expired) leaves an empty box. Such an answer is handed to CTFd as
// {status: "error", message} instead, which every lane shows as a warning, in
// the page's language (i18n.js, loaded before this file).
(function () {
  try {
    if (!window.fetch) return;
    var innerFetch = window.fetch;
    var ATTEMPT = /\/api\/v1\/challenges\/attempt(?:\?|$)/;
    // CTFd's own 403 (an expired or missing CSRF token) says only this.
    var DENIED = /^You don't have the permission/;

    function t(key, vars) { return window.ctfI18n.t(key, vars); }
    function trouble(code, body) {
      var msg = body && typeof body.message === "string" ? body.message : "";
      if (code === 403 && (!msg || DENIED.test(msg))) return t("attempt.expired");
      if (msg) return msg; // the server's own words, which i18n.js translates on the page
      if (!code) return t("attempt.offline");
      return t("attempt.failed", { code: code });
    }
    function answer(fixed, code) {
      return new Response(JSON.stringify(fixed), {
        status: code || 200, headers: { "Content-Type": "application/json" }
      });
    }

    // The challenge the flag is for: its id from the request, its name and points
    // from the open window.
    function challenge(init) {
      var id = null;
      try { id = parseInt(JSON.parse(init.body).challenge_id, 10); } catch (e) {}
      var win = document.getElementById("challenge-window");
      var name = win && win.querySelector(".challenge-name");
      var value = win && win.querySelector(".challenge-value");
      var pts = value ? parseInt((value.textContent || "").replace(/[^0-9]/g, ""), 10) : NaN;
      return { id: isNaN(id) ? null : id, name: name ? name.textContent.trim() : "", points: isNaN(pts) ? null : pts };
    }

    window.fetch = function (input, init) {
      var p = innerFetch.apply(this, arguments);
      var url = typeof input === "string" ? input : (input && input.url) || "";
      if (!ATTEMPT.test(url)) return p;
      var shown = document.querySelector("#challenge-window .notification-row .alert-danger");
      var before = shown ? (parseInt(shown.getAttribute("data-ctf-fails"), 10) || 1) : 0;
      var c = challenge(init || {});
      function tell(status) {
        document.dispatchEvent(new CustomEvent("ctf-attempt", { detail: {
          status: status, before: before, id: c.id, name: c.name, points: c.points
        } }));
      }
      function failed(code, body) {
        tell("error");
        return answer({ success: false, data: { status: "error", message: trouble(code, body) } }, code);
      }
      return p.then(function (r) {
        return r.clone().json().then(function (body) {
          if (!body || typeof body !== "object" || !body.data || typeof body.data !== "object") return failed(r.status, body);
          tell(body.data.status);
          return r;
        }, function () { return failed(r.status, null); }); // not JSON: an error page, a sign-in page
      }, function () { return failed(0, null); }); // no answer at all (a sign-in redirect off-site, offline)
    };
  } catch (e) {}
})();
