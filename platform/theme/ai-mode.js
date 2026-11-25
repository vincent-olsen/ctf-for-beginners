/* =========================================================================
   AI-MODUS  -  lane control + challenge-board filtering + fun mode
   Injected into CTFd's theme_footer by ctf.sh (see platform/theme/README.md).

   Two brackets ("lanes") share one CTFd:
     - Classic  (off): the normal challenges (categories WITHOUT the "ai-" prefix)
     - AI-modus (on) : the hard AI challenges (categories starting with "ai-")
   The real separation is the category name; this script filters the board to
   match the lane, opens the scoreboard on that bracket's ranking (scored by the
   ai_brackets plugin) with All | Classic | AI-MODUS tabs for the other boards,
   shows the lane's rule on the Challenges page, and in
   AI-modus runs the fun mode: boot sequence, drawn flames with a faint matrix
   rain behind them, a line above the title with how much of the bracket you
   have rooted, a final-boss row for the ai-llm category, a flame rating on
   each tile and a random screen flicker that gets rarer the longer you play;
   the AI Slop-o-meter, bottom left, picks how much of it: -1 WEB 1.0 (the board
   in 2003), 1 CALM (no boot, flames, rain, CRT layers or flicker), 2 BURN (the
   default) or 3 AI HORROR (all of it, recoloured, plus an AI assistant's worth
   of slop); the challenge window's nc port and link follow the level, so the
   terminal and web AI challenges show it too. Each AI challenge is linked to the normal ones it
   levels up (its metadata.yml builds_on, served by the ai_brackets plugin): a
   link each way in the challenge window. Everything is wrapped in try/catch
   so a theme/markup mismatch degrades gracefully (skin + labelled categories
   still work) instead of breaking the page. In a preview (ctf.sh up --preview,
   html[data-ctf-preview]) there is only the Classic lane: no lane control, no
   chooser and no lane rule (the preview has its countdown there). Every word comes
   from i18n.strings.js through i18n.js (window.ctfI18n): text that stays on
   the page is bound to its key (bind), so a NO | EN switch rewrites it in
   place.
   ========================================================================= */
(function () {
  "use strict";

  var KEY = "ctf-ai-mode";
  var AI_PREFIX = "ai-"; // AI-modus challenge categories start with this
  var SINCE_KEY = "ctf-ai-since";         // when this browser first entered AI-modus
  var NEXT_KEY = "ctf-ai-next-flicker";   // when the next flicker is due (ms epoch)
  var BOOTED_COOKIE = "ctf-ai-booted";    // session cookie: boot already shown
  var FX_KEY = "ctf-ai-fx";               // the AI Slop-o-meter's level: -1, 1, 2 or 3

  // Reduced motion is followed live (onMotionChange): turning it on mid-session
  // stops the boot, flicker and rain, not just the CSS.
  var motionQuery = null;
  var MOTION_OK = true;
  try {
    motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    MOTION_OK = !motionQuery.matches;
  } catch (e) {}

  // The AI Slop-o-meter (bottom left in AI-modus) sets a level: -1 WEB 1.0,
  // 1 CALM (no flames, matrix rain, CRT layers, flicker or boot sequence: the old
  // Effects OFF), 2 BURN (the default) or 3 AI HORROR. Its state is the attribute
  // html[data-ai-fx], which ai-mode.head.js sets from localStorage before paint,
  // so it holds for the page even where localStorage doesn't work.
  var FX_LEVELS = [-1, 1, 2, 3];
  function normLevel(v) {
    if (v === "off") return 1; // what the old Effects button stored
    var n = parseInt(v, 10);
    return FX_LEVELS.indexOf(n) === -1 ? 2 : n;
  }
  function fxLevel() { return normLevel(document.documentElement.getAttribute("data-ai-fx")); }
  function fxOn() { return fxLevel() >= 2; }      // the moving effects run
  function isSlop() { return fxLevel() === 3; }   // AI HORROR
  function isRetro() { return fxLevel() === -1; } // WEB 1.0
  // The OS setting and the player's choice: may the effects move?
  function fxOk() { return MOTION_OK && fxOn(); }

  // Set by ctfd_admin.py while a preview runs: the Classic lane only.
  var PREVIEW = document.documentElement.hasAttribute("data-ctf-preview");

  function stored(k) {
    try { return localStorage.getItem(k); } catch (e) { return null; }
  }
  function store(k, v) {
    try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, String(v)); } catch (e) {}
  }
  function storageWorks() {
    try { localStorage.setItem("ctf-ai-probe", "1"); localStorage.removeItem("ctf-ai-probe"); return true; }
    catch (e) { return false; }
  }
  function isOn() { return !PREVIEW && stored(KEY) === "on"; }
  function setOn(on) { store(KEY, on ? "on" : "off"); }
  function shownOn() { return document.documentElement.getAttribute("data-ai-mode") === "on"; }
  function urlRoot() {
    var cfg = (window.CTFd && window.CTFd.config) || window.init || {};
    return cfg.urlRoot || "";
  }
  function isAICategory(name) {
    return String(name || "").trim().toLowerCase().indexOf(AI_PREFIX) === 0;
  }
  function make(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }

  // ---- words (i18n.js) ---------------------------------------------------------
  // t(key, vars) for a text used once; bind/bindAttr for one that stays on the
  // page, which i18n.js then rewrites when the language switches. window.ctfI18n
  // is always there: without i18n.js, ctfd_admin.py's stand-in shows the keys,
  // which is ugly but never breaks the page.
  var L = window.ctfI18n;
  var t = L.t, bind = L.bind, bindAttr = L.bindAttr;
  function list(key) { var v = t(key); return Array.isArray(v) ? v : [v]; }
  function makeT(tag, cls, key, vars) { return bind(make(tag, cls), key, vars); }
  // fill every data-i18n inside el (markup written as a string)
  var fillIn = L.apply;
  // What CTFd wrote, in its English, whatever the page shows.
  var sourceText = L.sourceText;

  // ---- effect layers -------------------------------------------------------
  // Rain and flames sit behind the content (negative z-index); scanlines, the
  // rolling CRT bar and the flicker warning sit on top but never take clicks.

  // The fire's gradients, in a 0x0 SVG of their own: the flames along the
  // bottom and the flame rating on the tiles both fill from them. Kept out of
  // #ai-flames, which levels -1 and 1 hide (a gradient inside display:none
  // paints nothing in some browsers). Level 3 repaints them violet-pink-orange
  // (paintFire). The same SVG holds the eyes' clip path for level 3.
  var FIRE_GRADIENTS = [
    ["ai-fire-back", "#8a0c00", "#e01e00"],
    ["ai-fire-mid", "#e83000", "#ff7a00"],
    ["ai-fire-front", "#ff6a00", "#ffc400"],
    ["ai-fire-core", "#ffd040", "#fff7d6"]
  ];
  var SLOP_GRADIENTS = {
    "ai-fire-back": ["#3b0a7a", "#7c3aed"],
    "ai-fire-mid": ["#7c3aed", "#db2777"],
    "ai-fire-front": ["#db2777", "#f97316"],
    "ai-fire-core": ["#f9a8d4", "#fdf4ff"]
  };
  var ALMOND = "M2 20 Q30 -6 58 20 Q30 46 2 20Z";
  function ensureDefs() {
    if (document.getElementById("ai-defs")) return;
    var defs = make("div");
    defs.id = "ai-defs";
    defs.setAttribute("aria-hidden", "true");
    defs.innerHTML = '<svg width="0" height="0" focusable="false"><defs>' + // static markup, no user data
      FIRE_GRADIENTS.map(function (g) {
        return '<linearGradient id="' + g[0] + '" x1="0" y1="1" x2="0" y2="0">' +
          '<stop offset="0" stop-color="' + g[1] + '"></stop>' +
          '<stop offset="1" stop-color="' + g[2] + '"></stop></linearGradient>';
      }).join("") +
      '<clipPath id="ai-almond"><path d="' + ALMOND + '"></path></clipPath>' +
      "</defs></svg>";
    document.body.appendChild(defs);
    paintFire();
  }
  function paintFire() {
    var slop = isSlop();
    FIRE_GRADIENTS.forEach(function (g) {
      var grad = document.getElementById(g[0]);
      var stops = grad ? grad.querySelectorAll("stop") : [];
      if (stops.length !== 2) return;
      var c = slop ? SLOP_GRADIENTS[g[0]] : [g[1], g[2]];
      stops[0].setAttribute("stop-color", c[0]);
      stops[1].setAttribute("stop-color", c[1]);
    });
  }

  // The flames are drawn, not simulated: four rows of flame shapes (dark red
  // at the back, then orange, yellow and a white-hot core in front), each shape
  // licking on its own CSS loop (ai-lick-a/b/c in ai-mode.css) at its own pace,
  // over a bright bed, with embers floating up. Sizes and places come from a
  // fixed sequence, so the fire looks the same on every page load.
  var TONGUE_PATH = "M50 2C56 26 74 40 84 66C96 96 92 132 74 150C64 158 36 158 26 150" +
    "C8 132 4 98 18 70C24 58 32 50 34 36C40 48 44 52 48 52C44 38 44 18 50 2Z";
  // per row: shapes across a 1440px window, width and height (px), loop (s)
  var FIRE_ROWS = [
    { name: "back", count: 20, w: [110, 170], h: [128, 204], dur: 1.6 },
    { name: "mid", count: 26, w: [80, 120], h: [94, 153], dur: 1.2 },
    { name: "front", count: 30, w: [56, 86], h: [60, 110], dur: 0.9 },
    { name: "core", count: 24, w: [30, 50], h: [31, 60], dur: 0.7 }
  ];
  function seeded(i, s) { var v = Math.sin(i * 12.9898 + s * 78.233) * 43758.5453; return v - Math.floor(v); }
  // the window's width against the 1440px the rows are counted for
  function fireScale() { return Math.max(0.35, Math.min(1.5, (window.innerWidth || 1440) / 1440)); }
  function buildFlames(box, scale) {
    box.textContent = "";
    box.setAttribute("data-scale", scale.toFixed(2));
    FIRE_ROWS.forEach(function (row, r) {
      var layer = make("div", "ai-fl-row ai-fl-" + row.name);
      var n = Math.max(4, Math.round(row.count * scale));
      for (var i = 0; i < n; i++) {
        var a = seeded(i, r * 3 + 1), b = seeded(i, r * 3 + 2), d = seeded(i, r * 3 + 3);
        var w = row.w[0] + a * (row.w[1] - row.w[0]);
        var h = row.h[0] + b * (row.h[1] - row.h[0]);
        var x = (i + 0.5) / n * 100 + (d - 0.5) * (60 / n);
        var shape = make("div", "ai-fl");
        shape.style.cssText = "left:calc(" + x.toFixed(2) + "% - " + Math.round(w / 2) + "px);width:" +
          Math.round(w) + "px;height:" + Math.round(h) + "px;animation-duration:" +
          (row.dur + a * 0.5).toFixed(2) + "s;animation-delay:-" + (d * 2).toFixed(2) + "s";
        shape.innerHTML = '<svg viewBox="0 0 100 160" preserveAspectRatio="none" focusable="false">' +
          '<path d="' + TONGUE_PATH + '" fill="url(#ai-fire-' + row.name + ')"></path></svg>';
        layer.appendChild(shape);
      }
      box.appendChild(layer);
    });
    box.appendChild(make("div", "ai-fl-bed"));
    var embers = Math.round(18 * scale) + 4;
    for (var j = 0; j < embers; j++) {
      var k = seeded(j, 9), p = seeded(j, 10), size = (3 + k * 5).toFixed(1);
      var ember = make("i", "ai-ember");
      ember.style.cssText = "left:" + (p * 100).toFixed(1) + "%;width:" + size + "px;height:" + size +
        "px;animation-duration:" + (3 + k * 3).toFixed(1) + "s;animation-delay:-" + (p * 6).toFixed(1) + "s";
      box.appendChild(ember);
    }
  }
  // A much wider or narrower window gets a row of flames to match.
  var flameResize = 0;
  function onFlameResize() {
    clearTimeout(flameResize);
    flameResize = setTimeout(function () {
      var box = document.getElementById("ai-flames");
      if (!box) return;
      var scale = fireScale();
      if (Math.abs(scale - parseFloat(box.getAttribute("data-scale") || "1")) >= 0.15) buildFlames(box, scale);
    }, 300);
  }

  function ensureFx() {
    ensureDefs();
    if (document.getElementById("ai-flames")) return;
    var flames = make("div");
    flames.id = "ai-flames";
    buildFlames(flames, fireScale());
    window.addEventListener("resize", onFlameResize);
    var scanlines = make("div");
    scanlines.id = "ai-scanlines";
    var rollbar = make("div");
    rollbar.id = "ai-rollbar";
    var msg = make("div");
    msg.id = "ai-flicker-msg";
    msg.appendChild(make("span", "ai-glitch"));
    [flames, scanlines, rollbar, msg].forEach(function (el) {
      el.setAttribute("aria-hidden", "true");
      document.body.appendChild(el);
    });
  }

  // Matrix rain, faint, on a fixed canvas behind the flames: about a third of
  // the columns fall at a time, each at its own pace, with a pale glyph at the
  // head and a green trail that fades. The canvas is transparent (old glyphs
  // fade out of it instead of under a painted background); ai-mode.css keeps it
  // faint and fades it out before it reaches the flames.
  var RAIN_SIZE = 15;
  var RAIN_SHARE = 0.34; // share of the columns falling at a time
  var RAIN_GLYPHS = "アイウエオカキクケコサシスセソタチツテト0123456789ABCDEF{}<>=/$#";
  var SLOP_GLYPHS = "✦✧◆◇AIGPTLLM∞{}01"; // level 3: tokens, in violet
  var rain = { raf: 0, canvas: null, ctx: null, cols: [], last: 0, step: 0 };
  function rainGlyph() {
    var g = isSlop() ? SLOP_GLYPHS : RAIN_GLYPHS;
    return g.charAt(Math.floor(Math.random() * g.length));
  }
  function startRain() {
    if (!fxOk()) return;
    if (rain.canvas) {
      rain.canvas.style.display = "";
      if (!rain.raf) rain.raf = requestAnimationFrame(rain.draw);
      return;
    }
    try {
      var c = document.createElement("canvas");
      c.id = "ai-rain";
      c.setAttribute("aria-hidden", "true");
      document.body.appendChild(c);
      var ctx = c.getContext("2d");
      function resize() {
        c.width = window.innerWidth; c.height = window.innerHeight;
        // a new size clears the canvas and its settings
        ctx.font = RAIN_SIZE + "px ui-monospace, Menlo, Consolas, monospace";
        ctx.textBaseline = "top";
        var n = Math.ceil(c.width / RAIN_SIZE), rows = c.height / RAIN_SIZE;
        rain.cols = [];
        for (var i = 0; i < n; i++) {
          rain.cols[i] = {
            live: Math.random() < RAIN_SHARE,
            // already falling somewhere on screen, or about to: no empty start
            y: Math.floor(Math.random() * rows * 1.3 - rows * 0.3),
            every: 1 + Math.floor(Math.random() * 3), // steps per row: its pace
            prev: rainGlyph()
          };
        }
      }
      resize();
      window.addEventListener("resize", resize);
      rain.canvas = c; rain.ctx = ctx;
      rain.draw = function (ts) {
        rain.raf = requestAnimationFrame(rain.draw);
        if (ts - rain.last < 70) return; // ~14 steps a second: slow, and easy on the CPU
        rain.last = ts;
        rain.step++;
        var w = c.width, h = c.height;
        ctx.globalCompositeOperation = "destination-out"; // fade what is there
        ctx.fillStyle = "rgba(0,0,0,.08)";
        ctx.fillRect(0, 0, w, h);
        ctx.globalCompositeOperation = "source-over";
        for (var i = 0; i < rain.cols.length; i++) {
          var col = rain.cols[i];
          if (rain.step % col.every) continue;
          var x = i * RAIN_SIZE, y = col.y * RAIN_SIZE;
          if (col.live) {
            var slop = isSlop();
            ctx.fillStyle = slop ? "#c084fc" : "#39ff14"; // the last head cools to the trail's colour
            ctx.fillText(col.prev, x, y - RAIN_SIZE);
            col.prev = rainGlyph();
            ctx.fillStyle = slop ? "#fdf4ff" : "#d8ffe0";
            ctx.fillText(col.prev, x, y);
          }
          col.y++;
          // past the bottom: start over from the top, falling or not this time
          if (y > h && Math.random() > 0.95) {
            col.y = -Math.floor(Math.random() * 30);
            col.live = Math.random() < RAIN_SHARE;
          }
        }
      };
      rain.raf = requestAnimationFrame(rain.draw);
    } catch (e) {}
  }
  function stopRain() {
    if (rain.raf) cancelAnimationFrame(rain.raf), (rain.raf = 0);
    if (rain.canvas) rain.canvas.style.display = "none";
  }

  // ---- boot sequence: plays when you enter the lane --------------------------
  // Its lines are "boot.lines" in i18n.strings.js.
  // "Once per browser session" needs a session cookie: every tab shares it and
  // it goes when the browser closes (sessionStorage is per tab, so a challenge
  // opened in a new tab would play the boot again).
  function bootedThisSession() {
    try { return document.cookie.split("; ").indexOf(BOOTED_COOKIE + "=1") !== -1; }
    catch (e) { return false; }
  }
  function markBooted() {
    try { document.cookie = BOOTED_COOKIE + "=1; path=/; SameSite=Lax"; } catch (e) {}
  }
  var bootTimer = 0;
  // Esc is caught in the capture phase and stopped there: otherwise Bootstrap
  // also sees it and closes a challenge opened from a link under the boot.
  function onBootKey(e) {
    if (e.key !== "Escape") return;
    e.preventDefault();
    e.stopPropagation();
    stopBoot();
  }
  function stopBoot() {
    clearTimeout(bootTimer);
    var box = document.getElementById("ai-boot");
    if (box) box.parentNode.removeChild(box);
    document.removeEventListener("keydown", onBootKey, true);
  }
  function playBoot() {
    markBooted();
    if (!fxOk()) return;
    stopBoot();
    var box = make("div");
    box.id = "ai-boot";
    box.setAttribute("aria-hidden", "true");
    var caret = make("span", "ai-caret");
    var tail = make("div");
    tail.appendChild(caret);
    box.appendChild(tail);
    box.appendChild(makeT("span", "ai-boot-skip", "boot.skip"));
    box.addEventListener("click", stopBoot);
    document.addEventListener("keydown", onBootKey, true);
    document.body.appendChild(box);
    var i = 0, lines = list(isSlop() ? "boot.lines.slop" : "boot.lines");
    (function next() {
      if (i < lines.length) {
        box.insertBefore(make("div", null, lines[i++]), tail);
        bootTimer = setTimeout(next, 300);
      } else {
        box.className = "ai-boot-out";
        bootTimer = setTimeout(stopBoot, 450);
      }
    })();
  }

  // ---- random flicker ------------------------------------------------------
  // Every 45-75 s for the first 10 minutes in the lane, then every 1.5-2.5 min,
  // then every 3-6 min, where about 1 in 12 comes back within 3-10 s as a
  // surprise double-hit. The lane clock and the next due time live in
  // localStorage, so CTFd's page reloads don't reset them; a clock older than
  // 12 hours (yesterday's event) starts over.
  // The warnings are "flicker.messages" in i18n.strings.js.
  var flickerTimer = 0;
  function laneSeconds() {
    var now = Date.now(), since = +stored(SINCE_KEY) || 0;
    if (!since || now - since > 12 * 3600 * 1000) { since = now; store(SINCE_KEY, since); }
    return (now - since) / 1000;
  }
  function flickerGap() {
    var t = laneSeconds();
    function r(lo, hi) { return lo + Math.random() * (hi - lo); }
    if (isSlop()) return r(8, 15); // level 3 never calms down
    if (t < 600) return r(45, 75);
    if (t < 1800) return r(90, 150);
    return Math.random() < 1 / 12 ? r(3, 10) : r(180, 360);
  }
  // Never while a pop-up is open: shaking <main> makes it the containing block
  // and stacking context of CTFd's modals inside it, which would then jump and
  // sit under the backdrop, so a Submit click would be lost. (A modal that
  // opens mid-flicker ends it: see boot().)
  function flicker() {
    if (!fxOk() || !shownOn() || document.getElementById("ai-boot")) return;
    if (document.querySelector(".modal.show")) return;
    var root = document.documentElement;
    var span = document.querySelector("#ai-flicker-msg span");
    if (span) {
      var msgs = list(isSlop() ? "flicker.slop" : "flicker.messages");
      var text = msgs[Math.floor(Math.random() * msgs.length)];
      span.textContent = text;
      span.setAttribute("data-text", text);
    }
    root.classList.remove("ai-flickering");
    void root.offsetWidth; // restart the animation
    root.classList.add("ai-flickering");
    setTimeout(function () { root.classList.remove("ai-flickering"); }, 850);
  }
  function stopFlicker() { clearTimeout(flickerTimer); flickerTimer = 0; }
  // fresh: you just entered the lane, so start a new gap instead of honouring
  // a due time left over from earlier.
  function scheduleFlicker(fresh) {
    stopFlicker();
    if (!fxOk() || !shownOn()) return;
    var now = Date.now(), next = +stored(NEXT_KEY) || 0;
    if (fresh || !next || next < now - 60000) {
      next = now + flickerGap() * 1000;
      store(NEXT_KEY, next);
    }
    flickerTimer = setTimeout(function () {
      if (!shownOn()) return;
      // A background tab leaves the flicker to the tab you're looking at.
      // Another tab may already have used this one and set a later time.
      var due = +stored(NEXT_KEY) || 0;
      if (!document.hidden && due <= Date.now() + 1000) {
        store(NEXT_KEY, Date.now() + flickerGap() * 1000);
        flicker();
      }
      scheduleFlicker(false);
    }, Math.max(document.hidden ? 5000 : 1000, next - now));
  }

  // ---- the AI Slop-o-meter -------------------------------------------------------
  // Bottom left, shown in AI-modus only (the CSS): the level's number and name, a
  // slider over the four levels and a button per level. The choice is kept in
  // localStorage, and other tabs follow.
  function levelNum(lv) { return lv < 0 ? "−" + (-lv) : String(lv); }
  function syncFxDock() {
    var dock = document.getElementById("ai-fx-dock");
    if (!dock) return;
    var lv = fxLevel(), i = FX_LEVELS.indexOf(lv);
    var range = dock.querySelector(".ai-fx-range");
    if (range) {
      if (String(range.value) !== String(i)) range.value = String(i);
      bindAttr(range, "aria-valuetext", "fx.level." + lv);
      range.style.setProperty("--ai-fx-fill", Math.round(i / (FX_LEVELS.length - 1) * 100) + "%");
    }
    dock.querySelector(".ai-fx-num").textContent = levelNum(lv);
    bind(dock.querySelector(".ai-fx-name"), "fx.level." + lv);
    var ticks = dock.querySelectorAll(".ai-fx-tick");
    for (var k = 0; k < ticks.length; k++) {
      ticks[k].setAttribute("aria-pressed", ticks[k].getAttribute("data-level") === String(lv) ? "true" : "false");
    }
  }
  function ensureFxDock() {
    if (PREVIEW || document.getElementById("ai-fx-dock")) return;
    var dock = make("div");
    dock.id = "ai-fx-dock";
    dock.setAttribute("role", "group");
    bindAttr(dock, "aria-label", "fx.label");
    bindAttr(dock, "title", "fx.title");
    var bar = makeT("div", "ai-fx-bar98", "fx.label"); // level -1's title bar
    bar.setAttribute("aria-hidden", "true");
    dock.appendChild(bar);
    var head = make("div", "ai-fx-head");
    var label = makeT("label", "ai-fx-label", "fx.label");
    label.htmlFor = "ai-fx-range";
    head.appendChild(label);
    var read = make("span", "ai-fx-read");
    read.setAttribute("aria-hidden", "true"); // the slider's value text says it
    read.appendChild(make("span", "ai-fx-num"));
    read.appendChild(document.createTextNode(" · "));
    read.appendChild(make("span", "ai-fx-name"));
    head.appendChild(read);
    dock.appendChild(head);
    var range = make("input", "ai-fx-range");
    range.type = "range";
    range.id = "ai-fx-range";
    range.min = "0";
    range.max = String(FX_LEVELS.length - 1);
    range.step = "1";
    range.addEventListener("input", function () { setFx(FX_LEVELS[+range.value]); });
    dock.appendChild(range);
    var ticks = make("div", "ai-fx-ticks");
    FX_LEVELS.forEach(function (lv) {
      var b = make("button", "ai-fx-tick" + (lv < 0 ? " ai-fx-neg" : ""));
      b.type = "button";
      b.setAttribute("data-level", String(lv));
      b.appendChild(make("b", null, levelNum(lv)));
      b.appendChild(makeT("span", null, "fx.level." + lv));
      b.addEventListener("click", function () { setFx(lv); });
      ticks.appendChild(b);
    });
    dock.appendChild(ticks);
    document.body.appendChild(dock);
    syncFxDock();
  }
  // follow: only follow what another tab stored, without storing it again.
  function setFx(level, follow) {
    level = normLevel(level);
    var before = fxLevel();
    if (!follow) store(FX_KEY, String(level));
    var root = document.documentElement;
    root.setAttribute("data-ai-fx", String(level));
    syncFxDock();
    paintFire();
    try { fxWindow(); } catch (e) {}
    if (level < 2) {
      stopRain(); stopFlicker(); stopBoot();
      root.classList.remove("ai-flickering");
    } else if (shownOn()) {
      ensureFx(); startRain(); scheduleFlicker(level !== before);
    }
    if (shownOn()) {
      ensureLevelExtras();
      if (!follow && level === -1 && before !== -1) retroWelcome();
    }
    if (level !== -1) closeRetroWelcome();
  }
  // What another tab (or this page, back from the back/forward cache) stored.
  function followFx() {
    if (!storageWorks()) return;
    var lv = normLevel(stored(FX_KEY));
    if (lv !== fxLevel()) setFx(lv, true);
  }

  // ---- what levels 3 and -1 add around the board ---------------------------------
  // Built the first time the level shows (in AI-modus) and then kept in the page:
  // ai-mode.css shows each part only at its level (html[data-ai-fx]), so a level
  // change is the attribute flip. Nothing here takes a click away from the board:
  // the layers never take pointer events, and the assistant's chat sits in the
  // corner under any pop-up. None of it hints at a solution.
  function ensureLevelExtras() {
    if (PREVIEW || !shownOn()) return;
    if (isSlop()) {
      try { ensureSlopLayers(); } catch (e) {}
      try { ensureSlopNav(); } catch (e) {}
    }
    if (isRetro()) {
      try { ensureRetroBits(); } catch (e) {}
    }
    try { ensureLevelTitle(); } catch (e) {}
  }

  var EYE_SVG = '<svg viewBox="0 0 60 40" focusable="false"><path class="ai-eye-w" d="' + ALMOND + '"></path>' +
    '<g clip-path="url(#ai-almond)"><g class="ai-iris"><circle class="ai-eye-i" cx="30" cy="20" r="11"></circle>' +
    '<circle class="ai-eye-p" cx="30" cy="20" r="5"></circle><circle class="ai-eye-h" cx="26.5" cy="16.5" r="2"></circle></g></g>' +
    '<path class="ai-eye-lid" d="M2 20 Q30 -6 58 20"></path></svg>';
  var SPARK_PATH = "M12 0C12.9 7.6 16.4 11.1 24 12C16.4 12.9 12.9 16.4 12 24C11.1 16.4 7.6 12.9 0 12C7.6 11.1 11.1 7.6 12 0Z";
  function seeded(i, s) { var v = Math.sin(i * 12.9898 + s * 78.233) * 43758.5453; return v - Math.floor(v); }

  // Level 3: blobs, a synthwave floor and eyes behind the page; sparkles and a
  // violet vignette over it; toasts under the navbar; the board's own assistant
  // (Marvin AI, nothing to do with marvin-llm) in the bottom-right corner.
  function ensureSlopLayers() {
    if (document.getElementById("ai-slop-bg")) return;
    ensureDefs();
    var bg = make("div");
    bg.id = "ai-slop-bg";
    bg.setAttribute("aria-hidden", "true");
    bg.innerHTML = '<i class="ai-blob ai-b1"></i><i class="ai-blob ai-b2"></i><i class="ai-blob ai-b3"></i><i class="ai-floor"></i>';
    [["2%", "28%", 80], ["3%", "66%", 96], ["91%", "46%", 70], ["70%", "7%", 220]].forEach(function (e, i) {
      var eye = make("span", "ai-eye" + (e[2] > 150 ? " ai-eye-big" : ""));
      eye.innerHTML = EYE_SVG; // static markup
      eye.style.cssText = "left:" + e[0] + ";top:" + e[1] + ";width:" + e[2] + "px;height:" + Math.round(e[2] * 2 / 3) +
        "px;animation-delay:-" + (seeded(i, 51) * 5).toFixed(2) + "s";
      bg.appendChild(eye);
    });
    document.body.appendChild(bg);

    var top = make("div");
    top.id = "ai-slop-top";
    top.setAttribute("aria-hidden", "true");
    top.appendChild(make("i", "ai-vig"));
    for (var i = 0; i < 10; i++) {
      var sp = make("i", "ai-spark ai-sp-" + (i % 4));
      var size = Math.round(8 + seeded(i, 33) * 14);
      sp.style.cssText = "left:" + (2 + seeded(i, 31) * 96).toFixed(1) + "%;top:" + (8 + seeded(i, 32) * 84).toFixed(1) +
        "%;width:" + size + "px;height:" + size + "px;animation-duration:" + (1.6 + seeded(i, 34) * 1.8).toFixed(2) +
        "s;animation-delay:-" + (seeded(i, 35) * 3).toFixed(2) + "s";
      sp.innerHTML = '<svg viewBox="0 0 24 24" focusable="false"><path d="' + SPARK_PATH + '"></path></svg>';
      top.appendChild(sp);
    }
    document.body.appendChild(top);

    var toasts = make("div");
    toasts.id = "ai-slop-toasts";
    toasts.setAttribute("aria-hidden", "true"); // noise, not news
    list("slop.toasts").forEach(function (text, k) {
      var toast = make("div", "ai-toast");
      toast.style.animationDelay = (0.8 + k * 3.5) + "s";
      var ic = make("span", "ai-toast-ic");
      ic.innerHTML = '<svg viewBox="0 0 24 24" focusable="false"><path d="' + SPARK_PATH + '"></path></svg>';
      toast.appendChild(ic);
      toast.appendChild(make("span", "ai-toast-t", text));
      toasts.appendChild(toast);
    });
    document.body.appendChild(toasts);

    buildSlopChat();
  }

  // The assistant answers locally from a fixed list: nothing is sent anywhere.
  function buildSlopChat() {
    if (document.getElementById("ai-slop-chat")) return;
    var chat = make("section");
    chat.id = "ai-slop-chat";
    bindAttr(chat, "aria-label", "slop.chat.title");
    var head = make("div", "ai-chat-head");
    var av = make("span", "ai-chat-av");
    av.setAttribute("aria-hidden", "true");
    av.innerHTML = "<i></i><i></i><i></i>";
    head.appendChild(av);
    var who = make("span", "ai-chat-who");
    who.appendChild(makeT("b", null, "slop.chat.title"));
    who.appendChild(makeT("small", null, "slop.chat.status"));
    head.appendChild(who);
    var x = make("button", "ai-chat-x", "×");
    x.type = "button";
    bindAttr(x, "aria-label", "slop.chat.close");
    head.appendChild(x);
    chat.appendChild(head);
    var body = make("div", "ai-chat-body");
    body.setAttribute("role", "log");
    list("slop.chat.msgs").forEach(function (text, k) {
      var m = make("p", "ai-msg", text);
      m.style.animationDelay = (1.4 + k * 2) + "s";
      body.appendChild(m);
    });
    var typing = make("p", "ai-msg ai-msg-typing");
    typing.style.animationDelay = "9.4s";
    typing.appendChild(makeT("span", "visually-hidden", "slop.typing"));
    typing.appendChild(make("i"));
    typing.appendChild(make("i"));
    typing.appendChild(make("i"));
    body.appendChild(typing);
    chat.appendChild(body);
    var form = make("form", "ai-chat-form");
    var lab = makeT("label", "visually-hidden", "slop.chat.label");
    lab.htmlFor = "ai-chat-q";
    var input = make("input");
    input.id = "ai-chat-q";
    input.type = "text";
    input.autocomplete = "off";
    bindAttr(input, "placeholder", "slop.chat.input");
    var send = makeT("button", "ai-chat-send", "slop.chat.send");
    send.type = "submit";
    form.appendChild(lab);
    form.appendChild(input);
    form.appendChild(send);
    chat.appendChild(form);
    var said = { closed: 0, replies: 0 };
    function say(text, mine) {
      var m = make("p", "ai-msg" + (mine ? " ai-msg-me" : ""), text);
      m.style.animationDelay = "0s";
      body.insertBefore(m, typing);
      body.scrollTop = body.scrollHeight;
    }
    x.addEventListener("click", function () {
      var lines = list("slop.chat.closed");
      say(lines[Math.min(said.closed++, lines.length - 1)]);
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var q = (input.value || "").trim();
      if (!q) return;
      say(q, true);
      input.value = "";
      var lines = list("slop.chat.replies");
      setTimeout(function () { say(lines[said.replies++ % lines.length]); }, 700);
    });
    document.body.appendChild(chat);
  }

  // Level 3's navbar: "✦ Ask AI" (it opens the assistant) and a buzzword ticker
  // at the top of the page.
  function ensureSlopNav() {
    if (!document.getElementById("ai-slop-ask")) {
      var lane = document.querySelector(".ai-lane-item");
      if (lane && lane.parentNode) {
        var li = make("li", "nav-item ai-slop-ask-item");
        var b = make("button");
        b.id = "ai-slop-ask";
        b.type = "button";
        b.appendChild(makeT("span", null, "slop.ask"));
        b.appendChild(make("span", "ai-slop-ask-n", "99+"));
        b.addEventListener("click", function () {
          var q = document.getElementById("ai-chat-q");
          if (q) q.focus();
        });
        li.appendChild(b);
        lane.parentNode.insertBefore(li, lane);
      }
    }
    var main = document.querySelector("main");
    if (main && !document.getElementById("ai-slop-ticker")) {
      var ticker = make("div");
      ticker.id = "ai-slop-ticker";
      ticker.setAttribute("aria-hidden", "true");
      var track = make("div", "ai-ticker-track");
      var words = list("slop.ticker");
      for (var r = 0; r < 4; r++) words.forEach(function (w) { track.appendChild(make("span", null, w)); });
      ticker.appendChild(track);
      main.insertBefore(ticker, main.firstChild);
    }
  }

  // Around the Challenges page's title: level 3's kicker, melting drips, a
  // typewriter line and a whisper; level -1's under-construction sign.
  function ensureLevelTitle() {
    var host = document.querySelector(".jumbotron .container.ai-banner-host");
    var h1 = host && host.querySelector("h1");
    if (!h1) return;
    if (isSlop()) {
      if (!host.querySelector(".ai-kicker-slop")) {
        var kicker = makeT("p", "ai-kicker ai-kicker-slop", "board.kicker.slop");
        host.insertBefore(kicker, h1);
      }
      if (!h1.querySelector(".ai-drips")) {
        var drips = make("span", "ai-drips");
        drips.setAttribute("aria-hidden", "true");
        for (var i = 0; i < 9; i++) {
          var d = make("i");
          d.style.cssText = "left:" + (4 + i * 11 + seeded(i, 61) * 6).toFixed(1) + "%;width:" + Math.round(6 + seeded(i, 62) * 7) +
            "px;height:" + Math.round(26 + seeded(i, 63) * 60) + "px;animation-duration:" + (4 + seeded(i, 64) * 3).toFixed(2) +
            "s;animation-delay:-" + (seeded(i, 65) * 5).toFixed(2) + "s";
          drips.appendChild(d);
        }
        h1.appendChild(drips);
      }
      if (!host.querySelector(".ai-slop-type")) {
        var type = make("p", "ai-slop-type");
        type.setAttribute("aria-hidden", "true");
        host.appendChild(type);
        host.appendChild(makeT("p", "ai-slop-whisper", "slop.whisper"));
        fillSlopType();
      }
      var hud = host.querySelector(".ai-hud");
      if (hud && !hud.querySelector(".ai-hud-slop")) hud.appendChild(makeT("span", "ai-hud-slop", "hud.slop"));
    }
    if (isRetro() && !host.querySelector(".ai-retro-construct")) {
      var sign = make("div", "ai-retro-construct");
      sign.setAttribute("aria-hidden", "true");
      sign.appendChild(makeT("span", null, "retro.construct"));
      host.appendChild(sign);
    }
  }
  // The typewriter types its line in steps of one character, so its width is
  // the line's length in ch (monospace); a language switch types the new line.
  function fillSlopType() {
    var el = document.querySelector(".ai-slop-type");
    if (!el) return;
    var text = t("slop.type");
    el.textContent = text;
    el.style.width = text.length + "ch";
    el.style.animationTimingFunction = "steps(" + text.length + ")";
  }

  // Level -1: a marquee under the navbar and a hit counter at the bottom.
  function ensureRetroBits() {
    var main = document.querySelector("main");
    if (!main) return;
    if (!document.getElementById("ai-retro-marq")) {
      var marq = make("div");
      marq.id = "ai-retro-marq";
      marq.setAttribute("aria-hidden", "true");
      marq.appendChild(makeT("span", null, "retro.marquee"));
      main.insertBefore(marq, main.firstChild);
    }
    if (!document.getElementById("ai-retro-foot")) {
      var foot = make("div");
      foot.id = "ai-retro-foot";
      var count = make("p");
      count.appendChild(makeT("span", null, "retro.counter"));
      count.appendChild(document.createTextNode(" "));
      var digits = make("span", "ai-retro-digits");
      "001337".split("").forEach(function (c) { digits.appendChild(make("i", null, c)); });
      count.appendChild(digits);
      foot.appendChild(count);
      foot.appendChild(makeT("p", null, "retro.best"));
      main.appendChild(foot);
    }
  }
  // Entering level -1 greets you the way a 2003 homepage did: a dialog box.
  function closeRetroWelcome() {
    var box = document.getElementById("ai-retro-alert");
    if (box) box.parentNode.removeChild(box);
  }
  function retroWelcome() {
    if (document.getElementById("ai-retro-alert") || document.querySelector(".modal.show")) return;
    var box = make("div");
    box.id = "ai-retro-alert";
    box.setAttribute("role", "alertdialog");
    box.setAttribute("aria-labelledby", "ai-retro-alert-t");
    box.setAttribute("aria-describedby", "ai-retro-alert-d");
    var bar = make("div", "ai-r98-bar");
    var title = makeT("span", "ai-r98-title", "retro.alert.title");
    title.id = "ai-retro-alert-t";
    bar.appendChild(title);
    var x = make("button", "ai-r98-x", "×");
    x.type = "button";
    bindAttr(x, "aria-label", "window.close");
    bar.appendChild(x);
    box.appendChild(bar);
    var body = make("div", "ai-r98-body");
    body.id = "ai-retro-alert-d";
    var ic = make("span", "ai-r98-ic", "i");
    ic.setAttribute("aria-hidden", "true");
    body.appendChild(ic);
    var text = make("div");
    text.appendChild(makeT("p", null, "retro.alert.1"));
    text.appendChild(makeT("p", null, "retro.alert.2"));
    body.appendChild(text);
    box.appendChild(body);
    var ok = makeT("button", "ai-r98-ok", "retro.ok");
    ok.type = "button";
    box.appendChild(ok);
    function close() {
      document.removeEventListener("keydown", onKey, true);
      closeRetroWelcome();
    }
    function onKey(e) {
      if (e.key === "Escape" || e.key === "Enter") { e.preventDefault(); e.stopPropagation(); close(); }
    }
    x.addEventListener("click", close);
    ok.addEventListener("click", close);
    document.addEventListener("keydown", onKey, true);
    document.body.appendChild(box);
    ok.focus();
  }

  // ---- the challenge window follows the level -------------------------------------
  // meow-ai and pwn-ai serve each level's look on a port of its own, in the same
  // container (compose.yml); CTFd's connection info has level 2's port. The web
  // AI challenges read the level from their link (#fx=<level>), which never
  // reaches their server. Level 3 also puts its slop around the description.
  var TERMINAL_PORTS = {
    "meow-ai": { "-1": 4447, "1": 4449, "3": 4448 },
    "pwn-ai": { "-1": 1247, "1": 1249, "3": 1248 }
  };
  function fxWindow() {
    var win = document.getElementById("challenge-window");
    var nameEl = win && win.querySelector(".challenge-name");
    if (!nameEl || !sib.byName) return;
    var name = lc(nameEl.textContent), row = sib.byName[name];
    if (!row || !isAICategory(row.category)) return;
    var lv = String(fxLevel());
    var box = win.querySelector(".challenge-connection-info");
    if (box) {
      var code = box.querySelector("code");
      if (code && TERMINAL_PORTS[name]) {
        if (!code.hasAttribute("data-ctf-conn")) code.setAttribute("data-ctf-conn", code.textContent);
        var base = code.getAttribute("data-ctf-conn"), port = TERMINAL_PORTS[name][lv];
        var text = port ? base.replace(/(\s)\d+(\s*)$/, "$1" + port + "$2") : base;
        if (code.textContent !== text) code.textContent = text;
      }
      var links = box.querySelectorAll("a[href]");
      for (var i = 0; i < links.length; i++) {
        var a = links[i];
        if (!a.hasAttribute("data-ctf-href")) a.setAttribute("data-ctf-href", a.getAttribute("href"));
        var href = a.getAttribute("data-ctf-href").replace(/#.*$/, "") + "#fx=" + lv;
        if (a.getAttribute("href") !== href) a.setAttribute("href", href);
      }
    }
    if (isSlop()) slopWindow(win, row);
  }
  function slopWindow(win, row) {
    var pane = win.querySelector("#challenge") || win.querySelector(".modal-body");
    if (!pane || pane.querySelector(".ai-slop-sum")) return;
    win.removeAttribute("data-ctf-generated"); // a new challenge in the window
    var sum = make("div", "ai-slop-sum");
    sum.appendChild(makeT("p", "ai-slop-sum-h", "slop.sum.title"));
    sum.appendChild(makeT("p", null, "slop.sum.text", { name: row.name }));
    var ul = make("ul");
    ["slop.sum.1", "slop.sum.2", "slop.sum.3"].forEach(function (k) { ul.appendChild(makeT("li", null, k)); });
    sum.appendChild(ul);
    sum.appendChild(makeT("p", "ai-slop-sum-fine", "slop.sum.fine"));
    var anchor = win.querySelector(".ai-modal-chips") || win.querySelector(".challenge-value");
    if (anchor) anchor.insertAdjacentElement("afterend", sum);
    else pane.insertBefore(sum, pane.firstChild);

    var actions = make("div", "ai-slop-actions");
    var eli5 = makeT("button", "ai-slop-btn", "slop.eli5");
    eli5.type = "button";
    eli5.setAttribute("aria-expanded", "false");
    var gen = makeT("button", "ai-slop-btn", "slop.gen");
    gen.type = "button";
    actions.appendChild(eli5);
    actions.appendChild(gen);
    var explain = makeT("p", "ai-slop-eli5", "slop.eli5.text");
    explain.hidden = true;
    var desc = win.querySelector(".challenge-desc");
    (desc || sum).insertAdjacentElement("afterend", actions);
    actions.insertAdjacentElement("afterend", explain);
    eli5.addEventListener("click", function () {
      explain.hidden = !explain.hidden;
      eli5.setAttribute("aria-expanded", explain.hidden ? "false" : "true");
    });
    // It "generates" a flag into the answer box (and CTFd's own state): a wrong
    // one, which the wrong-flag line then calls a hallucination.
    gen.addEventListener("click", function () {
      var input = win.querySelector("#challenge-input, .challenge-input");
      if (!input) return;
      input.value = t("slop.genflag");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      win.setAttribute("data-ctf-generated", "");
      input.focus();
    });

    // "Was this challenge helpful?" Either answer is a yes: the button lights up
    // and pops, sparkles fly off it, the question turns into a thanks and Marvin,
    // who is always typing, answers. Nothing is sent anywhere.
    var foot = make("div", "ai-slop-foot");
    var votes = make("span", "ai-slop-votes");
    var ask = makeT("span", "ai-slop-ask-line", "slop.helpful");
    ask.setAttribute("aria-live", "polite");
    votes.appendChild(ask);
    foot.appendChild(votes);
    var typing = make("span", "ai-slop-typing");
    typing.appendChild(makeT("span", null, "slop.typing"));
    typing.appendChild(make("i"));
    typing.appendChild(make("i"));
    typing.appendChild(make("i"));
    foot.appendChild(typing);
    var reply = make("span", "ai-slop-reply");
    reply.setAttribute("aria-live", "polite");
    reply.hidden = true;
    foot.appendChild(reply);
    var voted = 0, replyTimer = null;
    ["slop.yes", "slop.alsoyes"].forEach(function (k) {
      var b = makeT("button", "ai-slop-vote", k);
      b.type = "button";
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () {
        var n = ++voted;
        var all = votes.querySelectorAll(".ai-slop-vote");
        for (var i = 0; i < all.length; i++) all[i].setAttribute("aria-pressed", all[i] === b ? "true" : "false");
        bind(ask, "slop.thanks." + ((n - 1) % 4));
        replay(ask, "ai-slop-said");
        replay(b, "ai-slop-voted");
        voteBurst(b);
        // Marvin types for a moment, then answers.
        clearTimeout(replyTimer);
        reply.hidden = true;
        typing.hidden = false;
        replyTimer = setTimeout(function () {
          bind(reply, "slop.reply." + ((n - 1) % 4), { n: n });
          typing.hidden = true;
          reply.hidden = false;
          replay(reply, "ai-slop-said");
        }, 900);
      });
      votes.appendChild(b);
    });
    pane.appendChild(foot);
  }

  // Restart a one-shot CSS animation: the class off, a reflow, the class on.
  function replay(el, cls) {
    el.classList.remove(cls);
    void el.offsetWidth;
    el.classList.add(cls);
  }

  // A vote's sparkles: a ring of ✦ flying off the button, in the slop's colours,
  // in a layer of their own over the challenge window that never takes a click.
  function voteBurst(from) {
    if (!MOTION_OK || !from.animate) return;
    var r = from.getBoundingClientRect();
    var layer = make("div", "ai-vote-burst");
    layer.setAttribute("aria-hidden", "true");
    layer.style.left = (r.left + r.width / 2) + "px";
    layer.style.top = (r.top + r.height / 2) + "px";
    var n = 16;
    for (var i = 0; i < n; i++) {
      var p = make("i", "ai-sp-" + (i % 4));
      p.innerHTML = '<svg viewBox="0 0 24 24" focusable="false"><path d="' + SPARK_PATH + '"></path></svg>';
      var size = rand(10, 20), ang = (i / n) * Math.PI * 2 + rand(-0.2, 0.2), dist = rand(42, 90);
      var dx = Math.cos(ang) * dist, dy = Math.sin(ang) * dist - 10;
      p.style.width = size + "px";
      p.style.height = size + "px";
      layer.appendChild(p);
      p.animate([
        { transform: "translate(-50%, -50%) scale(.2) rotate(0deg)", opacity: 1 },
        { transform: "translate(calc(-50% + " + dx + "px), calc(-50% + " + dy + "px)) scale(1) rotate(120deg)", opacity: 1, offset: 0.55 },
        { transform: "translate(calc(-50% + " + (dx * 1.2) + "px), calc(-50% + " + (dy * 1.2 + 24) + "px)) scale(.3) rotate(200deg)", opacity: 0 }
      ], { duration: rand(700, 1000), easing: "cubic-bezier(.2,.7,.3,1)", fill: "forwards" });
    }
    document.body.appendChild(layer);
    setTimeout(function () { if (layer.parentNode) layer.parentNode.removeChild(layer); }, 1100);
  }

  // ---- lane banner on the Challenges page ------------------------------------
  // Classic: a quiet rule strip under the title. AI-modus: one line above the
  // title (the lane, its rule, its threat level) and, beside the title, how
  // much of the bracket you have rooted, as a count and a thin bar. Both lanes'
  // parts are in the page; the CSS shows the lane's. The words go in by key
  // (data-i18n, fillIn).
  var BANNER_HTML =
    '<div class="ai-rule ai-rule-classic" role="note">' +
      '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"></circle><path d="M5.6 5.6l12.8 12.8"></path></svg>' +
      '<span><strong data-i18n="banner.classic.rule"></strong><span data-i18n="banner.classic.text"></span></span>' +
    '</div>' +
    '<div class="ai-hud" hidden>' +
      '<span class="ai-hud-count"></span>' +
      '<span class="ai-hud-bar" aria-hidden="true"><i></i></span>' +
    '</div>';
  // A preview has no banner: its countdown (preview.js) sits under the title.
  function ensureBanner() {
    if (PREVIEW || !onChallengesPage() || document.getElementById("ai-lane-banner")) return;
    var host = document.querySelector(".jumbotron .container");
    if (!host) return;
    var kicker = makeT("p", "ai-kicker", "board.kicker");
    kicker.id = "ai-lane-kicker";
    host.insertBefore(kicker, host.querySelector("h1") || host.firstChild);
    var banner = make("div", "ai-banner");
    banner.id = "ai-lane-banner";
    banner.innerHTML = BANNER_HTML; // static markup, no user data
    fillIn(banner);
    host.appendChild(banner);
    host.classList.add("ai-banner-host");
  }

  // "5 / 14 rooted": the AI bracket's tiles on the board, and how many of them
  // you have solved. Read off the board itself, so it follows a solve as soon
  // as CTFd redraws the tile.
  function updateHud() {
    var hud = document.querySelector("#ai-lane-banner .ai-hud");
    if (!hud) return;
    var tiles = document.querySelectorAll('[data-ai-bracket="ai"] .challenge-button');
    var total = tiles.length, solved = 0;
    for (var i = 0; i < total; i++) if (tiles[i].classList.contains("challenge-solved")) solved++;
    if (hud.hidden !== !total) hud.hidden = !total;
    if (!total) return;
    bind(hud.querySelector(".ai-hud-count"), "board.rooted", { n: solved, total: total });
    var fill = hud.querySelector(".ai-hud-bar i"), pct = Math.round(solved / total * 100) + "%";
    if (fill.style.width !== pct) fill.style.width = pct;
  }

  // The page title burns and glitches in AI-modus; the CSS needs its text.
  function glitchTitle() {
    var h1 = document.querySelector(".jumbotron h1");
    if (!h1 || h1.classList.contains("ai-glitch")) return;
    h1.setAttribute("data-text", (h1.textContent || "").trim());
    h1.classList.add("ai-glitch");
  }

  // Threat rating: 1-5 flames, as many as the rating (the CSS greys them out
  // once the tile is solved). Prefer the challenge's explicit metadata
  // `difficulty` (served by the ai_brackets plugin); fall back to its points
  // (300 -> 3, 500 -> 5) when no difficulty is set. Each flame fills from the
  // fire's gradients (#ai-defs), with a pale core.
  var FLAME_PATH = "M12 2c1.2 3.4 5 5.6 5 10.4A5 5 0 0 1 7 12.6c0-2.2 1-3.6 2.3-4.8 0 2.2 1 3.4 2.2 3.4 0-3.2-1.3-5.8.5-9.2z";
  function heatOf(value) { return Math.max(1, Math.min(5, Math.floor(value / 100))); }
  function clampHeat(n) { n = parseInt(n, 10); return n >= 1 ? Math.min(5, n) : 0; }
  function threatOf(row, value) {
    return clampHeat(row && row.difficulty) || heatOf(value > 0 ? value : (row ? row.value : 0));
  }
  function heatMarkup(heat) {
    var out = "";
    for (var i = 1; i <= heat; i++) {
      out += '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
        '<path d="' + FLAME_PATH + '" fill="url(#ai-fire-mid)"></path>' +
        '<path d="' + FLAME_PATH + '" fill="url(#ai-fire-core)" transform="translate(5.6 7.6) scale(.54)"></path></svg>';
    }
    return out;
  }
  // CTFd's tile: <p> with the name, then a <span> with the points.
  function tileValue(btn) {
    return btn.querySelector(".challenge-inner > p + span") || btn.querySelector(".challenge-inner span");
  }
  function decorateTiles() {
    // Rate tiles only once the challenge/difficulty fetch has settled, so the
    // first flames already reflect metadata `difficulty` instead of a
    // points-derived guess we'd redraw a moment later. sib.byName is null only
    // until then and becomes {} even if the fetch fails, so this never blocks.
    if (!sib.byName) { loadChallenges(); return; }
    var tiles = document.querySelectorAll('[data-ai-bracket="ai"] .challenge-button');
    if (tiles.length) ensureDefs();
    for (var i = 0; i < tiles.length; i++) {
      var btn = tiles[i];
      // Level 3: a badge on every tile, and each floats on its own beat.
      if (isSlop() && !btn.querySelector(".ai-slop-badge")) {
        var badge = makeT("span", "ai-slop-badge", "slop.badge." + (i % 7));
        badge.setAttribute("aria-hidden", "true");
        (btn.querySelector(".challenge-inner") || btn).appendChild(badge);
        btn.style.animationDelay = "-" + (seeded(i, 41) * 3).toFixed(2) + "s";
      }
      var valueEl = tileValue(btn);
      var value = parseInt(valueEl ? valueEl.textContent : "", 10);
      var row = sib.byName[lc(tileName(btn))];
      var heat = threatOf(row, value);
      if (!(heat > 0)) continue; // unparseable points and no difficulty -> skip; a later mutation retries
      var box = btn.querySelector(".ai-heat");
      if (box && parseInt(box.getAttribute("data-heat"), 10) === heat) continue; // already correct
      if (!box) {
        box = make("span", "ai-heat");
        box.setAttribute("role", "img");
        (btn.querySelector(".challenge-inner") || btn).appendChild(box);
      }
      box.setAttribute("data-heat", heat); // so a later difficulty load can upgrade it
      bindAttr(box, "aria-label", "tile.threat", { n: heat });
      box.innerHTML = heatMarkup(heat);
    }
  }

  // ---- the final boss ----------------------------------------------------------
  // The ai-llm category (attack the AI: marvin-llm) heads the AI board, its
  // name hidden, each of its challenges one wide row: "FINAL BOSS", the name,
  // the points and the boss's sanity, which drops with every team that breaks
  // it (100% minus solves per team). tagByCategoryHeaders marks the block
  // (data-ai-boss) and the board around it (data-ai-board); ai-mode.css moves
  // it to the top. The number of teams (users in users mode) is the total in
  // CTFd's own list; when that or the solve count isn't there, no sanity bar.
  var BOSS_CATEGORY = "ai-llm";
  var accounts = { promise: null, total: null };
  function loadAccounts() {
    if (accounts.promise) return accounts.promise;
    var cfg = (window.CTFd && window.CTFd.config) || window.init || {};
    accounts.promise = getJson(cfg.userMode === "users" ? "/api/v1/users" : "/api/v1/teams")
      .then(function (d) {
        var total = d && d.meta && d.meta.pagination ? parseInt(d.meta.pagination.total, 10) : 0;
        accounts.total = total > 0 ? total : 0;
        tagBoard();
      });
    return accounts.promise;
  }
  function markBoss(block, boss) {
    if (boss === block.hasAttribute("data-ai-boss")) return;
    if (!boss) { block.removeAttribute("data-ai-boss"); return; }
    block.setAttribute("data-ai-boss", "");
    if (block.parentElement) block.parentElement.setAttribute("data-ai-board", "");
  }
  function decorateBoss() {
    var tiles = document.querySelectorAll("[data-ai-boss] .challenge-button");
    if (!tiles.length) return;
    if (!sib.byName) { loadChallenges(); return; }
    if (accounts.total === null) loadAccounts();
    for (var i = 0; i < tiles.length; i++) {
      var btn = tiles[i], inner = btn.querySelector(".challenge-inner") || btn;
      if (!inner.querySelector(".ai-boss-kicker")) {
        inner.insertBefore(makeT("span", "ai-boss-kicker", "boss.kicker"), inner.firstChild);
      }
      var row = sib.byName[lc(tileName(btn))];
      var solves = row && row.solves != null ? parseInt(row.solves, 10) : NaN;
      var sanity = accounts.total > 0 && solves >= 0 ?
        Math.max(0, Math.min(100, Math.round(100 - solves / accounts.total * 100))) : null;
      var meter = inner.querySelector(".ai-boss-sanity");
      if (sanity === null) {
        if (meter && !meter.hidden) meter.hidden = true;
        continue;
      }
      if (!meter) {
        meter = make("span", "ai-boss-sanity");
        meter.appendChild(make("span", "ai-boss-sanity-text"));
        var bar = make("span", "ai-boss-sanity-bar");
        bar.setAttribute("aria-hidden", "true");
        bar.appendChild(make("i"));
        meter.appendChild(bar);
        inner.appendChild(meter);
      }
      if (meter.hidden) meter.hidden = false;
      bind(meter.querySelector(".ai-boss-sanity-text"), "boss.sanity", { n: sanity });
      var fill = meter.querySelector("i"), pct = sanity + "%";
      if (fill.style.width !== pct) fill.style.width = pct;
    }
  }

  // ---- challenge list + siblings ---------------------------------------------
  // One fetch of /api/v1/challenges serves both the board fallback (tile name ->
  // category) and the sibling links. Each AI challenge's `builds_on`
  // (metadata.yml) names the normal ones it levels up; the sync keeps that map
  // out of sight of players, and the ai_brackets plugin serves it at
  // /ai-brackets/siblings as {"<AI id>": [<normal id>, ...]}, visible pairs
  // only. The board stays as it is; the links are in the pop-up: an AI
  // challenge's "← builds on mono" chip opens mono in Classic, and once you
  // have solved a normal challenge, one quiet line under its description opens
  // its AI sibling ("Next level in AI-modus: mono-ai"). Without the plugin there
  // are no links.
  var sib = { promise: null, byName: null, next: null };

  function lc(s) { return String(s || "").trim().toLowerCase(); }
  function getJson(path) {
    return fetch(urlRoot() + path, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  function loadChallenges() {
    if (sib.promise) return sib.promise;
    sib.promise = Promise.all([getJson("/api/v1/challenges"), getJson("/ai-brackets/siblings")])
      .then(function (res) {
        var list = res[0] && res[0].data ? res[0].data : [];
        var links = res[1] && res[1].data ? res[1].data : null;
        var diff = (res[1] && res[1].difficulty) || {};
        var byName = {}, byId = {}, next = {};
        list.forEach(function (c) { c.buildsOn = []; c.difficulty = diff[c.id]; byName[lc(c.name)] = c; byId[c.id] = c; });
        Object.keys(links || {}).forEach(function (aiId) {
          var ai = byId[aiId];
          if (!ai || !isAICategory(ai.category)) return;
          (links[aiId] || []).forEach(function (baseId) {
            var base = byId[baseId];
            if (!base || isAICategory(base.category)) return; // not listed for you, or not a normal one
            ai.buildsOn.push(base);
            (next[lc(base.name)] = next[lc(base.name)] || []).push(ai);
          });
        });
        sib.byName = byName;
        sib.next = next;
        tagBoard();
        return sib;
      })
      .catch(function () { sib.byName = sib.byName || {}; sib.next = sib.next || {}; return sib; });
    return sib.promise;
  }

  function tileName(btn) {
    var p = btn.querySelector(".challenge-inner p");
    return p ? p.textContent : "";
  }
  function findTile(name) {
    var tiles = document.querySelectorAll(".challenge-button");
    for (var i = 0; i < tiles.length; i++) if (lc(tileName(tiles[i])) === name) return tiles[i];
    return null;
  }

  // Switch lane and open a challenge there: close this pop-up first (CTFd
  // reopens the window for the next challenge), then ask the board to load it.
  function openInLane(on, id) {
    var win = document.getElementById("challenge-window");
    var done = false;
    function go() {
      if (done) return;
      done = true;
      switchLane(on, true); // no boot sequence over the challenge you asked for
      window.dispatchEvent(new CustomEvent("load-challenge", { detail: id }));
    }
    if (win && win.classList.contains("show")) {
      win.addEventListener("hidden.bs.modal", go, { once: true });
      var close = win.querySelector("[data-bs-dismiss='modal']");
      if (close) close.click();
      setTimeout(go, 700); // a theme without Bootstrap's events: go anyway
    } else {
      go();
    }
  }

  // A challenge in the other lane, as a link: its name, never translated.
  function laneLink(c, on) {
    var b = make("button", "ai-link", c.name);
    b.type = "button";
    b.setAttribute("data-ctf-no-i18n", "");
    bindAttr(b, "title", on ? "sibling.next.title" : "sibling.back.title", { name: c.name });
    b.addEventListener("click", function () { openInLane(on, c.id); });
    return b;
  }

  // "<label> name, name": the label bound to its key, then a link per challenge.
  function linkLine(el, key, rows, on) {
    el.appendChild(makeT("span", null, key));
    rows.forEach(function (c, i) {
      el.appendChild(document.createTextNode(i ? ", " : " "));
      el.appendChild(laneLink(c, on));
    });
    return el;
  }

  // The board's tile says first (it follows a solve at once); the list fetched
  // with the page when the tile isn't there.
  function solvedByMe(name, row) {
    var tile = findTile(name);
    return tile ? tile.classList.contains("challenge-solved") : !!row.solved_by_me;
  }

  function decorateModal() {
    var win = document.getElementById("challenge-window");
    var nameEl = win && win.querySelector(".challenge-name");
    if (!nameEl) return;
    if (!sib.byName) { loadChallenges(); return; }
    var name = lc(nameEl.textContent), row = sib.byName[name];
    if (!row) return;
    if (isAICategory(row.category)) {
      if (!win.querySelector(".ai-modal-chips")) {
        var chips = make("div", "ai-modal-chips");
        if (row.buildsOn.length) chips.appendChild(linkLine(make("span", "ai-chip ai-chip-back"), "sibling.back", row.buildsOn, false));
        chips.appendChild(makeT("span", "ai-chip ai-chip-rule", "chip.ai"));
        var threat = threatOf(row, row.value);
        if (threat > 0) chips.appendChild(makeT("span", "ai-chip ai-chip-threat", "chip.threat", { n: threat }));
        (win.querySelector(".challenge-value") || nameEl).insertAdjacentElement("afterend", chips);
      }
      // A solved one says so among its chips (it appears right after a correct
      // flag, when the board redraws the tile).
      var chipRow = win.querySelector(".ai-modal-chips");
      if (chipRow && !chipRow.querySelector(".ai-chip-solved") && solvedByMe(name, row)) {
        chipRow.appendChild(makeT("span", "ai-chip ai-chip-solved", "chip.solved"));
      }
      fxWindow(); // the nc port and the link follow the AI Slop-o-meter
      return;
    }
    var next = sib.next[name];
    if (!next || win.querySelector(".ai-next")) return;
    if (!solvedByMe(name, row)) return; // shown right after a correct flag, when the board refreshes
    var anchor = win.querySelector(".challenge-desc") || win.querySelector(".challenge-value") || nameEl;
    anchor.insertAdjacentElement("afterend", linkLine(make("p", "ai-next"), "sibling.next", next, true));
  }

  // ---- challenge-board filtering -------------------------------------------
  // The board is filtered by CSS, not by hiding elements here: each category
  // block (or, on themes without category headers, each tile) is tagged
  // data-ai-bracket="ai"|"normal", and ai-mode.css hides whichever bracket does
  // not match html[data-ai-mode]. Toggling is then a single attribute flip, and
  // the tags are refreshed synchronously on every board mutation (before the
  // browser paints), so a late render or an Alpine re-render never shows the
  // wrong bracket.
  var TILES = ".challenge-button, [class*='challenge-button'], .challenge";

  function tag(el, ai) {
    var v = ai ? "ai" : "normal";
    if (el.getAttribute("data-ai-bracket") !== v) el.setAttribute("data-ai-bracket", v);
  }

  function tagByCategoryHeaders() {
    var headers = document.querySelectorAll(".category-header");
    if (!headers.length) return false;
    headers.forEach(function (h) {
      var name = (h.textContent || "").replace(/^🔥\s*/, "").trim();
      if (!name) return; // text not rendered yet; the next mutation tags it
      var block = h.closest(".pt-5") || h.parentElement;
      if (!block) return;
      tag(block, isAICategory(name));
      markBoss(block, lc(name) === BOSS_CATEGORY);
    });
    return true;
  }

  function tagByTiles() {
    // Fallback for themes without .category-header: tag individual tiles by name.
    var tiles = document.querySelectorAll(TILES);
    if (!tiles.length) return;
    if (!sib.byName) { loadChallenges(); return; } // calls tagBoard when it has the list
    // Match longest name first so a specific AI name ("julius-ai") wins over
    // the base name it contains ("julius"); a plain substring scan in
    // arbitrary key order would otherwise mis-bucket the AI sibling.
    var names = Object.keys(sib.byName).sort(function (a, b) { return b.length - a.length; });
    tiles.forEach(function (t) {
      var text = (t.textContent || "").trim().toLowerCase();
      var cat = null;
      for (var i = 0; i < names.length; i++) {
        if (names[i] && text.indexOf(names[i]) !== -1) { cat = sib.byName[names[i]].category; break; }
      }
      if (cat != null) tag(t.closest(".col-sm-6, .col, [class*='col-']") || t, isAICategory(cat));
    });
  }

  function onChallengesPage() {
    return /\/challenges\/?$/.test(location.pathname);
  }

  function tagBoard() {
    if (!onChallengesPage()) return;
    try {
      if (!tagByCategoryHeaders()) tagByTiles();
      decorateTiles();
      decorateModal();
    } catch (e) {}
    // Each on its own, so a failure in one still leaves the others done.
    try { decorateBoss(); } catch (e) {}
    try { updateHud(); } catch (e) {}
    try { relabelNext(); } catch (e) {}
    try { ensureLevelExtras(); } catch (e) {}
  }

  // ---- Close instead of "Next Challenge" -------------------------------------
  // After a correct flag CTFd offers "Next Challenge", and only when the
  // challenge has a next one set. Every challenge window gets a Close button
  // there instead (ai-mode.css shows it either way), which closes the window.
  var NEXT_BUTTON = "#challenge-window .notification-row .alert button.btn-info";
  function relabelNext() {
    var buttons = document.querySelectorAll(NEXT_BUTTON);
    for (var i = 0; i < buttons.length; i++) {
      if (buttons[i].hasAttribute("data-ctf-close")) continue;
      buttons[i].setAttribute("data-ctf-close", "");
      bind(buttons[i], "window.close");
    }
  }
  // Caught first and stopped, so CTFd's own handler doesn't open a next challenge
  // (matched by place, not by our label, so it also holds if relabelNext missed it).
  function onCloseClick(e) {
    var button = e.target && e.target.closest ? e.target.closest(NEXT_BUTTON) : null;
    if (!button) return;
    e.preventDefault();
    e.stopPropagation();
    var close = document.querySelector("#challenge-window [data-bs-dismiss='modal']");
    if (close) close.click();
  }

  // ---- the solution request after an answer -----------------------------------
  // After every answer CTFd 3.8 asks for the challenge's solution (it tests an
  // async check without awaiting it, so the answer is always yes). A visitor
  // without an account (a preview, a public board) is refused (403), and CTFd's
  // handler throws on the empty result before it refreshes the board. A failed
  // request now reads as "no solution", which is what a player gets anyway.
  function safeSolutionFetch() {
    var pages = window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge;
    if (!pages || typeof pages.getSolution !== "function" || pages.getSolution.ctfSafe) return;
    var inner = pages.getSolution;
    pages.getSolution = function () {
      return Promise.resolve(inner.apply(this, arguments)).then(
        function (data) { return data || { id: null }; },
        function () { return { id: null }; });
    };
    pages.getSolution.ctfSafe = true;
  }

  // ---- wrong-flag feedback ---------------------------------------------------
  // ai-mode.head.js reports each flag answer ("ctf-attempt"). On a wrong one the
  // alert gets data-ctf-fails, the number of wrong answers in a row, which
  // ai-mode.css (and preview.css) show in a "try again" line under it; from the
  // second in a row the alert also replays .ctf-refail, a shake in each lane's
  // style, so a repeat never looks like nothing happened.
  var ANSWER_ALERT = "#challenge-window .notification-row .alert";

  // CTFd draws the answer a moment after the response arrives: wait for an
  // alert-danger, at most ~1 s of frames.
  function whenFailDrawn(fn, frames) {
    var el = document.querySelector(ANSWER_ALERT);
    if (el && el.classList.contains("alert-danger")) return fn(el);
    if (frames > 0) requestAnimationFrame(function () { whenFailDrawn(fn, frames - 1); });
  }

  function onAttempt(e) {
    var d = e.detail || {};
    if (d.status === "correct" && !PREVIEW) {
      celebrate(d); // a preview has its own (preview.js)
      // fetch the list again for the new solve counts (the boss's sanity)
      setTimeout(function () { sib.promise = null; loadChallenges(); }, 1500);
    }
    if (d.status !== "incorrect") return;
    var fails = (d.before || 0) + 1;
    // Two frames first, so a repeat is marked after CTFd has redrawn the alert.
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        whenFailDrawn(function (el) {
          el.setAttribute("data-ctf-fails", String(fails));
          if (fails < 2) return;
          el.classList.remove("ctf-refail");
          void el.offsetWidth; // restart the animation
          el.classList.add("ctf-refail");
        }, 60);
      });
    });
  }

  // ---- a solve -----------------------------------------------------------------
  // A correct flag gets a moment of its own, in the lane's style, over the page
  // for about three seconds; it never takes a click. Classic: a calm card with a
  // check mark drawing itself and blue confetti falling. AI-modus: "FLAG PWNED"
  // in fire, the challenge window jolts and embers rise from the bottom. With
  // reduced motion only the card shows, still.
  var WIN_MS = 3200;
  var CONFETTI = ["#5ab0ff", "#9fd2ff", "#e6eef5", "#2f7fd1", "#c3d1de"];
  var EMBERS = ["#ff2e00", "#ff5a2a", "#ff7a00", "#ffc400", "#fff3b0"];

  function rand(a, b) { return a + Math.random() * (b - a); }

  // n particles from makeOne(i), each animated with frames(i) for a second or two.
  function burst(layer, n, makeOne, frames) {
    if (!MOTION_OK || !layer.animate) return;
    for (var i = 0; i < n; i++) {
      var p = makeOne(i);
      layer.appendChild(p);
      p.animate(frames(i), {
        duration: rand(1400, 2600), delay: rand(0, 350), easing: "cubic-bezier(.2,.6,.4,1)", fill: "both"
      });
    }
  }

  // c: the "ctf-attempt" detail, with the challenge's name and points.
  function celebrate(c) {
    try {
      var old = document.getElementById("ctf-win");
      if (old) old.parentNode.removeChild(old);
      var ai = shownOn();
      var layer = make("div", ai ? "ctf-win ctf-win-ai" : "ctf-win ctf-win-classic");
      layer.id = "ctf-win";
      layer.setAttribute("aria-hidden", "true"); // CTFd's "Correct" alert says it in words
      var card = make("div", "ctf-win-card");
      if (ai) {
        card.appendChild(make("div", "ctf-win-kicker", t("win.ai.kicker")));
        card.appendChild(make("div", "ctf-win-title", t("win.ai")));
      } else {
        card.innerHTML = '<svg class="ctf-win-check" viewBox="0 0 52 52" focusable="false">' +
          '<circle cx="26" cy="26" r="23"></circle><path d="M15 27l7 7 15-16"></path></svg>';
        card.appendChild(make("div", "ctf-win-title", t("win.classic")));
      }
      var line = (c.name || t("win.solved")) + (c.points != null ? t("win.points", { points: c.points }) : "");
      card.appendChild(make("div", "ctf-win-sub", line));
      if (ai) card.appendChild(make("div", "ctf-win-note", t("win.ai.note")));
      layer.appendChild(card);
      document.body.appendChild(layer);

      var w = window.innerWidth, h = window.innerHeight;
      if (ai) {
        burst(layer, 70, function (i) {
          var p = make("i", "ctf-win-ember");
          var size = rand(3, 8);
          p.style.cssText = "left:" + rand(0, w) + "px;width:" + size + "px;height:" + size + "px;" +
            "background:" + EMBERS[i % EMBERS.length] + ";box-shadow:0 0 " + (size * 2) + "px " + EMBERS[i % EMBERS.length];
          return p;
        }, function () {
          var drift = rand(-120, 120);
          return [
            { transform: "translate(0, 0) scale(1)", opacity: 0 },
            { opacity: 1, offset: 0.1 },
            { transform: "translate(" + drift + "px, " + (-rand(h * 0.5, h)) + "px) scale(.2)", opacity: 0 }
          ];
        });
        var modal = document.querySelector("#challenge-window .modal-content");
        if (modal && modal.animate && MOTION_OK) {
          modal.animate([
            { transform: "none" }, { transform: "translate(-10px, 4px) rotate(-.6deg)" },
            { transform: "translate(9px, -5px) rotate(.5deg)" }, { transform: "translate(-6px, 2px)" },
            { transform: "translate(3px, -1px)" }, { transform: "none" }
          ], { duration: 520, easing: "ease-out" });
        }
      } else {
        burst(layer, 90, function (i) {
          var p = make("i", "ctf-win-confetti");
          p.style.cssText = "left:" + rand(0, w) + "px;background:" + CONFETTI[i % CONFETTI.length] +
            ";width:" + rand(6, 10) + "px;height:" + rand(10, 16) + "px";
          return p;
        }, function () {
          var spin = rand(-540, 540), sway = rand(-80, 80);
          return [
            { transform: "translate(0, -30px) rotate(0deg)", opacity: 1 },
            { opacity: 1, offset: 0.75 },
            { transform: "translate(" + sway + "px, " + (h + 40) + "px) rotate(" + spin + "deg)", opacity: 0 }
          ];
        });
      }
      setTimeout(function () { layer.classList.add("ctf-win-out"); }, WIN_MS - 400);
      setTimeout(function () { if (layer.parentNode) layer.parentNode.removeChild(layer); }, WIN_MS);
    } catch (e) {}
  }

  // ---- per-bracket scoreboard ------------------------------------------------
  // The ai_brackets plugin (platform/plugins/) scores each bracket separately.
  // The Scoreboard page gets three tabs, All | Classic | AI-MODUS: every team
  // once per lane it plays in ("Team (Klassisk)", "Team (AI-MODUS)", never the
  // two added together), or one bracket's ranking. It opens on the selected
  // lane's and follows the lane control when the lane switches.
  // ai-mode.head.js points the page's API calls at the picked board
  // (html[data-ctf-board]) and reports (window.ctfAiBoard, "ai-board" event)
  // what is on screen. Here the page is labelled with that and, when the pick
  // changes, CTFd's own Alpine components (table + graph) fetch again. The pick
  // is kept in the address (?board=all|normal|ai), so a reload, or a link for
  // the projector, shows the same board. Without the plugin there is only the
  // combined board, and a preview has one lane: no tabs then.
  var BOARD_TABS = [["all", "board.all"], ["normal", "lane.classic"], ["ai", "lane.ai"]];
  var boardLane = null; // the lane the scoreboard page last followed
  var boardPick = null; // the board it last asked for: "all", "normal" or "ai"

  function onScoreboardPage() {
    return /\/scoreboard\/?$/.test(location.pathname);
  }

  function boardState() {
    return window.ctfAiBoard || { plugin: false, bracket: null, source: null };
  }

  function alpineData(el) {
    if (!el) return null;
    try {
      if (window.Alpine && typeof window.Alpine.$data === "function") return window.Alpine.$data(el);
    } catch (e) {}
    return el._x_dataStack ? el._x_dataStack[0] : null;
  }

  function isBoard(name) {
    return name === "all" || name === "normal" || name === "ai";
  }

  // The tabs, above CTFd's table (where its own bracket tabs go), made once.
  function boardTabs() {
    var tabs = document.getElementById("ai-board-tabs");
    if (tabs || PREVIEW) return tabs;
    var table = document.getElementById("scoreboard");
    if (!table || !table.parentNode) return null;
    tabs = make("div", "py-3");
    tabs.id = "ai-board-tabs";
    var nav = make("nav", "nav nav-pills nav-fill");
    bindAttr(nav, "aria-label", "board.tabs");
    BOARD_TABS.forEach(function (tab) {
      var button = makeT("button", "nav-link", tab[1]);
      button.type = "button";
      button.setAttribute("data-board", tab[0]);
      button.addEventListener("click", function () { pickBoard(tab[0]); });
      nav.appendChild(button);
    });
    tabs.appendChild(nav);
    table.parentNode.insertBefore(tabs, table);
    return tabs;
  }

  function markBoardTabs() {
    var tabs = boardTabs();
    if (!tabs) return;
    tabs.hidden = boardState().plugin === false; // only the combined board: nothing to pick
    var buttons = tabs.querySelectorAll("button[data-board]");
    for (var i = 0; i < buttons.length; i++) {
      var active = buttons[i].getAttribute("data-board") === boardPick;
      buttons[i].classList.toggle("active", active);
      buttons[i].setAttribute("aria-pressed", active ? "true" : "false");
    }
  }

  // Label what the page shows: a bracket, both side by side (All), or, when the
  // plugin isn't there or failed, that this is CTFd's combined scoreboard.
  function labelScoreboard(bracket, source) {
    markBoardTabs();
    var h1 = document.querySelector(".jumbotron h1");
    if (!h1) return;
    var label = document.getElementById("ai-board-label");
    if (!label) {
      label = document.createElement("p");
      label.id = "ai-board-label";
      h1.insertAdjacentElement("afterend", label);
    }
    var fallback = source === "stock" || boardState().plugin === false;
    bind(label, fallback ? "bracket.combined" : "bracket." + bracket);
    bindAttr(label, "title", fallback ? "bracket.combined.title" : bracket === "all" ? "bracket.all.title" : "bracket.title");
  }

  // Have CTFd's table and graph fetch again; false when they can't be reached.
  function refetchBoard() {
    var list = alpineData(document.getElementById("scoreboard"));
    var graph = alpineData(document.getElementById("score-graph"));
    if (!list || typeof list.update !== "function" || !graph || typeof graph.update !== "function") return false;
    list.update();
    graph.update();
    return true;
  }

  // Show the board `pick` ("all", "normal" or "ai"): a tab, or the lane switching.
  function pickBoard(pick) {
    var st = boardState();
    var stale = boardPick !== null && boardPick !== pick;
    boardPick = pick;
    document.documentElement.setAttribute("data-ctf-board", pick);
    // The head script may already have this board's answer (and its source).
    labelScoreboard(pick, st.bracket === pick ? st.source : null);
    // On page load (boardPick null) CTFd's own fetches already ask for this
    // board; without the plugin every pick is the same combined board.
    if (!stale || st.plugin === false) return;
    var url = null;
    try {
      url = new URL(location.href);
      url.searchParams.set("board", pick);
      history.replaceState(history.state, "", url);
    } catch (e) {}
    if (refetchBoard()) return;
    if (url) location.replace(url); // the head script reads ?board= on the way back in
    else location.reload();
  }

  function showScoreboard(on) {
    if (!onScoreboardPage()) return;
    var lane = on ? "ai" : "normal";
    if (boardLane === null) {
      // Page load: the board the address asks for (?board=, which the head
      // script has put in data-ctf-board), else the lane's.
      var asked = document.documentElement.getAttribute("data-ctf-board");
      boardLane = lane;
      pickBoard(!PREVIEW && isBoard(asked) ? asked : lane);
    } else if (boardLane !== lane) {
      boardLane = lane;
      pickBoard(lane);
    }
  }

  // Account pages show CTFd's combined score; add the score and place per
  // bracket under it. Team pages in teams mode, user pages in users mode (in
  // teams mode a user page shows the team's score, which the team page covers).
  function accountScoreTarget() {
    var cfg = (window.CTFd && window.CTFd.config) || window.init || {};
    var path = location.pathname;
    var m, who;
    if (cfg.userMode === "users") {
      m = path.match(/\/users\/(\d+)\/?$/);
      who = m ? m[1] : /\/user\/?$/.test(path) ? "me" : null;
      if (!who) return null;
      // The user page's "<n> points" heading has no id (CTFd's English, even
      // when the page shows another language).
      var hs = document.querySelectorAll("h2.text-center");
      for (var i = 0; i < hs.length; i++) {
        var small = hs[i].querySelector("small");
        if (small && /points/i.test(sourceText(small))) return { who: who, el: hs[i] };
      }
      return null;
    }
    var score = document.getElementById("team-score");
    if (!score) return null;
    m = path.match(/\/teams\/(\d+)\/?$/);
    who = m ? m[1] : /\/team\/?$/.test(path) ? "me" : null;
    return who ? { who: who, el: score } : null;
  }

  function showAccountBrackets(on) {
    var box = document.getElementById("ai-bracket-scores");
    if (!box) {
      var target = accountScoreTarget();
      if (!target) return;
      var cfg = (window.CTFd && window.CTFd.config) || window.init || {};
      box = document.createElement("div");
      box.id = "ai-bracket-scores";
      box.className = "text-center";
      box.hidden = true;
      target.el.insertAdjacentElement("afterend", box);
      fetch((cfg.urlRoot || "") + "/ai-brackets/account/" + target.who, {
        credentials: "same-origin",
        headers: { Accept: "application/json", "Content-Type": "application/json" }
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (!d || !d.data) return;
          ["normal", "ai"].forEach(function (b) {
            var s = d.data[b] || {};
            var line = document.createElement("div");
            line.className = "ai-bracket-score";
            line.setAttribute("data-bracket", b);
            line.appendChild(makeT("span", null, "bracket." + b));
            line.appendChild(makeT("span", null, "account.score", { score: s.score || 0 }));
            // place is CTFd's ordinal ("1st"); n the number alone
            if (s.place) line.appendChild(makeT("span", null, "account.place", { place: s.place, n: parseInt(s.place, 10) }));
            box.appendChild(line);
          });
          box.hidden = false;
        })
        .catch(function () {});
    }
    box.setAttribute("data-active", on ? "ai" : "normal");
  }

  // ---- apply mode ----------------------------------------------------------
  // fresh: you just entered the lane, so the flicker starts a new gap.
  function apply(on, fresh) {
    try {
      document.documentElement.setAttribute("data-ai-mode", on ? "on" : "off");
      syncLaneControl(on);
      ensureBanner();
      if (on) {
        ensureFx(); startRain(); glitchTitle(); scheduleFlicker(!!fresh);
        ensureLevelExtras();
      } else {
        stopRain(); stopFlicker(); stopBoot();
      }
      tagBoard();
      showScoreboard(on);
      showAccountBrackets(on);
    } catch (e) {}
  }

  function onMotionChange() {
    MOTION_OK = !(motionQuery && motionQuery.matches);
    if (!MOTION_OK) {
      stopRain(); stopFlicker(); stopBoot();
      document.documentElement.classList.remove("ai-flickering");
    }
    if (shownOn() && fxOk()) { startRain(); scheduleFlicker(false); }
  }

  // Entering the lane yourself plays the boot sequence (unless quiet: a link
  // in the pop-up opens a challenge straight away) and starts a fresh flicker
  // gap; other tabs and Back/Forward just follow along (apply).
  function switchLane(on, quiet) {
    setOn(on);
    if (on === shownOn()) return;
    apply(on, true);
    if (on && !quiet) playBoot();
  }

  // ---- the lane control in the navbar ----------------------------------------
  // Two labelled options, Classic | AI-MODUS, as a radio group: click, or the
  // arrow keys once it has focus.
  var LANES = [
    { on: false, lane: "classic", label: "lane.classic", title: "lane.classic.title" },
    { on: true, lane: "ai", label: "lane.ai", title: "lane.ai.title" }
  ];

  function laneButtons() {
    var group = document.getElementById("ai-lane");
    return group ? group.querySelectorAll("button") : [];
  }

  function syncLaneControl(on) {
    var buttons = laneButtons();
    for (var i = 0; i < buttons.length; i++) {
      var checked = (buttons[i].getAttribute("data-lane") === "ai") === on;
      buttons[i].setAttribute("aria-checked", checked ? "true" : "false");
      buttons[i].tabIndex = checked ? 0 : -1;
    }
  }

  function buildLaneControl() {
    if (PREVIEW || document.getElementById("ai-lane")) return true;
    var nav = document.querySelector("nav.navbar, .navbar, header");
    if (!nav) return false;

    var li = make("li", "nav-item ai-lane-item");
    var group = make("div", "ai-lane");
    group.id = "ai-lane";
    group.setAttribute("role", "radiogroup");
    bindAttr(group, "aria-label", "lane.group");
    LANES.forEach(function (l) {
      var b = makeT("button", null, l.label);
      b.type = "button";
      b.setAttribute("role", "radio");
      b.setAttribute("data-lane", l.lane);
      bindAttr(b, "title", l.title);
      b.addEventListener("click", function () { switchLane(l.on); });
      group.appendChild(b);
    });
    group.addEventListener("keydown", function (e) {
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].indexOf(e.key) === -1) return;
      e.preventDefault();
      switchLane(!shownOn());
      var buttons = laneButtons();
      for (var i = 0; i < buttons.length; i++) {
        if (buttons[i].getAttribute("aria-checked") === "true") buttons[i].focus();
      }
    });
    li.appendChild(group);

    // Prefer the right-hand nav list (the one with the theme switch); else the
    // first nav list; else the nav itself.
    var themeSwitch = nav.querySelector(".theme-switch");
    var targetLi = themeSwitch ? themeSwitch.closest("li") : null;
    if (targetLi && targetLi.parentNode) {
      targetLi.parentNode.insertBefore(li, targetLi);
    } else {
      var ul = nav.querySelector("ul.navbar-nav") || nav.querySelector("ul");
      if (ul) ul.appendChild(li); else nav.appendChild(li);
    }
    return true;
  }

  // ---- first-visit lane chooser ----------------------------------------------
  // Shown once on the Challenges page to a browser that hasn't picked a lane.
  // Esc or "Enter Classic" keeps the default.
  // The words go in by key (data-i18n, fillIn), so the language switch in the
  // navbar behind it rewrites them too.
  var CHOOSER_HTML =
    '<div class="ai-chooser-panel" role="dialog" aria-modal="true" aria-labelledby="ai-chooser-title">' +
      '<div class="ai-chooser-head"><h2 id="ai-chooser-title" data-i18n="chooser.title"></h2>' +
        '<p data-i18n="chooser.lead"></p></div>' +
      '<div class="ai-chooser-lanes">' +
        '<div class="ai-chooser-lane ai-chooser-classic">' +
          '<div class="ai-chooser-kicker" data-i18n="chooser.classic.kicker"></div>' +
          '<div class="ai-chooser-name" data-i18n="lane.classic"></div>' +
          '<div class="ai-chooser-rule" data-i18n="chooser.classic.rule"></div>' +
          '<ul><li data-i18n="chooser.classic.1"></li>' +
            '<li data-i18n="chooser.classic.2"></li>' +
            '<li data-i18n="chooser.classic.3"></li></ul>' +
          '<button type="button" data-pick="off" data-i18n="chooser.classic.go"></button>' +
        '</div>' +
        '<div class="ai-chooser-lane ai-chooser-ai">' +
          '<div class="ai-chooser-kicker" data-i18n="chooser.ai.kicker"></div>' +
          '<div class="ai-chooser-name" data-i18n="lane.ai"></div>' +
          '<div class="ai-chooser-rule" data-i18n="chooser.ai.rule"></div>' +
          '<ul><li data-i18n="chooser.ai.1"></li>' +
            '<li data-i18n="chooser.ai.2"></li>' +
            '<li data-i18n="chooser.ai.3"></li></ul>' +
          '<p class="ai-chooser-fx" data-i18n="chooser.ai.fx"></p>' +
          '<button type="button" data-pick="on" data-i18n="chooser.ai.go"></button>' +
        '</div>' +
      '</div>' +
      '<div class="ai-chooser-foot" data-i18n="chooser.foot"></div>' +
    '</div>';

  var chooser = null; // { overlay, onKey } while it is open

  // Remove the chooser without storing anything (another tab picked a lane).
  function dismissChooser() {
    if (!chooser) return;
    document.removeEventListener("keydown", chooser.onKey, true);
    if (chooser.overlay.parentNode) chooser.overlay.parentNode.removeChild(chooser.overlay);
    chooser = null;
  }

  // Offer the chooser once the pop-up in its way closes. A link to a challenge
  // that never opens (hidden or gone) holds it back for 4 s at most.
  var chooserWaits = false;
  function chooserAfterModal() {
    if (chooserWaits) return;
    chooserWaits = true;
    function again() {
      chooserWaits = false;
      document.removeEventListener("hidden.bs.modal", onHidden);
      maybeChooser(true);
    }
    function onHidden() { setTimeout(again, 0); }
    document.addEventListener("hidden.bs.modal", onHidden);
    setTimeout(function () {
      if (chooserWaits && !document.querySelector(".modal.show")) again();
    }, 4000);
  }

  // linkDone: the challenge link (if any) has had its turn.
  function maybeChooser(linkDone) {
    if (PREVIEW || !onChallengesPage() || stored(KEY) !== null || !storageWorks()) return;
    if (chooser) return;
    // A challenge opened from a link (#name-id) or any open pop-up comes first:
    // Bootstrap's focus trap would pull keyboard focus into it, behind the
    // chooser. Offer the chooser once it closes.
    if (document.querySelector(".modal.show") || (!linkDone && location.hash.length > 1)) {
      chooserAfterModal();
      return;
    }
    var overlay = make("div");
    overlay.id = "ai-chooser";
    overlay.innerHTML = CHOOSER_HTML; // static markup, no user data
    fillIn(overlay);
    var previous = document.activeElement;
    function close(on) {
      dismissChooser();
      if (on) {
        switchLane(true);
      } else {
        setOn(false);
        apply(false); // this tab may show AI-modus if another tab switched it
      }
      if (previous && previous.focus) try { previous.focus(); } catch (e) {}
    }
    function onKey(e) {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(false); return; }
      if (e.key !== "Tab") return;
      // keep focus inside the dialog
      var buttons = overlay.querySelectorAll("button");
      var first = buttons[0], last = buttons[buttons.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    overlay.addEventListener("click", function (e) {
      var pick = e.target.closest ? e.target.closest("[data-pick]") : null;
      if (pick) close(pick.getAttribute("data-pick") === "on");
    });
    chooser = { overlay: overlay, onKey: onKey };
    document.addEventListener("keydown", onKey, true);
    document.body.appendChild(overlay);
    var firstButton = overlay.querySelector("button");
    if (firstButton) firstButton.focus();
  }

  // ---- boot ----------------------------------------------------------------
  // Our own layers change on their own (the boot types its lines, the count
  // beside the title follows the board); board mutations inside them are not
  // the board's.
  var OWN = "#ai-lane-banner, #ai-boot, #ai-flicker-msg, #ai-flames, #ai-chooser, #ai-fx-dock, " +
    ".ai-boss-kicker, .ai-boss-sanity, #ai-slop-bg, #ai-slop-top, #ai-slop-toasts, #ai-slop-chat, " +
    "#ai-slop-ticker, #ai-retro-marq, #ai-retro-foot, #ai-retro-alert, .ai-slop-type, .ai-drips, .ai-slop-badge, " +
    ".ai-slop-foot, .ai-vote-burst, #ctf-fb, #ctf-fb-toasts, #ctf-fb-dock, #ctf-fb-live";
  function isOwn(node) {
    var el = node && (node.nodeType === 1 ? node : node.parentElement);
    return !!(el && el.closest && el.closest(OWN));
  }

  function boot() {
    var on = isOn();
    var firstInSession = !bootedThisSession();
    ensureFxDock();
    // retry building the lane control a few times in case the navbar renders late
    var tries = 0;
    (function tryBuild() {
      if (buildLaneControl() || tries++ > 20) {
        apply(on);
        // The first AI-modus page of a browser session gets the boot sequence.
        if (on && firstInSession) playBoot();
        maybeChooser();
        return;
      }
      setTimeout(tryBuild, 150);
    })();

    // The board (Alpine/JS) renders async and re-renders on solve: tag new
    // category blocks as they appear. Synchronous (no debounce) so they are
    // tagged before the next paint. A tile's class changes are watched too: a
    // solve flips it to .challenge-solved, which brings up the next-level line
    // in the pop-up. Other class changes (modals, tooltips,
    // Alpine :class anywhere) and our own data-ai-bracket writes are ignored.
    var obs = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (isOwn(m.target)) continue;
        if (m.type === "attributes" && !(m.target.classList && m.target.classList.contains("challenge-button"))) continue;
        tagBoard();
        return;
      }
    });
    try {
      obs.observe(document.body, {
        childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["class"]
      });
    } catch (e) {}

    // Keep the page in step with the stored mode: a page restored from the
    // back/forward cache still shows the mode it was left in, and other tabs
    // only learn about a switch through the storage event. The same goes for the
    // Effects button.
    // Once any tab stores a lane, a chooser still open here goes away.
    function followStored() {
      if (stored(KEY) !== null) dismissChooser();
      followFx();
      apply(isOn());
    }
    window.addEventListener("pageshow", function (e) { if (e.persisted) followStored(); });
    // ai-mode.head.js reports what the scoreboard's latest fetch returned.
    document.addEventListener("ai-board", function (e) {
      if (onScoreboardPage() && e.detail) labelScoreboard(e.detail.bracket, e.detail.source);
    });
    window.addEventListener("storage", function (e) {
      if (e.key === KEY) followStored();
      else if (e.key === FX_KEY) followFx();
    });
    document.addEventListener("click", onCloseClick, true);
    document.addEventListener("ctf-attempt", onAttempt);
    safeSolutionFetch();

    // A pop-up opening mid-flicker ends the flicker (see flicker()). One that
    // opens while the chooser is up (an admin's notification alert, say) takes
    // over: the chooser steps aside, so focus isn't trapped behind it, and
    // comes back once the pop-up closes.
    document.addEventListener("show.bs.modal", function () {
      document.documentElement.classList.remove("ai-flickering");
      if (chooser) { dismissChooser(); chooserAfterModal(); }
    });

    // The language switched (i18n.js has rewritten the bound text already): the
    // title's glitch copies follow, and so do the lanes after the names on the
    // All scoreboard (ai-mode.head.js writes them as the answer comes in).
    document.addEventListener("ctf-lang", function () {
      try {
        var h1 = document.querySelector(".jumbotron h1.ai-glitch");
        if (h1) h1.setAttribute("data-text", (h1.firstChild && h1.firstChild.nodeType === 3 ? h1.firstChild.nodeValue : h1.textContent || "").trim());
      } catch (e) {}
      try { fillSlopType(); } catch (e) {}
      try {
        if (onScoreboardPage() && boardPick === "all" && boardState().plugin === true) refetchBoard();
      } catch (e) {}
    });

    if (motionQuery) {
      if (motionQuery.addEventListener) motionQuery.addEventListener("change", onMotionChange);
      else if (motionQuery.addListener) motionQuery.addListener(onMotionChange);
    }

    // For the organisers: window.ctfAiModus.boot() / .flicker() replay the
    // effects on demand (for example on the projector during the intro talk).
    window.ctfAiModus = {
      boot: function () { if (shownOn()) playBoot(); },
      flicker: function () { ensureFx(); flicker(); },
      // the AI Slop-o-meter from the console: ctfAiModus.level(3)
      level: function (lv) { setFx(lv); },
      // first-blood.js: the standings changed, fetch the Scoreboard's table and graph again
      refreshBoard: function () { return onScoreboardPage() && refetchBoard(); }
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
