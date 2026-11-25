/* =========================================================================
   FIRST BLOOD  -  the first team to solve a challenge gets a moment
   Linked from CTFd's theme_footer by ctf.sh, after ai-mode.js, except in a
   preview (see platform/theme/README.md, "First blood").

   The ctf_firstblood plugin (platform/plugins/) lists each challenge's first
   solve of the last quarter of an hour at /first-blood/feed. Every page asks it
   every few seconds while the tab is visible and announces what is new:

     - the Scoreboard page (the one on the big screen) gets the show: blood on
       a machine. For two seconds the page goes dark behind hex rain and
       scanlines while a frame with the solve's number and time draws itself
       and the line of a cut is traced across it; then a blade crosses the
       screen, FIRST and BLOOD slam in on two beats while the picture tears,
       blood sprays and drips from the letters, the team's name resolves
       out of noise, the challenge follows, the announcement shows as an xxd
       hexdump of its real bytes, and at the end the screen switches off. With
       the sound turned on (the control under the page title, off until someone
       turns it on, remembered per browser) it has a deep note that grows
       through the intro, two
       impacts, a sub-bass drop, low brass, a heartbeat and a deep voice saying
       "first blood" (first-blood.mp3, on the two beats);
     - every other page gets a small banner at the top, never a sound;
     - the player who drew it gets FIRST BLOOD stamped on the solve moment
       (ai-mode.js, celebrate).

   The same feed carries a revision of the standings, so the Scoreboard page
   fetches its table and graph again within seconds of a solve.

   What a browser has announced is kept in localStorage (ctf-fb-seen), so a
   reload or another tab never repeats it. Only a first blood of the last five
   minutes is announced, at most three in a row, and a browser's first visit
   announces nothing: opening the board mid-event doesn't replay the day.

   Team and challenge names are other people's text: they only ever go in as
   textContent. Every word comes from i18n.strings.js (window.ctfI18n).
   For the organisers: window.ctfFirstBlood.demo("Team", "challenge") plays the
   show on demand, and so does Test next to the sound control.
   ========================================================================= */
(function () {
  "use strict";

  var root = document.documentElement;
  if (root.hasAttribute("data-ctf-preview")) return; // a preview saves no solve

  // The voice: "FIRST BLOOD", next to this file. VOICE_BEATS is where its two
  // words start, in seconds (tools/first-blood-voice.py prints them); the title's
  // two words land on them.
  var SELF = (document.currentScript && document.currentScript.src) || "";
  var VOICE_URL = /first-blood\.js(\?.*)?$/.test(SELF) ? SELF.replace(/first-blood\.js(\?.*)?$/, "first-blood.mp3") : "";
  var VOICE_BEATS = [0.14, 0.63];

  var SEEN_KEY = "ctf-fb-seen";   // what this browser has announced: {"<solve id>@<time>": when}
  var SOUND_KEY = "ctf-fb-sound"; // "on" once someone turned the sound on here
  var FRESH = 300;                // seconds: an older first blood is never announced
  var MAX_QUEUE = 3;              // most announcements in a row
  var POLL_BOARD = 4000, POLL_PAGE = 12000, POLL_RETRY = 30000;
  var REFRESH_GAP = 10000;        // the board is fetched again at most this often
  var TOAST_MS = 6500;
  // The show's clock, in ms from its start. First the intro: the screen comes up
  // while one deep note grows under it. Then FIRST lands on B0 and BLOOD on B1.
  var INTRO = 1900;
  var B0 = INTRO;
  var B1 = B0 + Math.round((VOICE_BEATS[1] - VOICE_BEATS[0]) * 1000);
  var TEAM_AT = B1 + 800, CHAL_AT = B1 + 1450;
  var HEART = 1.06;               // seconds between the heartbeats behind the names
  var GLITCHES = [B1 + 2350, B1 + 4150]; // when the picture tears, and crackles, while the names stand
  var SHOW_MS = 8800, OUT_MS = 650;
  // How long a name takes to resolve out of noise.
  function decodeMs(name) { return Math.min(900, 260 + String(name).length * 34); }

  var L = window.ctfI18n;
  var t = L.t, bind = L.bind, bindAttr = L.bindAttr;

  var motionQuery = null;
  try { motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)"); } catch (e) {}
  function motionOk() { return !(motionQuery && motionQuery.matches); }

  function make(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }
  function rand(a, b) { return a + Math.random() * (b - a); }
  function stored(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  // What CTFd's base template says about the viewer (CTFd.config keeps only part of it).
  function init() { return window.init || {}; }
  function urlRoot() { return init().urlRoot || ((window.CTFd && window.CTFd.config) || {}).urlRoot || ""; }
  function onBoard() { return /\/scoreboard\/?$/.test(location.pathname); }
  // The viewer's own account: the team in teams mode, else the user.
  function myAccount() {
    var i = init();
    var id = i.userMode === "users" ? i.userId : i.teamId;
    return typeof id === "number" && id > 0 ? id : null;
  }

  // ---- sound ---------------------------------------------------------------------
  // All of it is made here with Web Audio except the voice. A browser only lets
  // a page make sound after a click or a key press on it, so "armed" is what the
  // control shows once that has happened; until then the show plays silently.
  var Sound = (function () {
    var AC = window.AudioContext || window.webkitAudioContext;
    var ctx = null, bus = null, voice = null, onChange = function () {};

    function on() { return !!AC && stored(SOUND_KEY) === "on"; }
    function armed() { return !!ctx && ctx.state === "running"; }

    // One second of white noise, looped by everything that hisses.
    function noiseBuffer(c) {
      var buf = c.createBuffer(1, c.sampleRate, c.sampleRate), d = buf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      return buf;
    }
    // A hall: decaying stereo noise whose highs die first.
    function hall(c) {
      var n = Math.floor(c.sampleRate * 2.6), buf = c.createBuffer(2, n, c.sampleRate);
      for (var ch = 0; ch < 2; ch++) {
        var d = buf.getChannelData(ch), low = 0;
        for (var i = 0; i < n; i++) {
          var x = i / n, a = 0.3 + 0.62 * x;
          low = a * low + (1 - a) * (Math.random() * 2 - 1);
          d[i] = low * Math.pow(1 - x, 2.6);
        }
      }
      return buf;
    }
    function shaper(c, fn) {
      var curve = new Float32Array(1024);
      for (var i = 0; i < 1024; i++) curve[i] = fn(i / 512 - 1);
      var w = c.createWaveShaper();
      w.curve = curve;
      return w;
    }
    function drive(c) { return shaper(c, function (x) { return Math.tanh(3 * x); }); }
    // Eight steps instead of a smooth line: three bits, the sound of bad data.
    function crush(c) { return shaper(c, function (x) { return Math.round(x * 4) / 4; }); }

    // Everything but the voice (the effects, sfx, and the bass, low) goes through
    // a compressor that glues it together, a shelf that lifts the lows and a
    // limiter, and then through `duck`, which is what steps back while the voice
    // speaks. It has to sit after the compressor: turned down before it, the
    // compressor would just turn everything back up. The voice joins after all
    // that, so no impact, however big, squashes a word, and a last limiter only
    // catches what the sum would clip.
    function build() {
      var c = new AC();
      var master = c.createGain();
      master.gain.value = 0.88;
      master.connect(c.destination);
      var safety = c.createDynamicsCompressor();
      safety.threshold.value = -1.5; safety.knee.value = 0; safety.ratio.value = 20;
      safety.attack.value = 0.001; safety.release.value = 0.08;
      safety.connect(master);
      var duck = c.createGain();
      duck.connect(safety);
      var limiter = c.createDynamicsCompressor();
      limiter.threshold.value = -4; limiter.knee.value = 1; limiter.ratio.value = 20;
      limiter.attack.value = 0.001; limiter.release.value = 0.1;
      limiter.connect(duck);
      var shelf = c.createBiquadFilter();
      shelf.type = "lowshelf"; shelf.frequency.value = 110; shelf.gain.value = 4;
      shelf.connect(limiter);
      var comp = c.createDynamicsCompressor();
      comp.threshold.value = -14; comp.knee.value = 8; comp.ratio.value = 3;
      comp.attack.value = 0.004; comp.release.value = 0.22;
      comp.connect(shelf);
      // the compressor adds its own make-up gain: come in low, so that only the big hits reach the limiter
      var pre = c.createGain();
      pre.gain.value = 0.3;
      pre.connect(comp);
      var sfx = c.createGain(), low = c.createGain();
      sfx.connect(pre); low.connect(pre);
      var verb = c.createConvolver(), wet = c.createGain(), send = c.createGain();
      verb.buffer = hall(c);
      wet.gain.value = 0.55;
      send.connect(verb); verb.connect(wet); wet.connect(sfx);
      ctx = c;
      bus = { out: safety, duck: duck, sfx: sfx, low: low, send: send, noise: noiseBuffer(c) };
      c.onstatechange = function () { onChange(); };
      if (VOICE_URL) {
        fetch(VOICE_URL).then(function (r) {
          if (!r.ok) throw new Error("no voice");
          return r.arrayBuffer();
        }).then(function (data) {
          // the callback form: Safari's decodeAudioData returned no promise for years
          c.decodeAudioData(data, function (buf) { voice = buf; }, function () {});
        }).catch(function () {});
      }
    }

    // Create the context when the sound is on; inside a click or key press this
    // also starts it. Safe to call again and again.
    function arm() {
      if (!on()) return;
      try {
        if (!ctx) build();
        if (ctx.state !== "running") { var p = ctx.resume(); if (p && p.catch) p.catch(function () {}); }
      } catch (e) {}
      onChange();
    }

    // -- the instruments: (when, ...) in the context's seconds --
    function wire(node, verb, to) {
      node.connect(to || bus.sfx);
      if (verb) { var s = ctx.createGain(); s.gain.value = verb; node.connect(s); s.connect(bus.send); }
    }
    // A pitched hit: an oscillator sliding f0 -> f1 that dies over dur.
    function tone(when, type, f0, f1, dur, peak, verb, attack) {
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.type = type;
      o.frequency.setValueAtTime(f0, when);
      o.frequency.exponentialRampToValueAtTime(f1, when + dur);
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(peak, when + (attack || 0.006));
      g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
      o.connect(g); wire(g, verb);
      o.start(when); o.stop(when + dur + 0.05);
    }
    // Bass you feel: a sine dropping f0 -> f1, on the bass path, that falls to a
    // sixteenth of its level over dur and then lets go (a ramp to nothing would
    // be gone after a fifth of it). A driven copy adds the overtones a laptop's
    // speakers need to show it at all.
    function bass(node) {
      var d = drive(ctx), lp = ctx.createBiquadFilter(), dg = ctx.createGain();
      lp.type = "lowpass"; lp.frequency.value = 260;
      dg.gain.value = 0.34;
      node.connect(bus.low);
      node.connect(d); d.connect(lp); lp.connect(dg); dg.connect(bus.low);
    }
    function boom(when, f0, f1, dur, peak, attack) {
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.type = "sine";
      o.frequency.setValueAtTime(f0, when);
      o.frequency.exponentialRampToValueAtTime(f1, when + dur * 0.7);
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(peak, when + (attack || 0.012));
      g.gain.exponentialRampToValueAtTime(peak / 16, when + dur);
      g.gain.linearRampToValueAtTime(0, when + dur + 0.08);
      o.connect(g); bass(g);
      o.start(when); o.stop(when + dur + 0.12);
    }
    // The intro: one deep note (and its octave, quieter), there from the first
    // moment and growing all the way, bending up at the end into what comes
    // next, and let go a moment before it so the hit lands in silence.
    function swell(when, dur, peak) {
      [[31, 42, 1], [62, 84, 0.32]].forEach(function (v) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.type = "sine";
        o.frequency.setValueAtTime(v[0], when);
        o.frequency.setValueAtTime(v[0], when + dur * 0.62);
        o.frequency.exponentialRampToValueAtTime(v[1], when + dur);
        g.gain.setValueAtTime(0, when);
        g.gain.linearRampToValueAtTime(peak * v[2] * 0.3, when + 0.25);
        g.gain.linearRampToValueAtTime(peak * v[2], when + dur - 0.08);
        g.gain.linearRampToValueAtTime(0, when + dur);
        o.connect(g); bass(g);
        o.start(when); o.stop(when + dur + 0.05);
      });
    }
    // Filtered noise whose filter slides f0 -> f1; rising swells, else it dies.
    function hiss(when, dur, peak, type, f0, f1, q, verb, rising) {
      var src = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      src.buffer = bus.noise; src.loop = true;
      f.type = type; f.Q.value = q;
      f.frequency.setValueAtTime(f0, when);
      f.frequency.exponentialRampToValueAtTime(f1, when + dur);
      if (rising) {
        g.gain.setValueAtTime(0.0001, when);
        g.gain.exponentialRampToValueAtTime(peak, when + dur);
        g.gain.linearRampToValueAtTime(0, when + dur + 0.04);
      } else {
        g.gain.setValueAtTime(peak, when);
        g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
      }
      src.connect(f); f.connect(g); wire(g, verb);
      src.start(when); src.stop(when + dur + 0.1);
    }
    // The long, distorted low brass of a film trailer, swelling over `swell` seconds.
    function braam(when, swell, dur, peak) {
      var mix = ctx.createGain(), lp = ctx.createBiquadFilter(), g = ctx.createGain(), d = drive(ctx);
      [41.2, 55, 55.7, 82.4, 110.4].forEach(function (hz, i) {
        var o = ctx.createOscillator(), og = ctx.createGain();
        o.type = "sawtooth"; o.frequency.value = hz;
        og.gain.value = i < 3 ? 0.45 : 0.2;
        o.connect(og); og.connect(mix);
        o.start(when); o.stop(when + dur + 0.1);
      });
      lp.type = "lowpass"; lp.Q.value = 1.2;
      lp.frequency.setValueAtTime(420, when);
      lp.frequency.exponentialRampToValueAtTime(1000, when + swell);
      lp.frequency.exponentialRampToValueAtTime(150, when + dur);
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(peak * 0.25, when + 0.04);
      g.gain.exponentialRampToValueAtTime(peak, when + swell);
      g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
      mix.connect(lp); lp.connect(d); d.connect(g); wire(g, 0.6);
    }
    // A floor of bass under the names: two low notes a fifth apart, in and out slowly.
    function drone(when, dur, peak) {
      [36.7, 55].forEach(function (hz, i) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.type = "sine"; o.frequency.value = hz;
        g.gain.setValueAtTime(0.0001, when);
        g.gain.exponentialRampToValueAtTime(peak * (i ? 0.6 : 1), when + 0.9);
        g.gain.setValueAtTime(peak * (i ? 0.6 : 1), when + dur - 0.5);
        g.gain.linearRampToValueAtTime(0, when + dur);
        o.connect(g); g.connect(bus.low);
        o.start(when); o.stop(when + dur + 0.05);
      });
    }
    function heartbeat(when, peak) {
      boom(when, 60, 34, 0.24, peak, 0.008);
      boom(when + 0.19, 52, 31, 0.28, peak * 0.62, 0.008);
    }
    // -- the machine's own noise --
    // The signal tearing: a few bursts of three-bit noise.
    function crackle(when, n, peak) {
      for (var k = 0; k < n; k++) {
        var src = ctx.createBufferSource(), f = ctx.createBiquadFilter(), c = crush(ctx), g = ctx.createGain(), at = when + k * 0.04;
        src.buffer = bus.noise; src.loop = true;
        f.type = "bandpass"; f.Q.value = 2.5; f.frequency.value = rand(700, 4200);
        g.gain.setValueAtTime(peak, at);
        g.gain.setValueAtTime(0, at + 0.024);
        src.connect(f); f.connect(c); c.connect(g); wire(g, 0.15);
        src.start(at); src.stop(at + 0.03);
      }
    }
    // The browser's own voice, pitched all the way down, when the file is missing.
    function speak(after) {
      try {
        var u = new SpeechSynthesisUtterance("First blood");
        u.lang = "en-US"; u.pitch = 0.1; u.rate = 0.72; u.volume = 1;
        setTimeout(function () { try { window.speechSynthesis.speak(u); } catch (e) {} }, after);
      } catch (e) {}
    }

    // The show's sound, from now. False when nothing can play yet.
    function play() {
      if (!on()) return false;
      arm();
      if (!armed()) return false;
      try {
        var t0 = ctx.currentTime + 0.03, b0 = t0 + B0 / 1000, b1 = t0 + B1 / 1000;
        var team = t0 + TEAM_AT / 1000;
        var duck = bus.duck.gain;
        duck.cancelScheduledValues(t0);
        duck.setValueAtTime(1, t0);
        // the intro: a deep note growing for as long as the screen takes to come
        // up, brass growling up under it, the air sucked out of the room at the
        // end, and then the blade
        var intro = B0 / 1000;
        swell(t0, intro - 0.05, 0.26);
        braam(t0 + 0.25, intro - 0.36, intro - 0.28, 0.12);
        hiss(b0 - 0.6, 0.58, 0.16, "bandpass", 300, 5200, 1.4, 0.3, true);
        hiss(b0 - 0.06, 0.34, 0.2, "bandpass", 7600, 3200, 7, 0.5);
        [2637, 3951, 5274].forEach(function (hz, i) { tone(b0 - 0.04, "sine", hz, hz * 0.995, 0.7 - i * 0.12, 0.06, 0.8); });
        // FIRST: the picture tears just before it, then the hit
        crackle(b0 - 0.13, 3, 0.36);
        tone(b0, "sine", 165, 46, 0.22, 0.8, 0.2);
        boom(b0, 76, 40, 0.5, 0.75);
        hiss(b0, 0.08, 0.3, "highpass", 2200, 1800, 0.7, 0.3);
        // BLOOD: the big one. The sub drops with the word and keeps rumbling
        // under the names; the brass swells up once the word is out.
        crackle(b1 - 0.15, 3, 0.4);
        tone(b1, "sine", 150, 38, 0.32, 0.9, 0.25);
        boom(b1, 72, 30, 2.7, 1.0, 0.04);
        boom(b1 + 0.02, 132, 60, 0.9, 0.28, 0.03);
        hiss(b1, 0.07, 0.3, "highpass", 2400, 1700, 0.7, 0.3);
        hiss(b1 + 0.01, 0.26, 0.3, "lowpass", 1100, 170, 0.9, 0.4);
        braam(b1, 0.9, 3.0, 0.42);
        // a heart under the names, on the red pulse behind them (first-blood.css, ctf-fb-heart)
        [0.4, 0.36, 0.3, 0.24].forEach(function (peak, i) { heartbeat(team + 0.065 + i * HEART, peak); });
        // and a floor of bass from there until the screen goes dark
        drone(b1 + 1.6, (SHOW_MS - OUT_MS) / 1000 - (B1 / 1000 + 1.6) + 0.1, 0.2);
        // the picture tearing while they stand (GLITCHES), and the screen switching off
        GLITCHES.forEach(function (ms) { crackle(t0 + ms / 1000, 4, 0.3); });
        var off = t0 + (SHOW_MS - OUT_MS) / 1000;
        tone(off, "sine", 1500, 60, 0.3, 0.3, 0.3);
        boom(off + 0.02, 90, 32, 0.45, 0.5);
        hiss(off, 0.05, 0.14, "highpass", 3000, 2500, 0.7, 0.2);
        if (voice) {
          var src = ctx.createBufferSource(), vg = ctx.createGain();
          src.buffer = voice;
          vg.gain.value = 0.92;
          src.connect(vg); vg.connect(bus.out);
          src.start(Math.max(t0, b0 - VOICE_BEATS[0]));
          // Everything else steps back while it speaks: the hit of each word
          // still lands, at half, and then makes room. Once "blood" is out it
          // all comes up again, so the sub swells in right behind the word.
          duck.setValueAtTime(1, b0 - 0.02);
          duck.linearRampToValueAtTime(0.5, b0);
          duck.linearRampToValueAtTime(0.26, b0 + 0.12);
          duck.setValueAtTime(0.26, b1 - 0.03);
          duck.linearRampToValueAtTime(0.5, b1);
          duck.linearRampToValueAtTime(0.26, b1 + 0.12);
          duck.setValueAtTime(0.26, b1 + 0.42);
          duck.linearRampToValueAtTime(1, b1 + 0.8);
        } else {
          speak(B0 - 120);
        }
        return true;
      } catch (e) { return false; }
    }

    return {
      supported: !!AC,
      on: on,
      armed: armed,
      arm: arm,
      play: play,
      set: function (value) { store(SOUND_KEY, value ? "on" : "off"); if (value) arm(); else onChange(); },
      changed: function (fn) { onChange = fn; }
    };
  })();

  // ---- the show (the Scoreboard page) ------------------------------------------------
  var showing = null; // {layer, timers, done}

  // Where a drip can hang from a letter, as a share of its width: under a stroke,
  // not under the gap of an R or the hollow of an A.
  var DRIP_AT = { F: 0.2, I: 0.5, R: 0.2, S: 0.5, T: 0.5, B: 0.22, L: 0.22, O: 0.5, D: 0.22 };

  function titleWord(word, cls, bleeds) {
    var el = make("span", "ctf-fb-word " + cls);
    el.setAttribute("data-text", word); // its red and cyan ghosts (first-blood.css)
    Array.prototype.forEach.call(word, function (ch) {
      var letter = make("span", "ctf-fb-ch", ch);
      if (bleeds && motionOk() && Math.random() < 0.7) {
        var drip = make("i", "ctf-fb-drip");
        var at = DRIP_AT[ch.toUpperCase()];
        drip.style.cssText = "left:" + ((at == null ? 0.5 : at) * 100) + "%;--fb-len:" + rand(0.22, 0.8).toFixed(2) +
          "em;--fb-wide:" + rand(0.045, 0.075).toFixed(3) + "em;animation-delay:" + Math.round(B1 + rand(150, 1500)) +
          "ms;animation-duration:" + Math.round(rand(1800, 3600)) + "ms";
        letter.appendChild(drip);
      }
      el.appendChild(letter);
    });
    return el;
  }

  // The name resolves out of noise, left to right.
  function decode(el, text, ms) {
    var chars = Array.from(text), glyphs = "!<>-_\\/[]{}=+*^?#$%&01", start = null;
    function frame(now) {
      if (!el.isConnected) return;
      if (start === null) start = now;
      var p = Math.min(1, (now - start) / ms), locked = Math.floor(p * chars.length), out = "";
      for (var i = 0; i < chars.length; i++) {
        out += i < locked || chars[i] === " " ? chars[i] : glyphs.charAt(Math.floor(Math.random() * glyphs.length));
      }
      el.textContent = out;
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function shake(el, px, ms) {
    if (!el || !el.animate || !motionOk()) return;
    el.animate([
      { transform: "translate(0, 0)" }, { transform: "translate(" + -px + "px, " + px * 0.5 + "px) rotate(-.5deg)" },
      { transform: "translate(" + px * 0.8 + "px, " + -px * 0.6 + "px) rotate(.4deg)" },
      { transform: "translate(" + -px * 0.5 + "px, " + px * 0.3 + "px)" },
      { transform: "translate(" + px * 0.25 + "px, " + -px * 0.15 + "px)" }, { transform: "translate(0, 0)" }
    ], { duration: ms, easing: "ease-out" });
  }

  // Drops thrown out from the middle of the title, falling.
  function spray(layer, n) {
    if (!layer.animate || !motionOk()) return;
    var w = window.innerWidth, h = window.innerHeight;
    for (var i = 0; i < n; i++) {
      var drop = make("i", "ctf-fb-drop"), size = rand(4, 13), angle = rand(-Math.PI, 0), speed = rand(0.18, 0.62) * w;
      var dx = Math.cos(angle) * speed, up = Math.sin(angle) * rand(0.12, 0.42) * h;
      drop.style.cssText = "width:" + size + "px;height:" + size * rand(1.1, 1.8) + "px;left:" + (w / 2 + rand(-w * 0.14, w * 0.14)) +
        "px;top:" + h * 0.4 + "px";
      layer.appendChild(drop);
      drop.animate([
        { transform: "translate(0, 0) scale(1)", opacity: 1, easing: "cubic-bezier(.2,.7,.4,1)" },
        { transform: "translate(" + dx * 0.6 + "px, " + up + "px) scale(1)", opacity: 1, offset: 0.35, easing: "cubic-bezier(.5,0,.9,.5)" },
        { transform: "translate(" + dx + "px, " + (h * 0.75) + "px) scale(.6)", opacity: 0.9 }
      ], { duration: rand(1100, 2000), delay: rand(0, 120), fill: "both" });
    }
  }

  function chip(cls, text) { return make("span", "ctf-fb-chip " + cls, text); }

  // -- the machine around the blood --

  // Hex falling behind everything, in red: columns of digits with a pale head,
  // each at its own pace, thinning out towards the middle where the words are.
  // Drawn at half size and stretched (first-blood.css), which costs a quarter
  // and suits it. Returns the function that stops it.
  function rain(canvas) {
    var g = canvas.getContext && canvas.getContext("2d");
    if (!g || !motionOk()) return function () {};
    var w = canvas.width = Math.round(window.innerWidth / 2), h = canvas.height = Math.round(window.innerHeight / 2);
    var cell = Math.max(9, Math.round(w / 86)), cols = Math.ceil(w / cell), drops = [], HEX = "0123456789ABCDEF";
    for (var i = 0; i < cols; i++) drops.push({ y: rand(-h, 0), v: rand(0.5, 1.25), on: Math.random() < 0.62 });
    g.font = "bold " + Math.round(cell * 0.95) + "px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
    g.textAlign = "center";
    // 0 in the middle of the screen, 1 from about two thirds of the way out
    function edge(x, y) {
      var dx = (x / w - 0.5) / 0.36, dy = (y / h - 0.5) / 0.42, d = Math.sqrt(dx * dx + dy * dy);
      return Math.max(0, Math.min(1, (d - 0.55) / 0.9));
    }
    var raf = 0, last = 0;
    function frame(now) {
      raf = requestAnimationFrame(frame);
      if (now - last < 48) return; // about twenty frames a second is plenty
      last = now;
      g.globalCompositeOperation = "destination-out"; // fade what is there, keeping the canvas see-through
      g.fillStyle = "rgba(0,0,0,.14)";
      g.fillRect(0, 0, w, h);
      g.globalCompositeOperation = "source-over";
      for (var i = 0; i < cols; i++) {
        var d = drops[i];
        if (!d.on) { if (Math.random() < 0.004) d.on = true; continue; }
        var x = i * cell + cell / 2, a = edge(x, d.y);
        if (a > 0.02) {
          g.fillStyle = "rgba(255,46,31," + (0.85 * a).toFixed(2) + ")";
          g.fillText(HEX.charAt(Math.floor(Math.random() * 16)), x, d.y - cell);
          g.fillStyle = "rgba(255,217,210," + a.toFixed(2) + ")";
          g.fillText(HEX.charAt(Math.floor(Math.random() * 16)), x, d.y);
        }
        d.y += cell * d.v;
        if (d.y > h + cell * 2) { d.y = rand(-h * 0.4, 0); d.v = rand(0.5, 1.25); d.on = Math.random() < 0.7; }
      }
    }
    raf = requestAnimationFrame(frame);
    return function () { cancelAnimationFrame(raf); };
  }

  // The announcement as `xxd` prints it: offset, sixteen bytes in hex, and the
  // same bytes as text. The bytes are the real ones (UTF-8), so it can be read back.
  function hexdump(text, lines) {
    var bytes;
    try { bytes = new TextEncoder().encode(text); }
    catch (e) { bytes = Array.prototype.map.call(unescape(encodeURIComponent(text)), function (ch) { return ch.charCodeAt(0); }); }
    var out = [];
    for (var off = 0; off < bytes.length && out.length < lines; off += 16) {
      var hex = "", ascii = "";
      for (var i = 0; i < 16; i++) {
        var b = bytes[off + i];
        hex += (b === undefined ? "  " : (b < 16 ? "0" : "") + b.toString(16)) + (i % 2 ? " " : "");
        if (b !== undefined) ascii += b >= 32 && b < 127 ? String.fromCharCode(b) : ".";
      }
      out.push(("0000000" + off.toString(16)).slice(-8) + ": " + hex + " " + ascii);
    }
    return out;
  }

  function two(n) { return (n < 10 ? "0" : "") + n; }
  function hex4(n) { return "0x" + ("000" + (Number(n) || 0).toString(16).toUpperCase()).slice(-4); }

  // The frame around the screen: corner brackets, LIVE and the solve's number,
  // when it happened, and the hexdump.
  function hud(e) {
    var box = make("div", "ctf-fb-hud");
    ["tl", "tr", "bl", "br"].forEach(function (c) { box.appendChild(make("i", "ctf-fb-corner ctf-fb-" + c)); });
    var live = make("div", "ctf-fb-read ctf-fb-read-tl");
    live.appendChild(make("b", "ctf-fb-dot"));
    live.appendChild(make("span", null, t("fb.hud.live")));
    live.appendChild(make("span", "ctf-fb-dimmer", t("fb.hud.solve", { id: hex4(e.id) })));
    box.appendChild(live);
    var d = e.ts ? new Date(e.ts * 1000) : new Date();
    box.appendChild(make("div", "ctf-fb-read ctf-fb-read-tr",
      d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate()) + " " +
      two(d.getHours()) + ":" + two(d.getMinutes()) + ":" + two(d.getSeconds())));
    var dump = make("div", "ctf-fb-read ctf-fb-hex");
    hexdump(t("fb.title") + "\n" + String(e.account || "") + "\n" + String(e.challenge || "") + "\n", 4).forEach(function (line, i) {
      var row = make("div", null, line);
      row.style.setProperty("--fb-i", i);
      dump.appendChild(row);
    });
    box.appendChild(dump);
    return box;
  }

  // The picture tears: the title's ghosts slip sideways for a moment (first-blood.css,
  // .ctf-fb-tear) and blocks of bad data blink around the screen.
  var BLOCKS = ["rgba(255,46,31,.8)", "rgba(0,229,255,.55)", "rgba(255,255,255,.85)", "rgba(255,46,31,.5)"];
  function tear(layer, n, ms) {
    if (!motionOk()) return;
    layer.classList.add("ctf-fb-tear");
    setTimeout(function () { layer.classList.remove("ctf-fb-tear"); }, ms);
    if (!layer.animate) return;
    var w = window.innerWidth, h = window.innerHeight;
    for (var i = 0; i < n; i++) {
      var block = make("i", "ctf-fb-block");
      block.style.cssText = "left:" + rand(0, w * 0.92) + "px;top:" + rand(0, h * 0.96) + "px;width:" + rand(30, 240) +
        "px;height:" + rand(4, 22) + "px;background:" + BLOCKS[i % BLOCKS.length];
      layer.appendChild(block);
      var gone = block.animate([{ opacity: 0 }, { opacity: 1, offset: 0.1 }, { opacity: 1, offset: 0.8 }, { opacity: 0 }],
        { duration: rand(70, 190), delay: rand(0, ms * 0.8), fill: "both", easing: "steps(3)" });
      gone.onfinish = (function (el) { return function () { if (el.parentNode) el.parentNode.removeChild(el); }; })(block);
    }
  }

  function endShow() {
    var s = showing;
    if (!s) return;
    showing = null;
    s.timers.forEach(clearTimeout);
    s.stopRain();
    document.removeEventListener("keydown", s.onKey, true);
    if (s.layer.parentNode) s.layer.parentNode.removeChild(s.layer);
    s.done();
  }

  // e: an event from the feed. done() once the page is its own again.
  function show(e, done) {
    endShow();
    var layer = make("div", "ctf-fb");
    layer.id = "ctf-fb";
    layer.setAttribute("aria-hidden", "true"); // #ctf-fb-live says it in words
    layer.setAttribute("data-lane", e.bracket === "ai" ? "ai" : "normal");
    layer.style.setProperty("--fb-b0", B0 + "ms");
    layer.style.setProperty("--fb-b1", B1 + "ms");
    layer.style.setProperty("--fb-team", TEAM_AT + "ms");
    layer.style.setProperty("--fb-chal", CHAL_AT + "ms");
    layer.style.setProperty("--fb-heart", HEART + "s");
    layer.style.setProperty("--fb-show", SHOW_MS + "ms");
    // .ctf-fb-screen is everything that is "on the monitor": it is what switches
    // off at the end. The scanlines lie over it.
    layer.innerHTML = '<div class="ctf-fb-dim"></div><div class="ctf-fb-screen">' +
      '<canvas class="ctf-fb-rain"></canvas><div class="ctf-fb-charge"></div><div class="ctf-fb-pulse"></div>' +
      '<div class="ctf-fb-cut"><u></u><i></i><b></b></div><div class="ctf-fb-bloom"></div></div>' +
      '<div class="ctf-fb-scan"><i></i></div><div class="ctf-fb-off"></div>';
    var screen = layer.querySelector(".ctf-fb-screen");

    var stage = make("div", "ctf-fb-stage");
    var kicker = make("div", "ctf-fb-kicker");
    var typed = make("span", null, t("fb.kicker"));
    typed.style.setProperty("--fb-n", String(t("fb.kicker")).length);
    kicker.appendChild(typed);
    stage.appendChild(kicker);
    var title = make("div", "ctf-fb-title");
    var words = String(t("fb.title")).split(/\s+/);
    title.appendChild(titleWord(words[0] || "FIRST", "ctf-fb-w0"));
    title.appendChild(document.createTextNode(" "));
    title.appendChild(titleWord(words.slice(1).join(" ") || "BLOOD", "ctf-fb-w1", true));
    stage.appendChild(title);
    stage.appendChild(make("div", "ctf-fb-rule"));

    var name = String(e.account || "");
    var team = make("div", "ctf-fb-team", name);
    if (name.length > 28) team.setAttribute("data-long", "2");
    else if (name.length > 16) team.setAttribute("data-long", "1");
    stage.appendChild(team);
    stage.appendChild(make("div", "ctf-fb-line", t("fb.line")));
    var chal = make("div", "ctf-fb-chal");
    chal.appendChild(make("span", "ctf-fb-chal-name", String(e.challenge || "")));
    var chips = make("span", "ctf-fb-chips");
    if (e.category) chips.appendChild(chip("ctf-fb-chip-cat", String(e.category)));
    if (typeof e.value === "number") chips.appendChild(chip("ctf-fb-chip-pts", t("fb.points", { points: e.value })));
    chips.appendChild(chip("ctf-fb-chip-lane", t(e.bracket === "ai" ? "lane.ai" : "lane.classic")));
    chal.appendChild(chips);
    stage.appendChild(chal);
    screen.appendChild(stage);
    screen.appendChild(hud(e));
    document.body.appendChild(layer);
    // Impact is narrow; whatever stands in for it may not be. Fit the title: it is
    // an inline-block, so its width is its words', whatever their animation does.
    var room = stage.clientWidth * 0.92, wide = title.offsetWidth;
    if (wide > room) title.style.fontSize = (parseFloat(getComputedStyle(title).fontSize) * room / wide).toFixed(1) + "px";

    var timers = [];
    function at(ms, fn) { timers.push(setTimeout(function () { try { fn(); } catch (err) {} }, ms)); }
    var page = document.querySelector("main") || document.querySelector("body > .container");
    at(B0, function () { shake(stage, 10, 380); tear(layer, 8, 200); });
    at(B1, function () { shake(stage, 18, 520); shake(page, 12, 520); spray(screen, 46); tear(layer, 16, 280); });
    GLITCHES.forEach(function (ms) { at(ms, function () { tear(layer, 10, 220); }); });
    if (motionOk()) at(TEAM_AT, function () { decode(team, name, decodeMs(name)); });
    at(SHOW_MS - OUT_MS, function () { layer.classList.add("ctf-fb-out"); });
    at(SHOW_MS, endShow);

    showing = {
      layer: layer, timers: timers, done: done || function () {},
      stopRain: rain(layer.querySelector(".ctf-fb-rain")),
      onKey: function (ev) { if (ev.key === "Escape") endShow(); }
    };
    document.addEventListener("keydown", showing.onKey, true);
    Sound.play();
  }

  // ---- the banner (every other page) -----------------------------------------------
  function toast(e, done) {
    var box = document.getElementById("ctf-fb-toasts");
    if (!box) {
      box = make("div");
      box.id = "ctf-fb-toasts";
      box.setAttribute("aria-hidden", "true");
      document.body.appendChild(box);
    }
    var el = make("div", "ctf-fb-toast");
    el.setAttribute("data-lane", e.bracket === "ai" ? "ai" : "normal");
    el.appendChild(make("span", "ctf-fb-toast-tag", t("fb.title")));
    var text = make("span", "ctf-fb-toast-text");
    text.appendChild(make("b", null, String(e.account || "")));
    text.appendChild(document.createTextNode(" " + t("fb.line") + " "));
    text.appendChild(make("b", null, String(e.challenge || "")));
    if (typeof e.value === "number") text.appendChild(make("span", "ctf-fb-toast-pts", t("fb.points", { points: e.value })));
    el.appendChild(text);
    box.appendChild(el);
    setTimeout(function () { el.classList.add("ctf-fb-toast-out"); }, TOAST_MS - 450);
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
      if (done) done();
    }, TOAST_MS);
  }

  // The player's own solve moment (ai-mode.js, #ctf-win) gets the stamp.
  function stamp(e) {
    var layer = document.getElementById("ctf-win");
    var card = layer && layer.querySelector(".ctf-win-card");
    if (!card || card.querySelector(".ctf-fb-stamp")) return false;
    layer.classList.add("ctf-win-fb");
    var el = make("div", "ctf-fb-stamp");
    el.appendChild(make("strong", null, t("fb.title")));
    el.appendChild(make("span", null, t("fb.own")));
    card.appendChild(el);
    say(e);
    return true;
  }

  // For a screen reader: the same news, in words.
  function say(e) {
    var live = document.getElementById("ctf-fb-live");
    if (!live) {
      live = make("div");
      live.id = "ctf-fb-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      document.body.appendChild(live);
    }
    live.textContent = t("fb.live", { team: String(e.account || ""), challenge: String(e.challenge || "") });
  }

  // One at a time, in the order they happened.
  var queue = [], busy = false;
  function pump() {
    if (busy || !queue.length) return;
    busy = true;
    var e = queue.shift();
    say(e);
    (onBoard() ? show : toast)(e, function () {
      busy = false;
      setTimeout(pump, 450);
    });
  }
  function announce(e) { queue.push(e); pump(); }

  // ---- what this browser has announced ------------------------------------------------
  var memory = null; // the same list, for a browser without localStorage
  function readSeen() {
    try {
      var v = JSON.parse(localStorage.getItem(SEEN_KEY));
      if (v && typeof v === "object" && !Array.isArray(v)) return v;
    } catch (e) {}
    return memory;
  }
  function writeSeen(seen) {
    var now = Date.now(), keep = {};
    Object.keys(seen).forEach(function (k) {
      // an event stops being announced FRESH seconds after it happened, so this is long enough
      if (now - seen[k] < (FRESH + 120) * 1000) keep[k] = seen[k];
    });
    memory = keep;
    store(SEEN_KEY, JSON.stringify(keep));
  }
  function keyOf(e) { return e.id + "@" + e.ts; }

  // ---- the feed --------------------------------------------------------------------
  var ownSolve = null;  // the challenge id of this page's last correct flag
  var lastRev = null, refreshTimer = 0, refreshedAt = 0;

  // The standings changed: have the Scoreboard page fetch them again (ai-mode.js),
  // soon, but not on every solve of a busy minute.
  function refreshBoard() {
    if (!onBoard() || refreshTimer) return;
    var wait = Math.max(600, refreshedAt + REFRESH_GAP - Date.now());
    refreshTimer = setTimeout(function () {
      refreshTimer = 0;
      refreshedAt = Date.now();
      try { if (window.ctfAiModus && window.ctfAiModus.refreshBoard) window.ctfAiModus.refreshBoard(); } catch (e) {}
    }, wait);
  }

  function onFeed(data) {
    var events = Array.isArray(data.events) ? data.events : [];
    var fresh = events.filter(function (e) { return e && typeof e.age === "number" && e.age <= FRESH; });
    var seen = readSeen(), first = seen === null, now = Date.now(), news = [];
    seen = seen || {};
    fresh.forEach(function (e) {
      var k = keyOf(e);
      if (Object.prototype.hasOwnProperty.call(seen, k)) return;
      seen[k] = now;
      news.push(e);
    });
    writeSeen(seen);
    if (!first) {
      var me = myAccount();
      news.slice(-MAX_QUEUE).forEach(function (e) {
        // My own flag just now: the solve moment on screen says it.
        if (me !== null && e.account_id === me && e.challenge_id === ownSolve && stamp(e)) return;
        announce(e);
      });
    }
    if (lastRev !== null && data.rev !== lastRev) refreshBoard();
    lastRev = data.rev;
  }

  var timer = 0, stopped = false, inflight = false, again = false;
  function schedule(ms) {
    clearTimeout(timer);
    if (!stopped) timer = setTimeout(poll, ms);
  }
  function poll() {
    if (stopped || document.hidden) return; // a hidden tab waits for visibilitychange
    if (inflight) { again = true; return; }
    inflight = true;
    clearTimeout(timer);
    fetch(urlRoot() + "/first-blood/feed", {
      credentials: "same-origin", cache: "no-store",
      // as JSON, so a visitor who may not see the scores gets a 403, not the login page
      headers: { Accept: "application/json", "Content-Type": "application/json" }
    }).then(function (r) {
      // No plugin, or scores this visitor may not see: nothing to announce on this page.
      if (r.status === 404 || r.status === 403 || r.status === 401) { stopped = true; return null; }
      if (!r.ok) throw new Error("feed " + r.status);
      return r.json();
    }).then(function (body) {
      inflight = false;
      if (stopped) return;
      if (body && body.data) onFeed(body.data);
      if (again) { again = false; poll(); return; }
      schedule(onBoard() ? POLL_BOARD : POLL_PAGE);
    }).catch(function () {
      inflight = false;
      again = false;
      schedule(POLL_RETRY);
    });
  }

  // ---- the sound control (the Scoreboard page) -----------------------------------------
  var ICON_ON = '<svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/>' +
    '<path class="ctf-fb-wave" d="M16 8.5a5 5 0 0 1 0 7M18.6 6a8.5 8.5 0 0 1 0 12"/></svg>';
  var ICON_OFF = '<svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/>' +
    '<path class="ctf-fb-wave" d="M16.5 9.5l5 5M21.5 9.5l-5 5"/></svg>';

  function syncDock() {
    var dock = document.getElementById("ctf-fb-dock");
    if (!dock) return;
    var on = Sound.on();
    dock.setAttribute("data-sound", on ? "on" : "off");
    dock.setAttribute("data-armed", Sound.armed() ? "true" : "false");
    var button = dock.querySelector(".ctf-fb-dock-sound");
    button.setAttribute("aria-pressed", on ? "true" : "false");
    button.querySelector(".ctf-fb-dock-icon").innerHTML = on ? ICON_ON : ICON_OFF;
    bind(button.querySelector(".ctf-fb-dock-text"), on ? "fb.sound.on" : "fb.sound.off");
  }

  function buildDock() {
    if (!onBoard() || document.getElementById("ctf-fb-dock")) return;
    var host = document.querySelector(".jumbotron .container") || document.querySelector(".jumbotron");
    if (!host) return;
    var dock = make("div");
    dock.id = "ctf-fb-dock";
    dock.appendChild(bind(make("span", "ctf-fb-dock-label"), "fb.dock"));
    if (Sound.supported) {
      var sound = make("button", "ctf-fb-dock-sound");
      sound.type = "button";
      sound.appendChild(make("span", "ctf-fb-dock-icon"));
      sound.appendChild(make("span", "ctf-fb-dock-text"));
      bindAttr(sound, "title", "fb.sound.title");
      sound.addEventListener("click", function () { Sound.set(!Sound.on()); syncDock(); });
      dock.appendChild(sound);
    }
    var test = bind(make("button", "ctf-fb-dock-test"), "fb.test");
    test.type = "button";
    bindAttr(test, "title", "fb.test.title");
    test.addEventListener("click", function () { Sound.arm(); demo(); });
    dock.appendChild(test);
    // on, but the browser is still waiting for a click before it lets the page make sound
    dock.appendChild(bind(make("span", "ctf-fb-dock-hint"), "fb.sound.arm"));
    host.appendChild(dock);
    if (Sound.supported) syncDock();
  }

  // The show with made-up names, or the given ones: for trying the screen and the
  // volume before the event.
  function demo(team, challenge) {
    queue.length = 0;
    show({
      id: 0, ts: 0, age: 0, challenge_id: 0, account_id: 0, bracket: "normal", value: 100, category: "demo",
      account: team || init().teamName || t("fb.demo.team"),
      challenge: challenge || t("fb.demo.challenge")
    }, function () { busy = false; pump(); });
    busy = true;
  }

  // ---- start ------------------------------------------------------------------------
  function start() {
    if (onBoard()) {
      buildDock();
      Sound.changed(syncDock);
      // The sound was turned on here before: start it now if the browser allows
      // that without a click, else on the first click or key press.
      Sound.arm();
      var wake = function () { Sound.arm(); };
      document.addEventListener("pointerdown", wake, true);
      document.addEventListener("keydown", wake, true);
    }
    // ai-mode.head.js reports each flag answer. A correct one may be a first
    // blood of this player's own: ask right away, while the solve moment is up.
    document.addEventListener("ctf-attempt", function (ev) {
      var d = ev.detail || {};
      if (d.status !== "correct") return;
      ownSolve = d.id;
      setTimeout(poll, 150);
    });
    document.addEventListener("visibilitychange", function () { if (!document.hidden) poll(); });
    window.addEventListener("storage", function (ev) { if (ev.key === SOUND_KEY) syncDock(); });
    poll();
  }

  window.ctfFirstBlood = {
    demo: demo,
    // ctfFirstBlood.sound(true) turns the sound on from the console
    sound: function (on) { Sound.set(!!on); syncDock(); }
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
