/* =========================================================================
   LANGUAGE  -  Norwegian and English, switched with NO | EN in the navbar
   Linked from CTFd's theme_header by ctf.sh, after i18n.strings.js (the words)
   and before ai-mode.head.js; see docs/language.md.

   The language is the one this browser picked (localStorage "ctf-lang"), else
   the event's default (ctf.sh up --lang, which ctfd_admin.py puts in
   html[data-ctf-lang-default]), else CTF_I18N.defaultLanguage. It goes on
   <html> before the page paints: data-ctf-lang="no" and lang="nb". With it:
     - the theme's own text: ctfI18n.t(key), and elements bound to a key with
       ctfI18n.bind() (data-i18n), which a switch rewrites in place;
     - the stylesheets' text: a --ctf-t-<name> variable per "css." string;
     - CTFd's own text: CTFd renders English (ctfd_admin.py pins its
       default_locale), and a text on the page that is exactly one of
       CTF_I18N.ctfd, or matches ctfdPatterns, is replaced as the page loads and
       whenever CTFd draws more. Challenge content, names people chose and pages
       an organiser wrote are left alone. Switching back puts the English back;
     - bilingual content (challenge descriptions, hints, pages): a block per
       language, <div class="ctf-lang" lang="no">, and ai-mode.css shows the one
       in the page's language.
   A switch takes effect at once, with no reload, in every open tab, and is
   announced with a "ctf-lang" event on document ({detail: {lang}}).
   ========================================================================= */
(function () {
  "use strict";

  var I = window.CTF_I18N || {};
  var LANGS = I.languages && I.languages.length ? I.languages
    : [{ code: "en", label: "EN", name: "English", html: "en" }];
  var SOURCE = "en"; // the language CTFd renders in, and the fallback for a string
  var KEY = "ctf-lang";
  var root = document.documentElement;

  function info(code) {
    for (var i = 0; i < LANGS.length; i++) if (LANGS[i].code === code) return LANGS[i];
    return null;
  }
  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function store(code) {
    try { localStorage.setItem(KEY, code); } catch (e) {}
  }
  function defaultLang() {
    var c = root.getAttribute("data-ctf-lang-default");
    if (info(c)) return c;
    return info(I.defaultLanguage) ? I.defaultLanguage : LANGS[0].code;
  }

  var lang = info(stored()) ? stored() : defaultLang();

  // ---- the theme's strings -----------------------------------------------------
  function pick(entry) {
    if (entry == null || typeof entry !== "object" || Array.isArray(entry)) return entry;
    if (entry[lang] != null) return entry[lang];
    return entry[SOURCE] != null ? entry[SOURCE] : entry[LANGS[0].code];
  }
  function fill(text, vars) {
    return String(text).replace(/\{(\w+)\}/g, function (m, k) {
      return vars && vars[k] != null ? String(vars[k]) : m;
    });
  }
  // t("key", {name: ...}): the text in the current language (a list for a list).
  function t(key, vars) {
    var v = pick((I.strings || {})[key]);
    if (v == null) return key;
    if (Array.isArray(v)) return v.map(function (s) { return fill(s, vars); });
    return fill(v, vars);
  }

  function mark() {
    root.setAttribute("data-ctf-lang", lang);
    root.setAttribute("lang", info(lang).html || lang);
  }

  // "css.try-again" -> --ctf-t-try-again; one with {n} is split around it into
  // --ctf-t-<name>-a and -b, for content: var(-a) attr(data-ctf-fails) var(-b).
  var cssStyle = null;
  function quote(s) {
    return '"' + String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\a ") + '"';
  }
  function cssVars() {
    var out = [];
    Object.keys(I.strings || {}).forEach(function (key) {
      if (key.indexOf("css.") !== 0) return;
      var name = "--ctf-t-" + key.slice(4);
      var parts = String(pick(I.strings[key]) || "").split("{n}");
      if (parts.length > 1) {
        out.push(name + "-a:" + quote(parts[0]), name + "-b:" + quote(parts.slice(1).join("")));
      } else {
        out.push(name + ":" + quote(parts[0]));
      }
    });
    if (!cssStyle) {
      cssStyle = document.createElement("style");
      cssStyle.id = "ctf-i18n-css";
      (document.head || root).appendChild(cssStyle);
    }
    cssStyle.textContent = ":root{" + out.join(";") + "}";
  }

  // ---- elements bound to a key ------------------------------------------------------
  // data-i18n="key" (the text), data-i18n-title / -aria-label / -placeholder
  // (those attributes), data-i18n-vars='{"n": 3}' (the {names} in them).
  var BOUND = "[data-i18n],[data-i18n-title],[data-i18n-aria-label],[data-i18n-placeholder]";
  var BOUND_ATTRS = ["title", "aria-label", "placeholder"];

  function varsOf(el) {
    try { return JSON.parse(el.getAttribute("data-i18n-vars") || "null"); } catch (e) { return null; }
  }
  function render(el) {
    var vars = varsOf(el), key = el.getAttribute("data-i18n");
    if (key) {
      var text = t(key, vars);
      if (el.textContent !== text) el.textContent = text;
    }
    for (var i = 0; i < BOUND_ATTRS.length; i++) {
      var k = el.getAttribute("data-i18n-" + BOUND_ATTRS[i]);
      if (!k) continue;
      var val = t(k, vars);
      if (el.getAttribute(BOUND_ATTRS[i]) !== val) el.setAttribute(BOUND_ATTRS[i], val);
    }
  }
  function apply(scope) {
    scope = scope || document;
    if (scope.nodeType === 1 && scope.matches(BOUND)) render(scope);
    var els = scope.querySelectorAll(BOUND);
    for (var i = 0; i < els.length; i++) render(els[i]);
  }
  function setVars(el, vars) {
    var s = vars ? JSON.stringify(vars) : null;
    if (s && el.getAttribute("data-i18n-vars") !== s) el.setAttribute("data-i18n-vars", s);
    else if (!s && el.hasAttribute("data-i18n-vars")) el.removeAttribute("data-i18n-vars");
  }
  // bind(el, key, vars): el's text is t(key, vars), now and after a switch.
  // Only for an element with nothing else in it. Unchanged values aren't
  // written again, so it is safe to call from a MutationObserver.
  function bind(el, key, vars) {
    if (el.getAttribute("data-i18n") !== key) el.setAttribute("data-i18n", key);
    setVars(el, vars);
    render(el);
    return el;
  }
  // bindAttr(el, "title", key, vars): the same for an attribute.
  function bindAttr(el, attr, key, vars) {
    if (el.getAttribute("data-i18n-" + attr) !== key) el.setAttribute("data-i18n-" + attr, key);
    if (vars !== undefined) setVars(el, vars);
    render(el);
    return el;
  }

  // ---- CTFd's own text ------------------------------------------------------------
  var phrases = {}, patterns = [];
  function norm(s) { return String(s).replace(/\s+/g, " ").trim(); }
  function buildPhrases() {
    phrases = {};
    patterns = [];
    if (lang === SOURCE) return;
    (I.ctfd || []).forEach(function (p) {
      if (p && p[SOURCE] && p[lang] != null) phrases[norm(p[SOURCE])] = p[lang];
    });
    (I.ctfdPatterns || []).forEach(function (p) {
      if (p && p[SOURCE] instanceof RegExp && p[lang] != null) patterns.push(p);
    });
  }
  function lookup(text) {
    if (lang === SOURCE) return null;
    var key = norm(text);
    if (!key) return null;
    if (Object.prototype.hasOwnProperty.call(phrases, key)) return phrases[key];
    for (var i = 0; i < patterns.length; i++) {
      if (patterns[i][SOURCE].test(key)) return key.replace(patterns[i][SOURCE], patterns[i][lang]);
    }
    return null;
  }

  // Never translated: content (challenge descriptions, names, hints, code), names
  // and affiliations people chose (an affiliation "Yes" stays "Yes"), notices an
  // organiser wrote (a notification "Correct" stays as written), the theme's own
  // layers (bound to keys instead), and pages an organiser wrote (selfExcluded).
  var SKIP = [
    "script", "style", "textarea", "code", "pre", "kbd", "samp", "svg", "[contenteditable]",
    ".ctf-lang", "[data-i18n]", "[data-ctf-no-i18n]",
    ".challenge-desc", ".challenge-name", ".challenge-inner p", ".category-header", ".challenge-tag",
    ".challenge-attribution", ".challenge-connection-info", ".challenge-files",
    ".challenge-hints details > div", ".challenge-solution-content",
    ".navbar-brand", ".badge", "#team-id", "#user-id",
    ".table td", // table data: team/user names and brackets in the lists and scoreboard,
                 // and challenge names, categories and award names in the solve/award tables
    "a[href*='/challenges#']", // a solved challenge's name, linked from an account page
    "#team-captain-form option", // teammates' names in the captain dropdown
    "td.d-md-table-cell", // the Users and Teams lists: affiliation, country
    ".card-body > .card-title", ".card-body > .blockquote", // the Notifications page
    ".toast-header > strong", ".toast-body", ".modal-title[x-text]", ".modal-body > p[x-html]", // a notification as it arrives
    "#ai-lane", "#ctf-lang-switch", "#ai-lane-banner", "#ai-chooser", "#ai-boot", "#ai-flicker-msg",
    "#ai-fx-dock", "#ai-slop-chat", "#ai-slop-toasts", "#ai-slop-ticker", "#ai-retro-marq", "#ai-retro-foot",
    "#ai-retro-alert", ".ai-slop-sum", ".ai-slop-actions", ".ai-slop-eli5", ".ai-slop-foot",
    "#ctf-win", "#pv-boot", "#pv-win", "#pv-countdown", "#ctf-fb", "#ctf-fb-toasts", "#ctf-fb-live"
  ].join(",");
  var ACCOUNT_LINK = /\/(?:users|teams)\/\d+\/?(?:[?#].*)?$/; // a player's or team's name
  // A page from Admin -> Pages is the first thing in <main>, where CTFd's own
  // pages start with their title bar; only CTFd's error pages also do, and they
  // have this inside.
  var ERROR_PAGE = ":scope > .row > .col-md-12 > .pt-5";

  // A public account page (/users/<id>, /teams/<id>) shows the account's own name
  // in its one <h1>; the other headings there (Awards, Solves) are <h3>.
  var PUBLIC_ACCOUNT = /^\/(?:users|teams)\/\d+(?:[/?#]|$)/;
  function selfExcluded(el) {
    if (el.matches(SKIP)) return true;
    if (el.tagName === "A" && ACCOUNT_LINK.test(el.getAttribute("href") || "")) return true;
    if (el.tagName === "H1" && PUBLIC_ACCOUNT.test(location.pathname)) return true;
    return el.matches("main > .container:first-child") && !el.querySelector(ERROR_PAGE);
  }
  function excluded(el) {
    if (!el) return true;
    for (var e = el; e && e !== root; e = e.parentElement) if (selfExcluded(e)) return true;
    return false;
  }

  // Each translated text node and attribute keeps its English, so a switch can
  // put it back, and a text CTFd changes later is taken as new English.
  var texts = new WeakMap(); // Text -> {src, out}
  var attrs = new WeakMap(); // Element -> {name: {src, out}}
  var ATTRS = ["title", "placeholder", "aria-label", "data-bs-original-title", "data-bs-title", "value"];

  function translateText(node) {
    var rec = texts.get(node), cur = node.data;
    var src = rec && cur === rec.out ? rec.src : cur;
    var out = lookup(src);
    if (out == null) {
      if (rec) {
        texts.delete(node);
        if (cur !== src) node.data = src;
      }
      return;
    }
    var space = /^(\s*)[\s\S]*?(\s*)$/.exec(src);
    out = space[1] + out + space[2];
    texts.set(node, { src: src, out: out });
    if (cur !== out) node.data = out;
  }

  function translateAttr(el, name) {
    // value is a label only on an input button (a form's Submit)
    if (name === "value" && !(el.tagName === "INPUT" && /^(submit|button|reset)$/i.test(el.type))) return;
    var cur = el.getAttribute(name), recs = attrs.get(el), rec = recs && recs[name];
    if (cur == null) {
      if (rec) delete recs[name];
      return;
    }
    var src = rec && cur === rec.out ? rec.src : cur;
    var out = lookup(src);
    if (out == null) {
      if (rec) {
        delete recs[name];
        if (cur !== src) el.setAttribute(name, src);
      }
      return;
    }
    if (!recs) attrs.set(el, (recs = {}));
    recs[name] = { src: src, out: out };
    if (cur !== out) el.setAttribute(name, out);
  }

  function translateEl(el) {
    for (var i = 0; i < ATTRS.length; i++) if (el.hasAttribute(ATTRS[i])) translateAttr(el, ATTRS[i]);
  }

  function walk(node) {
    if (!node || !node.isConnected) return;
    if (node.nodeType === 3) {
      if (!excluded(node.parentElement)) translateText(node);
      return;
    }
    if (node.nodeType !== 1 || excluded(node)) return;
    translateEl(node);
    var tw = document.createTreeWalker(node, 5 /* elements and text */, {
      acceptNode: function (n) { return n.nodeType === 1 && selfExcluded(n) ? 2 /* reject */ : 1; }
    });
    for (var n = tw.nextNode(); n; n = tw.nextNode()) {
      if (n.nodeType === 3) translateText(n);
      else translateEl(n);
    }
  }

  // Synchronous, before the next paint: the parser's nodes, CTFd's Alpine
  // renders and server answers (a flag's "Correct") never show in English first.
  function onMutations(records) {
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      if (r.type === "childList") {
        for (var j = 0; j < r.addedNodes.length; j++) walk(r.addedNodes[j]);
      } else if (r.type === "characterData") {
        if (!excluded(r.target.parentElement)) translateText(r.target);
      } else if (!excluded(r.target)) {
        translateAttr(r.target, r.attributeName);
      }
    }
  }

  // The text of el with CTFd's English in place of any translation, for code
  // that reads what CTFd wrote ("1st place", "300 points").
  function sourceText(el) {
    if (!el) return "";
    var out = "", tw = document.createTreeWalker(el, 4 /* text */);
    for (var n = tw.nextNode(); n; n = tw.nextNode()) {
      var rec = texts.get(n);
      out += rec && n.data === rec.out ? rec.src : n.data;
    }
    return out;
  }

  // ---- CTFd's own dialogs ------------------------------------------------------------
  // Unlocking a hint or a solution asks with confirm() and answers an error with
  // alert(), out of reach of the page's text; CTFd lets a theme replace both.
  function patchDialogs() {
    var c = window.CTFd && window.CTFd._functions && window.CTFd._functions.challenge;
    if (!c || c.ctfI18n) return;
    c.ctfI18n = true;
    c.displayUnlock = c.displayHintUnlock = function () { return confirm(t("unlock.hint")); };
    c.displaySolutionUnlock = function () { return confirm(t("unlock.solution")); };
    c.displayUnlockError = function (response) {
      var errors = (response && response.errors) || {};
      alert(Object.keys(errors).map(function (k) {
        var msg = String(errors[k]);
        var out = lookup(msg);
        return out == null ? msg : out;
      }).join("\n"));
    };
  }

  // CTFd renders its pages in a player's own language (a "language" cookie from
  // its Language menu, which the theme hides) before default_locale, and the
  // table above only knows its English. So the cookie goes, on every path it may
  // have been set for, and a page CTFd rendered in another language is loaded
  // again, once. (A player's saved Language is cleared by ctfd_admin.py.)
  function dropLanguageCookie() {
    var m = /(?:^|;\s*)language=([^;]*)/.exec(document.cookie);
    if (!m) return;
    var parts = location.pathname.split("/"), paths = ["/"];
    for (var i = 2; i <= parts.length; i++) paths.push(parts.slice(0, i).join("/") || "/");
    paths.forEach(function (path) {
      document.cookie = "language=; Max-Age=0; path=" + path + "; SameSite=Lax";
      document.cookie = "language=; Max-Age=0; path=" + path + "/; SameSite=Lax";
    });
    var other = m[1] && m[1] !== SOURCE;
    try {
      if (other && !sessionStorage.getItem("ctf-lang-reloaded")) {
        sessionStorage.setItem("ctf-lang-reloaded", "1");
        location.reload();
      }
    } catch (e) {}
  }

  // ---- the switch -------------------------------------------------------------------
  // Small on purpose (the lane control is the loud one): NO | EN at the far end
  // of the navbar, after the light/dark switch. A radio group, like the lanes.
  function switchButtons() {
    var group = document.getElementById("ctf-lang-switch");
    return group ? group.querySelectorAll("button") : [];
  }
  function syncSwitch() {
    var buttons = switchButtons();
    for (var i = 0; i < buttons.length; i++) {
      var on = buttons[i].getAttribute("data-lang") === lang;
      buttons[i].setAttribute("aria-checked", on ? "true" : "false");
      buttons[i].tabIndex = on ? 0 : -1;
    }
  }
  function buildSwitch() {
    if (LANGS.length < 2 || document.getElementById("ctf-lang-switch")) return;
    var nav = document.querySelector("nav.navbar");
    if (!nav) return;
    var li = document.createElement("li");
    li.className = "nav-item ctf-lang-item";
    var group = document.createElement("div");
    group.id = "ctf-lang-switch";
    group.className = "ctf-lang-switch";
    group.setAttribute("role", "radiogroup");
    bindAttr(group, "aria-label", "lang.switch");
    LANGS.forEach(function (l) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = l.label || l.code.toUpperCase();
      b.title = l.name || l.code;
      b.setAttribute("role", "radio");
      b.setAttribute("data-lang", l.code);
      b.setAttribute("lang", l.html || l.code);
      b.addEventListener("click", function () { set(l.code); });
      group.appendChild(b);
    });
    group.addEventListener("keydown", function (e) {
      var step = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 }[e.key];
      if (!step) return;
      e.preventDefault();
      var i = LANGS.indexOf(info(lang));
      set(LANGS[(i + step + LANGS.length) % LANGS.length].code);
      var buttons = switchButtons();
      for (var k = 0; k < buttons.length; k++) if (buttons[k].getAttribute("aria-checked") === "true") buttons[k].focus();
    });
    li.appendChild(group);
    var themeSwitch = nav.querySelector(".theme-switch");
    var after = themeSwitch ? themeSwitch.closest("li") : null;
    if (after && after.parentNode) {
      after.parentNode.insertBefore(li, after.nextSibling);
    } else {
      var lists = nav.querySelectorAll("ul.navbar-nav");
      (lists.length ? lists[lists.length - 1] : nav).appendChild(li);
    }
    syncSwitch();
  }

  // set(code): switch this page (and, through localStorage, every other tab).
  // follow: only follow what another tab stored, without storing it again.
  function set(code, follow) {
    if (!info(code)) return;
    if (!follow) store(code);
    if (code === lang) { syncSwitch(); return; }
    lang = code;
    mark();
    buildPhrases();
    cssVars();
    apply(document);
    walk(document.documentElement);
    syncSwitch();
    try { document.dispatchEvent(new CustomEvent("ctf-lang", { detail: { lang: lang } })); } catch (e) {}
  }

  // ---- start ------------------------------------------------------------------------
  window.ctfI18n = {
    lang: function () { return lang; },
    languages: LANGS,
    t: t,
    set: set,
    bind: bind,
    bindAttr: bindAttr,
    apply: apply,
    sourceText: sourceText
  };

  try { dropLanguageCookie(); } catch (e) {}
  try {
    mark();
    buildPhrases();
    cssVars();
    walk(root);
    new MutationObserver(onMutations).observe(root, {
      childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS
    });
  } catch (e) {}

  function ready() {
    try {
      walk(document.body);
      apply(document);
      buildSwitch();
      patchDialogs();
    } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready);
  else ready();
  window.addEventListener("load", function () { try { patchDialogs(); } catch (e) {} });

  // Another tab switched, or this page came back from the back/forward cache.
  window.addEventListener("storage", function (e) {
    if (e.key === KEY && info(e.newValue)) set(e.newValue, true);
  });
  window.addEventListener("pageshow", function (e) {
    var s = stored();
    if (e.persisted && info(s)) set(s, true);
  });
})();
