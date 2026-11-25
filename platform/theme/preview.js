/* =========================================================================
   PREVIEW BOOT SCREEN AND COUNTDOWN  -  ctf.sh up --preview only
   (platform/theme/README.md).
   On the first page of a browser session: a retro boot sequence for 5 seconds,
   then the board. A click or any key skips it. preview.head.js has covered the
   page already (html.pv-booting) and decides whether it plays: a session cookie
   keeps it to once per browser session, so new tabs don't replay it. With
   reduced motion it shows a still frame for 1.5 seconds instead.
   Under the page title, a countdown to the start of the event
   (CTF_PREVIEW_EVENT_START). The words are "preview.*" in i18n.strings.js.
   ========================================================================= */

// When the event starts: 18 November 2026 at 16:00 Oslo time (CET, UTC+1).
var CTF_PREVIEW_EVENT_START = Date.parse("2026-11-18T16:00:00+01:00");
var CTF_PREVIEW_EVENT_LABEL = "2026-11-18 16:00 Europe/Oslo";

(function () {
  "use strict";

  var root = document.documentElement;
  var COOKIE = "ctf-preview-booted";
  var DURATION = 5000; // ms the boot screen stays up
  var BAR_WIDTH = 28;  // characters in the progress bar
  // When each line of "preview.boot" (i18n.strings.js) shows, in ms after the
  // start; a leading "[  OK  ]" is coloured.
  var TIMES = [0, 350, 700, 1050, 1500, 1800, 2100, 2400, 2700, 3100, 3700];
  var OK = "[  OK  ]";

  var t = window.ctfI18n.t;
  function lines() {
    var v = t("preview.boot", { when: CTF_PREVIEW_EVENT_LABEL });
    return (Array.isArray(v) ? v : [v]).map(function (text, i) {
      var last = TIMES[TIMES.length - 1];
      return [i < TIMES.length ? TIMES[i] : last + 300 * (i - TIMES.length + 1), text];
    });
  }

  function reducedMotion() {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }

  function bar(fraction) {
    var n = Math.round(fraction * BAR_WIDTH);
    return "[" + new Array(n + 1).join("#") + new Array(BAR_WIDTH - n + 1).join(".") + "] " +
      Math.round(fraction * 100) + "%";
  }

  function boot() {
    if (!root.hasAttribute("data-ctf-preview") || !root.classList.contains("pv-booting")) return;
    try { document.cookie = COOKIE + "=1; path=/; SameSite=Lax"; } catch (e) {}

    var box = document.createElement("div");
    box.id = "pv-boot";
    box.setAttribute("aria-hidden", "true");
    var log = document.createElement("div");
    log.className = "pv-boot-log";
    var caret = document.createElement("span");
    caret.className = "pv-caret";
    caret.textContent = "█";
    log.appendChild(caret);
    var progress = document.createElement("div");
    progress.className = "pv-boot-bar";
    var skip = document.createElement("div");
    skip.className = "pv-boot-skip";
    skip.textContent = t("preview.skip");
    box.appendChild(log);
    box.appendChild(progress);
    box.appendChild(skip);
    document.body.appendChild(box);

    function addLine(text) {
      var line = document.createElement("div");
      if (text.indexOf(OK) === 0) {
        var tag = document.createElement("span");
        tag.className = "pv-ok";
        tag.textContent = OK;
        line.appendChild(tag);
        line.appendChild(document.createTextNode(text.slice(OK.length)));
      } else {
        line.textContent = text;
      }
      log.insertBefore(line, caret);
    }

    var timers = [], ticker = 0, done = false, started = Date.now();
    function finish() {
      if (done) return;
      done = true;
      timers.forEach(clearTimeout);
      clearInterval(ticker);
      document.removeEventListener("keydown", onKey, true);
      box.classList.add("pv-boot-out");
      root.classList.remove("pv-booting");
      setTimeout(function () { if (box.parentNode) box.parentNode.removeChild(box); }, 400);
    }
    // Caught first and stopped, so the key doesn't also reach the page beneath.
    function onKey(e) {
      e.preventDefault();
      e.stopPropagation();
      finish();
    }
    box.addEventListener("click", finish);
    document.addEventListener("keydown", onKey, true);

    var bootLines = lines();
    if (reducedMotion()) {
      bootLines.forEach(function (l) { addLine(l[1]); });
      progress.textContent = bar(1);
      timers.push(setTimeout(finish, 1500));
      return;
    }
    bootLines.forEach(function (l) {
      timers.push(setTimeout(function () { addLine(l[1]); }, l[0]));
    });
    progress.textContent = bar(0);
    ticker = setInterval(function () {
      progress.textContent = bar(Math.min(1, (Date.now() - started) / DURATION));
    }, 100);
    timers.push(setTimeout(finish, DURATION));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();

/* The countdown: `$ ./countdown`, then the time left in big digits, ticking every
   second, under the page title (the board's "$ cd challenges"). Once the start
   has passed it says so and stops. */
(function () {
  "use strict";

  var root = document.documentElement;
  var START = CTF_PREVIEW_EVENT_START;
  var L = window.ctfI18n;

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  // bound to its key (i18n.js), so the language switch rewrites it
  var bind = L.bind;

  function make(tag, cls, text) {
    var el = document.createElement(tag);
    el.className = cls;
    if (text) el.textContent = text;
    return el;
  }

  function countdown() {
    if (!root.hasAttribute("data-ctf-preview") || isNaN(START)) return;
    var host = document.querySelector(".jumbotron .container");
    if (!host || document.getElementById("pv-countdown")) return;

    var box = make("div", "pv-countdown");
    box.id = "pv-countdown";
    box.setAttribute("role", "timer");
    L.bindAttr(box, "aria-label", "preview.countdown");
    var cmd = make("div", "pv-cd-cmd");
    cmd.appendChild(make("span", "pv-cd-prompt", "$ "));
    cmd.appendChild(document.createTextNode('./countdown --until "' + CTF_PREVIEW_EVENT_LABEL + '"'));
    var clock = make("div", "pv-cd-clock");
    var note = make("div", "pv-cd-note");
    box.appendChild(cmd);
    box.appendChild(clock);
    box.appendChild(note);
    host.appendChild(box);

    var timer = 0;
    function tick() {
      var left = Math.max(0, Math.floor((START - Date.now()) / 1000));
      var d = Math.floor(left / 86400), h = Math.floor(left % 86400 / 3600);
      var m = Math.floor(left % 3600 / 60), s = left % 60;
      clock.textContent = "T-" + pad(d) + "d " + pad(h) + "h " + pad(m) + "m " + pad(s) + "s";
      if (left > 0) {
        bind(note, "preview.until");
        return;
      }
      box.classList.add("pv-cd-done");
      bind(note, "preview.started");
      clearInterval(timer);
    }
    tick();
    if (!box.classList.contains("pv-cd-done")) timer = setInterval(tick, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", countdown);
  } else {
    countdown();
  }
})();

/* A solve, the preview's way. Nothing is saved on the server in a preview, so the
   challenges you solve are kept in this browser only (localStorage,
   SOLVED_KEY: their names), and the board marks them `[  OK  ] solved`. A new
   solve gets a terminal of its own over
   the page for about three seconds, typing out the capture and then ACCESS
   GRANTED with green glyphs raining behind it; it never takes a click. A
   challenge already in the list just gets CTFd's own "Correct". Reduced motion
   shows the terminal at once, without the rain. */
(function () {
  "use strict";

  var root = document.documentElement;
  if (!root.hasAttribute("data-ctf-preview")) return;
  var SOLVED_KEY = "ctf-preview-solved";
  var WIN_MS = 3600;
  var GLYPHS = "01{}<>/$#*%&@ABCDEF0123456789";
  var L = window.ctfI18n;
  var t = L.t;

  function lc(s) { return String(s || "").trim().toLowerCase(); }
  function reducedMotion() {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }
  function make(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }

  // The solved names, lower case; an empty list when storage is off or garbled.
  function solved() {
    try {
      var list = JSON.parse(localStorage.getItem(SOLVED_KEY) || "[]");
      return Array.isArray(list) ? list.map(lc) : [];
    } catch (e) { return []; }
  }
  // Adds name; true if it wasn't in the list yet (or the list can't be kept).
  function addSolved(name) {
    var list = solved(), key = lc(name);
    if (!key || list.indexOf(key) !== -1) return false;
    list.push(key);
    try { localStorage.setItem(SOLVED_KEY, JSON.stringify(list)); } catch (e) {}
    return true;
  }

  function tiles() { return document.querySelectorAll(".challenge-button"); }
  function tileName(btn) {
    var p = btn.querySelector(".challenge-inner p");
    return p ? lc(p.textContent) : "";
  }

  // Mark the board's solved tiles. Only changes what differs, so the board
  // observer below doesn't loop.
  function markBoard() {
    var list = solved(), all = tiles();
    for (var i = 0; i < all.length; i++) {
      var on = list.indexOf(tileName(all[i])) !== -1;
      if (all[i].classList.contains("pv-solved") !== on) all[i].classList.toggle("pv-solved", on);
    }
  }

  function rain(layer) {
    if (reducedMotion() || !layer.animate) return;
    var w = window.innerWidth, h = window.innerHeight;
    for (var i = 0; i < 70; i++) {
      var g = make("i", "pv-win-glyph", GLYPHS.charAt(Math.floor(Math.random() * GLYPHS.length)));
      g.style.left = Math.round(Math.random() * w) + "px";
      layer.appendChild(g);
      g.animate([
        { transform: "translateY(-40px)", opacity: 0 },
        { opacity: 1, offset: 0.1 },
        { opacity: 0.8, offset: 0.8 },
        { transform: "translateY(" + (h + 40) + "px)", opacity: 0 }
      ], { duration: 1600 + Math.random() * 1600, delay: Math.random() * 600, easing: "linear", fill: "both" });
    }
  }

  function celebrate(c) {
    var old = document.getElementById("pv-win");
    if (old) old.parentNode.removeChild(old);
    var layer = make("div", "pv-win");
    layer.id = "pv-win";
    layer.setAttribute("aria-hidden", "true"); // CTFd's "Correct" alert says it in words
    var term = make("div", "pv-win-term");
    var lines = [
      ["pv-win-cmd", "$ ./capture --flag " + (lc(c.name) || "challenge")],
      ["pv-win-ok", t("preview.win.ok") + (c.points != null ? t("preview.win.points", { points: c.points }) : "")],
      ["pv-win-big", t("preview.win.granted")]
    ];
    var still = reducedMotion();
    lines.forEach(function (l, i) {
      var el = make("div", l[0], l[1]);
      if (!still) el.style.animationDelay = (i * 0.35) + "s";
      term.appendChild(el);
    });
    layer.appendChild(term);
    document.body.appendChild(layer);
    rain(layer);
    setTimeout(function () { layer.classList.add("pv-win-out"); }, WIN_MS - 400);
    setTimeout(function () { if (layer.parentNode) layer.parentNode.removeChild(layer); }, WIN_MS);
  }

  function onAttempt(e) {
    try {
      var c = e.detail; // the challenge's name and points come with it (ai-mode.head.js)
      if (!c || c.status !== "correct") return;
      if (!addSolved(c.name)) return;
      markBoard();
      celebrate(c);
    } catch (err) {}
  }

  function start() {
    document.addEventListener("ctf-attempt", onAttempt);
    markBoard();
    // The board renders late and again after each answer; another tab's solve
    // arrives through the storage event.
    try {
      new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          var t = mutations[i].target;
          if (t.closest && t.closest("#pv-win, #pv-countdown")) continue;
          markBoard();
          return;
        }
      }).observe(document.body, { childList: true, subtree: true });
    } catch (e) {}
    window.addEventListener("storage", function (e) { if (e.key === SOLVED_KEY) markBoard(); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
