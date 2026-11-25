/* =========================================================================
   HOSTED-FX  -  the layers of the AI-modus effects level on the hosted AI
   challenge pages (noter-ai, robot-ai, api-ai, viking-ai). The levels and
   how a page gets one are at the top of hosted-fx.css: each page's inline
   bootstrap sets html[data-ai-fx] before paint and loads this file from CTFd.

     -1  WEB 1.0    a marquee over the page and a hit counter under it
      1  CALM       nothing (hosted-fx.css hides the scanlines)
      2  BURN       the board's matrix rain and drawn flames behind the page
                    (as ai-mode.js draws them: buildFlames, startRain) and a
                    slow rolling CRT bar over it
      3  AI HORROR  the same in slop colours, plus a buzzword ticker and an
                    "AI summary" above the page, drifting blobs and blinking
                    eyes behind it, sparkles and a vignette over it, and toasts
                    taking turns in the corner

   It only adds DOM layers: no requests, no cookies, no storage, nothing that
   changes what the page sends; the page's text is read once (the challenge's
   name, from its strip) and only ever written back as text. No layer takes
   clicks; the toasts and sparkles step aside from any form control they
   would cover, and the eyes from the page's content. Nothing is added until
   hosted-fx.css has applied, so a page whose stylesheet did not load looks
   as it always did. Everything runs in try/catch: a failure leaves the page
   as it is.
   ========================================================================= */
(function () {
  "use strict";

  var root = document.documentElement;
  var LEVEL = root.getAttribute("data-ai-fx");
  if (window.ctfHostedFx) return; // once per page
  window.ctfHostedFx = { level: LEVEL };
  if (LEVEL !== "-1" && LEVEL !== "2" && LEVEL !== "3") return; // 1 (CALM): nothing to add
  var SLOP = LEVEL === "3";

  // Reduced motion is followed live: turning it on mid-visit stops the rain
  // (hosted-fx.css stops everything else).
  var motion = null;
  try { motion = window.matchMedia("(prefers-reduced-motion: reduce)"); } catch (e) {}
  function motionOk() { return !(motion && motion.matches); }

  function make(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }
  function decor(el) { el.setAttribute("aria-hidden", "true"); return el; }
  // a fixed sequence, so a layer looks the same on every page load
  function seeded(i, s) { var v = Math.sin(i * 12.9898 + s * 78.233) * 43758.5453; return v - Math.floor(v); }

  // The challenge's name, from the page's strip ("ai-web · noter-ai").
  function challengeName() {
    try {
      var spans = document.querySelectorAll(".bar span");
      for (var i = 0; i < spans.length; i++) {
        var t = spans[i].textContent || "", at = t.lastIndexOf("·");
        var name = at === -1 ? "" : t.slice(at + 1).trim();
        if (name) return name.slice(0, 40);
      }
    } catch (e) {}
    return "this challenge";
  }

  var STAR = "M12 0C12.9 7.6 16.4 11.1 24 12C16.4 12.9 12.9 16.4 12 24C11.1 16.4 7.6 12.9 0 12C7.6 11.1 11.1 7.6 12 0Z";
  var ALMOND = "M2 20 Q30 -6 58 20 Q30 46 2 20Z";

  // ---- -1 WEB 1.0 ------------------------------------------------------------
  // The marquee and the counter frame the page, outside it: siblings of <body>
  // (viking-ai's <body> is the grey window itself at this level).
  function web10() {
    var marq = decor(make("div", "hfx-marq"));
    marq.appendChild(make("span", null, "*** Welcome to " + challengeName() + "!!! *** You are visitor no. 001337" +
      " *** Sign my guestbook!!! *** Best viewed in Internet Explorer 6 at 800x600 ***"));
    root.insertBefore(marq, document.body);
    var foot = decor(make("div", "hfx-foot"));
    var line = make("div", null, "You are visitor number ");
    var digits = make("span", "hfx-digits");
    for (var i = 0; i < 6; i++) digits.appendChild(make("i", null, "001337".charAt(i)));
    line.appendChild(digits);
    foot.appendChild(line);
    foot.appendChild(make("div", null, "Best viewed with Internet Explorer 6.0 at 800x600 · Made with Notepad"));
    root.appendChild(foot);
  }

  // ---- 2 BURN and 3 AI HORROR: fire, rain, rolling bar -----------------------
  // The fire's gradients (and the eyes' outline) in a 0x0 SVG of their own.
  var FIRE_GRADIENTS = SLOP
    ? [["back", "#3b0a7a", "#7c3aed"], ["mid", "#7c3aed", "#db2777"], ["front", "#db2777", "#f97316"], ["core", "#f9a8d4", "#fdf4ff"]]
    : [["back", "#8a0c00", "#e01e00"], ["mid", "#e83000", "#ff7a00"], ["front", "#ff6a00", "#ffc400"], ["core", "#ffd040", "#fff7d6"]];
  function addDefs() {
    var defs = decor(make("div"));
    defs.id = "hfx-defs";
    defs.innerHTML = '<svg width="0" height="0" focusable="false"><defs>' + // static markup, no page data
      '<clipPath id="hfx-almond"><path d="' + ALMOND + '"></path></clipPath>' +
      FIRE_GRADIENTS.map(function (g) {
        return '<linearGradient id="hfx-fire-' + g[0] + '" x1="0" y1="1" x2="0" y2="0">' +
          '<stop offset="0" stop-color="' + g[1] + '"></stop>' +
          '<stop offset="1" stop-color="' + g[2] + '"></stop></linearGradient>';
      }).join("") + "</defs></svg>";
    document.body.appendChild(defs);
  }

  // The board's flames (ai-mode.js buildFlames): four rows of flame shapes,
  // dark at the back, white-hot in front, each licking on its own loop, over a
  // bright bed, with embers floating up.
  var TONGUE_PATH = "M50 2C56 26 74 40 84 66C96 96 92 132 74 150C64 158 36 158 26 150" +
    "C8 132 4 98 18 70C24 58 32 50 34 36C40 48 44 52 48 52C44 38 44 18 50 2Z";
  // per row: shapes across a 1440px window, width and height (px), loop (s)
  var FIRE_ROWS = [
    { name: "back", count: 20, w: [110, 170], h: [128, 204], dur: 1.6 },
    { name: "mid", count: 26, w: [80, 120], h: [94, 153], dur: 1.2 },
    { name: "front", count: 30, w: [56, 86], h: [60, 110], dur: 0.9 },
    { name: "core", count: 24, w: [30, 50], h: [31, 60], dur: 0.7 }
  ];
  // the window's width against the 1440px the rows are counted for
  function fireScale() { return Math.max(0.35, Math.min(1.5, (window.innerWidth || 1440) / 1440)); }
  function buildFlames(box, scale) {
    box.textContent = "";
    box.setAttribute("data-scale", scale.toFixed(2));
    FIRE_ROWS.forEach(function (row, r) {
      var layer = make("div", "hfx-fl-row hfx-fl-" + row.name);
      var n = Math.max(4, Math.round(row.count * scale));
      for (var i = 0; i < n; i++) {
        var a = seeded(i, r * 3 + 1), b = seeded(i, r * 3 + 2), d = seeded(i, r * 3 + 3);
        var w = row.w[0] + a * (row.w[1] - row.w[0]);
        var h = row.h[0] + b * (row.h[1] - row.h[0]);
        var x = (i + 0.5) / n * 100 + (d - 0.5) * (60 / n);
        var shape = make("div", "hfx-fl");
        shape.style.cssText = "left:calc(" + x.toFixed(2) + "% - " + Math.round(w / 2) + "px);width:" +
          Math.round(w) + "px;height:" + Math.round(h) + "px;animation-duration:" +
          (row.dur + a * 0.5).toFixed(2) + "s;animation-delay:-" + (d * 2).toFixed(2) + "s";
        shape.innerHTML = '<svg viewBox="0 0 100 160" preserveAspectRatio="none" focusable="false">' +
          '<path d="' + TONGUE_PATH + '" fill="url(#hfx-fire-' + row.name + ')"></path></svg>';
        layer.appendChild(shape);
      }
      box.appendChild(layer);
    });
    box.appendChild(make("div", "hfx-bed"));
    var embers = Math.round((SLOP ? 26 : 18) * scale) + (SLOP ? 6 : 4);
    for (var j = 0; j < embers; j++) {
      var k = seeded(j, 9), p = seeded(j, 10), size = (3 + k * 5).toFixed(1);
      var ember = make("i", "hfx-ember");
      ember.style.cssText = "left:" + (p * 100).toFixed(1) + "%;width:" + size + "px;height:" + size +
        "px;animation-duration:" + (3 + k * 3).toFixed(1) + "s;animation-delay:-" + (p * 6).toFixed(1) + "s";
      box.appendChild(ember);
    }
  }
  var flameResize = 0;
  function addFlames() {
    var flames = decor(make("div"));
    flames.id = "hfx-flames";
    buildFlames(flames, fireScale());
    document.body.appendChild(flames);
    // a much wider or narrower window gets a row of flames to match
    window.addEventListener("resize", function () {
      clearTimeout(flameResize);
      flameResize = setTimeout(function () {
        try {
          var scale = fireScale();
          if (Math.abs(scale - parseFloat(flames.getAttribute("data-scale") || "1")) >= 0.15) buildFlames(flames, scale);
        } catch (e) {}
      }, 300);
    });
  }

  // The board's matrix rain (ai-mode.js startRain), faint, on a transparent
  // canvas behind the flames: at most 40 columns, about half of them falling at
  // a time, each at its own pace, with a pale glyph at the head. At level 3
  // it rains violet tokens. hosted-fx.css keeps it faint and fades it out
  // before it reaches the fire.
  var RAIN_SIZE = 15, RAIN_COLS = 40, RAIN_SHARE = 0.55;
  var RAIN_GLYPHS = SLOP ? "✦✧◆◇AIGPTLLM∞{}01"
    : "アイウエオカキクケコサシスセソタチツテト" +
      "0123456789ABCDEF{}<>=/$#";
  var RAIN_TRAIL = SLOP ? "#c084fc" : "#39ff14", RAIN_HEAD = SLOP ? "#fdf4ff" : "#d8ffe0";
  var rain = { raf: 0, canvas: null, cols: [], last: 0, step: 0, gap: RAIN_SIZE, w: 0 };
  function rainGlyph() { return RAIN_GLYPHS.charAt(Math.floor(Math.random() * RAIN_GLYPHS.length)); }
  function startRain() {
    if (!motionOk()) return;
    if (rain.canvas) {
      rain.canvas.style.display = "";
      if (!rain.raf) rain.raf = requestAnimationFrame(rain.draw);
      return;
    }
    var c = decor(make("canvas"));
    c.id = "hfx-rain";
    var ctx = c.getContext && c.getContext("2d");
    if (!ctx) return;
    function resize() {
      var w = window.innerWidth, h = window.innerHeight, wider = w !== rain.w;
      c.width = w; c.height = h; // clears the canvas and its settings
      ctx.font = RAIN_SIZE + "px ui-monospace, Menlo, Consolas, monospace";
      ctx.textBaseline = "top";
      ctx.textAlign = "center";
      if (!wider) return; // a phone's address bar coming and going keeps the columns
      rain.w = w;
      var n = Math.min(RAIN_COLS, Math.ceil(w / RAIN_SIZE)), rows = h / RAIN_SIZE;
      rain.gap = w / n;
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
    window.addEventListener("resize", function () { try { resize(); } catch (e) {} });
    document.body.appendChild(c);
    rain.canvas = c;
    rain.draw = function (ts) {
      rain.raf = requestAnimationFrame(rain.draw);
      if (ts - rain.last < 70) return; // ~14 steps a second: slow, and easy on the CPU
      rain.last = ts;
      rain.step++;
      var h = c.height;
      ctx.globalCompositeOperation = "destination-out"; // fade what is there
      ctx.fillStyle = "rgba(0,0,0,.08)";
      ctx.fillRect(0, 0, c.width, h);
      ctx.globalCompositeOperation = "source-over";
      for (var i = 0; i < rain.cols.length; i++) {
        var col = rain.cols[i];
        if (rain.step % col.every) continue;
        var x = (i + 0.5) * rain.gap, y = col.y * RAIN_SIZE;
        if (col.live) {
          ctx.fillStyle = RAIN_TRAIL; // the last head cools to the trail's colour
          ctx.fillText(col.prev, x, y - RAIN_SIZE);
          col.prev = rainGlyph();
          ctx.fillStyle = RAIN_HEAD;
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
  }
  function stopRain() {
    if (rain.raf) { cancelAnimationFrame(rain.raf); rain.raf = 0; }
    if (rain.canvas) rain.canvas.style.display = "none";
  }

  function addRollbar() {
    var bar = decor(make("div"));
    bar.id = "hfx-rollbar";
    document.body.appendChild(bar);
  }

  // ---- 3 AI HORROR ----------------------------------------------------------
  var BUZZ = ["Unlock the power of AI", "Let’s delve in", "This page is now AI-powered",
    "Certainly!", "Great question!", "10x your flags"];
  // three eyes in the side margins (hidden on narrow screens), ten sparkles
  var EYES = [{ l: 4, t: 15, w: 80 }, { l: 90, t: 40, w: 56 }, { l: 3, t: 68, w: 92 }];
  var SPARKS = 10;
  var avoid = []; // [element, rect(), what it must not cover: "controls" or "content"]
  function starSvg() {
    return '<svg viewBox="0 0 24 24" focusable="false"><path d="' + STAR + '"></path></svg>';
  }
  function slop() {
    var body = document.body, name = challengeName();

    // above the page: the ticker, then the summary
    var ticker = decor(make("div", "hfx-ticker")), track = make("div");
    for (var r = 0; r < 2; r++) {
      for (var b = 0; b < BUZZ.length; b++) track.appendChild(make("span", null, "✦ " + BUZZ[b]));
    }
    ticker.appendChild(track);
    var sum = make("div", "hfx-sum");
    sum.setAttribute("role", "note");
    sum.appendChild(make("b", null, "✦ AI Summary of this page"));
    sum.appendChild(make("span", null, "Certainly! This page has a title, some text and a box. Key takeaways: " +
      "the title is a title · the box is a box · you are doing great."));
    sum.appendChild(make("small", null, "AI can make mistakes. So can this summary. The page below is the real one."));
    body.insertBefore(sum, body.firstChild);
    body.insertBefore(ticker, body.firstChild);

    // behind the page: blobs and eyes
    var bg = decor(make("div"));
    bg.id = "hfx-slop-bg";
    var html = '<div class="hfx-blob hfx-b1"></div><div class="hfx-blob hfx-b2"></div>'; // static markup, no page data
    for (var e = 0; e < EYES.length; e++) {
      var eye = EYES[e];
      html += '<svg class="hfx-eye" viewBox="0 0 60 40" focusable="false" style="left:' + eye.l + "%;top:" + eye.t +
        "%;width:" + eye.w + "px;height:" + Math.round(eye.w * 2 / 3) + "px;animation-delay:-" +
        (seeded(e, 51) * 5).toFixed(2) + 's"><path class="hfx-eye-w" d="' + ALMOND + '"></path>' +
        '<g clip-path="url(#hfx-almond)"><g class="hfx-iris" style="animation-delay:-' + (seeded(e, 52) * 6).toFixed(2) + 's">' +
        '<circle class="hfx-eye-i" cx="30" cy="20" r="11"></circle><circle class="hfx-eye-p" cx="30" cy="20" r="5"></circle>' +
        '<circle class="hfx-eye-h" cx="26.5" cy="16.5" r="2"></circle></g></g>' +
        '<path class="hfx-eye-lid" d="M2 20 Q30 -6 58 20"></path></svg>';
    }
    bg.innerHTML = html;
    body.appendChild(bg);
    // an eye stays in the margins: hidden while the page's content is behind it
    var eyes = bg.querySelectorAll(".hfx-eye");
    for (var n = 0; n < eyes.length; n++) {
      avoid.push([eyes[n], (function (eye) {
        return function () {
          var x = eye.l / 100 * window.innerWidth, y = eye.t / 100 * window.innerHeight;
          return { left: x, top: y, right: x + eye.w, bottom: y + eye.w * 2 / 3 };
        };
      })(EYES[n]), "content"]);
    }

    // over the page: the vignette and sparkles
    var top = decor(make("div"));
    top.id = "hfx-slop-top";
    top.appendChild(make("div", "hfx-vig"));
    for (var s = 0; s < SPARKS; s++) {
      var spark = make("span", "hfx-spark hfx-sp" + (s % 4));
      var left = 2 + seeded(s, 31) * 94, topPct = 6 + seeded(s, 32) * 86, size = Math.round(8 + seeded(s, 33) * 14);
      spark.style.cssText = "left:" + left.toFixed(1) + "%;top:" + topPct.toFixed(1) + "%;width:" + size + "px;height:" +
        size + "px;animation-duration:" + (1.6 + seeded(s, 34) * 1.8).toFixed(2) + "s;animation-delay:-" +
        (seeded(s, 35) * 3).toFixed(2) + "s";
      spark.innerHTML = starSvg();
      top.appendChild(spark);
      // its place untransformed (it twinkles from nothing to full size)
      avoid.push([spark, (function (l, t, z) {
        return function () {
          var x = l / 100 * window.innerWidth, y = t / 100 * window.innerHeight;
          return { left: x, top: y, right: x + z, bottom: y + z };
        };
      })(left, topPct, size), "controls"]);
    }
    body.appendChild(top);

    // the toasts, taking turns
    var toasts = decor(make("div"));
    toasts.id = "hfx-toasts";
    var said = ["Someone just rooted " + name + ". You could be next! ✦", "This page was summarised for you ✦",
      "How are we doing? ★★★★★"];
    for (var t = 0; t < said.length; t++) {
      var toast = make("div", "hfx-toast"), icon = make("span", "hfx-t-ic");
      toast.style.animationDelay = (0.6 + t * 4) + "s";
      icon.innerHTML = starSvg();
      toast.appendChild(icon);
      toast.appendChild(make("span", null, said[t]));
      toasts.appendChild(toast);
    }
    body.appendChild(toasts);
    avoid.push([toasts, function () { return toasts.getBoundingClientRect(); }, "controls"]);
    watchControls();
  }

  // A toast or sparkle never sits over an input, button or the like, and an
  // eye never behind the page's own blocks: while it would, it is hidden.
  // Checked on scroll, resize and focus, and every second (a page can grow,
  // Swagger UI's above all).
  var AVOID = {
    controls: "input, textarea, select, button",
    content: ".wrap, .ai-frame, body > .bar, .nav-bar, .hero-message, .staff-tool, .listing-grid, " +
      ".product-container, .center, .search-results, .footer-bar, .hfx-sum, .hfx-ticker"
  };
  var guardQueued = false;
  function inView(sel) {
    var vw = window.innerWidth, vh = window.innerHeight, boxes = [], els = document.querySelectorAll(sel);
    for (var i = 0; i < els.length; i++) {
      var c = els[i].getBoundingClientRect();
      if (c.width && c.height && c.bottom > 0 && c.top < vh && c.right > 0 && c.left < vw) boxes.push(c);
    }
    return boxes;
  }
  function guard() {
    guardQueued = false;
    try {
      var found = {};
      for (var j = 0; j < avoid.length; j++) {
        var kind = avoid[j][2], boxes = found[kind] || (found[kind] = inView(AVOID[kind]));
        var a = avoid[j][1](), hit = false;
        for (var k = 0; k < boxes.length && !hit; k++) {
          var b = boxes[k];
          hit = a.left - 8 < b.right && b.left < a.right + 8 && a.top - 8 < b.bottom && b.top < a.bottom + 8;
        }
        if (hit) avoid[j][0].classList.add("hfx-hide");
        else avoid[j][0].classList.remove("hfx-hide");
      }
    } catch (e) {}
  }
  function queueGuard() {
    if (guardQueued) return;
    guardQueued = true;
    requestAnimationFrame(guard);
  }
  function watchControls() {
    guard();
    window.addEventListener("scroll", queueGuard, { passive: true, capture: true });
    window.addEventListener("resize", queueGuard);
    document.addEventListener("focusin", queueGuard);
    setInterval(queueGuard, 1000);
  }

  // ---- start ---------------------------------------------------------------
  function build() {
    if (LEVEL === "-1") { web10(); return; }
    addDefs();
    addFlames();
    startRain();
    addRollbar();
    if (SLOP) slop();
    var follow = function () { try { if (motionOk()) startRain(); else stopRain(); } catch (e) {} };
    if (motion && motion.addEventListener) motion.addEventListener("change", follow);
    else if (motion && motion.addListener) motion.addListener(follow);
  }
  // Only once the page is parsed and hosted-fx.css has applied: without the
  // stylesheet the layers would be bare, so a page whose CSS never came gets
  // nothing at all.
  function styled() {
    try { return getComputedStyle(root).getPropertyValue("--hfx-kit").trim() === "1"; } catch (e) { return false; }
  }
  var tries = 0;
  function whenReady() {
    if (document.body && styled()) {
      try { build(); } catch (e) {}
      return;
    }
    if (++tries <= 75) setTimeout(whenReady, 200); // gives up after ~15 s
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", whenReady);
  else whenReady();
})();
