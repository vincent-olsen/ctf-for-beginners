// VikeMerch — AI-modus edition.
//
// The storefront is the vikeMERCH shop from `viking` (same products, same
// pictures), in the AI-modus fire skin.
//
// The shop ships a staff "link preview" tool at /fetch?url=... that fetches a
// URL server-side and echoes the response. The admin console (which prints the
// flag) runs on an internal, loopback-only port that is never exposed outside
// the container.
package main

import (
	"embed"
	"fmt"
	"html/template"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

const (
	publicAddr   = "0.0.0.0:5000"   // the shop (exposed)
	internalAddr = "127.0.0.1:9000" // admin console (loopback only, NOT exposed)
)

func loadFlag() string {
	if v := os.Getenv("FLAG"); v != "" {
		return strings.TrimSpace(v)
	}
	if b, err := os.ReadFile("flag.txt"); err == nil {
		return strings.TrimSpace(string(b))
	}
	return "FLAG_NOT_SET"
}

var flag = loadFlag()

// --- internal admin console (loopback only) ---------------------------------

func internalServer() {
	mux := http.NewServeMux()
	mux.HandleFunc("/internal/flag", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "VikeMerch admin console (internal)\nflag: %s\n", flag)
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, "VikeMerch internal admin service. Try /internal/flag.")
	})
	log.Fatal(http.ListenAndServe(internalAddr, mux))
}

// --- catalogue (same products as the original shop) --------------------------

//go:embed assets/*.jpg
var assets embed.FS

type Cents int

func (c Cents) String() string { return fmt.Sprintf("$%d.%02d", int(c)/100, int(c)%100) }

type Listing struct {
	ID, Title, Description string
	Price                  Cents
	Image                  string
}

var listings = []Listing{
	{"299f2f88-2da2-4d1a-a7c0-da7431393f4a", "Viking Beanie", "Warm and cozy beanie with a Viking-inspired design.", 2500, "_694ffa14-0e1f-4477-a0ed-bd64b3997a57.jpg"},
	{"d30fc1e8-838d-4d25-b3ee-76007376cdef", "Sweater Vest", "Classic sweater vest perfect for layering in chilly weather.", 3500, "_c07fee49-8e5e-45e6-9144-ebac60e1ced3.jpg"},
	{"bf223350-c731-42f7-ba0d-e738b556581f", "Bottle Opener", "Sturdy stainless steel bottle opener with ergonomic handle.", 1000, "_780729f1-fc8c-4e90-930e-26acd2167fb6.jpg"},
	{"ea5e8447-8e48-482b-9f62-f6a7e77d68d1", "Viking Shield Wall Art", "Handcrafted wooden wall art featuring a Viking shield design.", 4500, "_4a3d1c6e-07ab-4d3c-a47e-51296f8206b1.jpg"},
	{"6e3b0a1b-f905-41c4-b74b-99cb80fa34bc", "Thor's Hammer Pendant", "Detailed stainless steel pendant shaped like Thor's hammer, Mjölnir.", 2800, "_e7e26434-cd4b-4350-bf69-7be88fdc51b6.jpg"},
	{"c1a5bc52-7db7-48b6-bda3-492c54b83207", "Viking Drinking Horn", "Authentic drinking horn with intricate carvings, perfect for mead or ale.", 3200, "_f426e77b-0ea7-4613-aaa5-5c4274f9d8f2.jpg"},
	{"8b6ef5e7-563a-4b92-a4dd-45f9da1ff32e", "Rune Stone Coasters", "Set of four coasters featuring Viking rune stone designs.", 1800, "_125d3722-b8b9-49ec-98dd-8a379475ba65.jpg"},
	{"72a6b066-2fa7-42de-b44a-fb0f81ab0518", "Viking Axe Keychain", "Miniature replica of a Viking battle axe, perfect for a keychain.", 1200, "_cae90c88-756e-4ab9-b429-ed9f325f906c.jpg"},
	{"5b7d8db1-d5b4-4b1f-971f-d7fc94e4357b", "Viking Rune T-shirt", "Soft cotton t-shirt featuring Viking rune symbols and their meanings.", 2900, "_adcef4f0-0de4-415f-b25d-91c03cea5e45.jpg"},
	{"4fdab11a-7d0a-40ac-8c7d-62026886cd15", "Viking Horned Helmet Mug", "Ceramic mug shaped like a Viking horned helmet, perfect for your favorite beverage.", 2400, "_f955e086-d781-4728-8b33-6a3ab81c1a9e.jpg"},
	{"7e25b441-bb90-4dc3-b1f8-38a59db79e70", "Viking Rune Journal", "Leather-bound journal with Viking rune inscriptions on the cover.", 3800, "_60af98f3-aa5a-4cb3-80a3-37ad1fa823ea.jpg"},
	{"91f7973e-6880-4dcb-bfc8-9f67e742b181", "Viking Ship Model Kit", "Build-your-own Viking longship model kit, complete with sails and oars.", 5000, "_3d45f00f-12fd-4a38-a7b6-fb38d8f421f7.jpg"},
}

// --- pages --------------------------------------------------------------------

// Layout and components mirror the original viking views (navbar, hero,
// listing grid, footer); the colours are the AI-modus palette shared with
// platform/theme/ai-mode.css and the other hosted AI challenges. The "top"
// template starts with their shared effects-level bootstrap (the level picked
// on the CTFd board, platform/theme/hosted-fx.css): a plain <script> with no
// template actions, which html/template passes through as it is (bar its
// comments, which it strips).
const pagesHTML = `
{{define "top"}}<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<script>
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
<title>vikeMERCH{{if .}} - {{.}}{{end}}</title>
<style>
  :root{--bg:#060403;--panel:#120a06;--panel2:#1a0e07;--line:#4a2412;--fg:#ffe9d6;--soft:#f2d2b6;--muted:#c79a7a;
    --amber:#ffc400;--orange:#ff7a00;--red:#ff2e00;--hot:#ff5a2a;--neon:#39ff14;--cyan:#00e5ff;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Courier New",monospace;
    --fire:linear-gradient(0deg,#ff2e00 0%,#ff7a00 38%,#ffc400 68%,#fff3b0 100%)}
  *{box-sizing:border-box}html{background:var(--bg);color-scheme:dark}
  body{margin:0;min-height:100vh;display:flex;flex-direction:column;color:var(--fg);background:transparent;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
  body>main{flex:1}
  a{color:var(--amber)}a:hover{color:#ffe27a;text-shadow:0 0 8px var(--orange)}
  a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid #fff;outline-offset:2px}
  p{margin:.5rem 0;color:var(--soft)}
  .fire{font-family:var(--mono);font-weight:700;background:var(--fire);background-size:100% 220%;
    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:var(--orange);
    filter:drop-shadow(0 0 12px rgba(255,90,0,.5));animation:fire 1.3s ease-in-out infinite alternate}
  .glitch{position:relative;display:inline-block}
  .glitch::before,.glitch::after{content:attr(data-text);position:absolute;left:0;top:0;width:100%;-webkit-text-fill-color:currentColor;background:none;clip-path:inset(0 0 100% 0);pointer-events:none}
  .glitch::before{color:var(--cyan);animation:glitch-a 3.1s steps(1) infinite}
  .glitch::after{color:var(--red);animation:glitch-b 3.1s steps(1) infinite}
  input,button{font:inherit;font-family:var(--mono);min-height:44px;border-radius:8px}
  input{padding:0 12px;background:#0a0604;color:var(--fg);border:1px solid var(--line);caret-color:var(--amber);min-width:0}
  input:focus{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(255,122,0,.3)}
  button{padding:0 18px;border:0;cursor:pointer;font-weight:700;letter-spacing:.06em;color:#1a0600;background:linear-gradient(90deg,#ff2e00,#ff7a00 55%,#ffc400);box-shadow:0 0 16px rgba(255,90,0,.45)}

  /* AI-modus strip */
  .bar{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem 1rem;padding:8px 16px;border-bottom:1px solid var(--line);
    background:#0b0604;font:.75rem var(--mono);letter-spacing:.14em;color:var(--muted)}
  .lane{padding:3px 9px;border-radius:6px;font-weight:700;color:#1a0600;background:linear-gradient(90deg,#ff2e00,#ff7a00 55%,#ffc400);box-shadow:0 0 14px rgba(255,90,0,.5)}
  .threat{color:var(--hot);font-weight:700}

  /* navbar (original: logo | search | My Cart) */
  .nav-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;padding:8px 16px;background:var(--panel);border-bottom:1px solid var(--line);box-shadow:0 6px 30px rgba(255,90,0,.08)}
  .logo{font-size:2rem;line-height:1.2;padding:0 4px;text-decoration:none;color:var(--fg);font-family:var(--mono);letter-spacing:.02em}
  .logo b{background:var(--fire);background-size:100% 220%;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;
    filter:drop-shadow(0 0 10px rgba(255,90,0,.55));animation:fire 1.3s ease-in-out infinite alternate}
  .logo:hover{text-shadow:none;color:var(--fg)}
  .search-bar{flex:1 1 240px;width:100%}
  .navlinks{display:flex;gap:16px;margin-left:auto}
  .navlink{color:var(--muted);text-decoration:none;font-family:var(--mono);font-size:.9rem;white-space:nowrap}
  .navlink.staff{color:var(--amber)}

  /* hero (original: grey band, title, text + hero.jpg) */
  .hero-message{padding:32px 16px;min-height:50svh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;
    border-bottom:1px solid var(--line);
    background:radial-gradient(ellipse 80% 70% at 50% 110%,rgba(255,60,0,.28),rgba(255,120,0,.08) 45%,transparent 70%),var(--panel)}
  .hero-message .title{font-size:clamp(1.5rem,4.5vw,2.4rem);line-height:1.2;text-align:center;margin:0 0 .5rem}
  .hero-message .content{display:flex;flex-wrap:wrap;align-items:center;gap:24px;width:min(1000px,100%)}
  .hero-message .content>div{flex:1 1 320px}
  .hero-message img{flex:0 1 380px;width:100%;max-width:380px;aspect-ratio:1;object-fit:cover;border-radius:10px;border:1px solid var(--line);
    box-shadow:0 0 40px rgba(255,90,0,.35);animation:ember 2.6s ease-in-out infinite alternate}

  /* staff tool */
  .staff-tool{width:min(1000px,calc(100% - 32px));margin:24px auto 0;padding:18px 20px;border:1px solid var(--line);border-radius:12px;background:var(--panel2);box-shadow:0 0 30px rgba(255,90,0,.10)}
  .staff-tool h2{margin:0 0 .3rem;font-size:1.2rem}
  .staff-tool form{display:flex;flex-wrap:wrap;gap:8px;margin:.6rem 0}
  .staff-tool input{flex:1 1 260px}
  .staff-tool .note{color:var(--muted);font-size:.9rem}
  .kicker{font:.72rem var(--mono);letter-spacing:.16em;color:var(--amber);text-transform:uppercase}

  /* listing grid (original: 256px grey cards) */
  .listing-grid{display:flex;flex-wrap:wrap;justify-content:center;max-width:1250px;margin:auto;padding:24px 16px;gap:16px}
  .listing-item{width:256px;max-width:100%;padding:16px;overflow:hidden;color:var(--fg);text-decoration:none;
    background:var(--panel);border:1px solid var(--line);border-radius:10px;transition:transform .15s,border-color .15s,box-shadow .15s}
  .listing-item:hover{color:var(--fg);text-shadow:none;transform:translateY(-3px);border-color:var(--orange);box-shadow:0 0 24px rgba(255,90,0,.35)}
  .productimage{display:block;width:100%;aspect-ratio:1;object-fit:cover;border-radius:6px;filter:saturate(1.1) sepia(.15)}
  .info{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:start;gap:4px 8px;margin-top:10px}
  .info .title{font-weight:700}
  .price{font-family:var(--mono);color:var(--amber)}

  /* product / search / small pages */
  .product-container{display:flex;flex-wrap:wrap;justify-content:center;max-width:1000px;margin:auto;padding:24px 16px;gap:24px}
  .product-container .productimage{flex:0 1 460px;max-width:460px;border:1px solid var(--line);border-radius:10px;box-shadow:0 0 36px rgba(255,90,0,.25)}
  .productinfo{flex:1 1 280px}
  .productinfo h1{font-size:clamp(1.5rem,4vw,2.1rem);line-height:1.2;margin:0 0 .6rem}
  .productinfo .price{font-size:1.3rem}
  .search-results{text-align:center;font-size:1.25em;color:var(--soft);padding:24px 16px 0}
  .center{max-width:720px;margin:auto;padding:48px 16px;text-align:center}
  .center h1{font-size:clamp(1.6rem,5vw,2.6rem);line-height:1.2;margin:0 0 .6rem}
  pre{font-family:var(--mono);color:var(--neon);background:#020201;border:1px solid var(--line);border-radius:8px;padding:12px;
    white-space:pre-wrap;word-break:break-word;text-align:left;text-shadow:0 0 6px rgba(57,255,20,.35)}
  .err{color:var(--hot)}

  /* footer (original: Copyright 2024 vikeCORP | Admin) */
  .footer-bar{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 12px;padding:16px;color:var(--muted);font-size:small;border-top:1px solid var(--line)}
  .footer-bar a{color:var(--muted)}
  .footer-bar .rule{font-family:var(--mono);letter-spacing:.08em}.footer-bar .rule b{color:var(--amber)}

  .fx-scanlines{position:fixed;inset:0;z-index:2;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,0) 0,rgba(0,0,0,0) 2px,rgba(0,0,0,.24) 3px,rgba(0,0,0,0) 4px)}
  @keyframes fire{from{background-position:0 0}to{background-position:0 100%}}
  @keyframes ember{from{box-shadow:0 0 28px rgba(255,60,0,.25)}to{box-shadow:0 0 54px rgba(255,140,0,.45)}}
  @keyframes glitch-a{0%,84%,100%{clip-path:inset(0 0 100% 0);transform:none}86%{clip-path:inset(12% 0 58% 0);transform:translate(-4px,-1px)}89%{clip-path:inset(62% 0 10% 0);transform:translate(3px,1px)}92%{clip-path:inset(34% 0 38% 0);transform:translate(-2px,0)}}
  @keyframes glitch-b{0%,85%,100%{clip-path:inset(0 0 100% 0);transform:none}87%{clip-path:inset(48% 0 22% 0);transform:translate(4px,1px)}90%{clip-path:inset(8% 0 70% 0);transform:translate(-3px,-1px)}93%{clip-path:inset(70% 0 4% 0);transform:translate(2px,0)}}
  @media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style></head>
<body>
<div class="fx-scanlines" aria-hidden="true"></div>
<div class="bar"><span class="lane">AI-MODUS</span><span>ai-web · viking-ai</span><span class="threat">THREAT 4/5</span></div>
<form action="/search" role="search">
  <header class="nav-bar">
    <a class="logo" href="/">vike<b>MERCH</b></a>
    <input name="q" class="search-bar" placeholder="Search" aria-label="Search">
    <nav class="navlinks"><a class="navlink staff" href="/fetch">Link Preview</a><a class="navlink" href="/cart">My Cart</a></nav>
  </header>
</form>
<main>
{{end}}

{{define "bottom"}}
</main>
<footer class="footer-bar">
  <span>Copyright 2024 vikeCORP | <a href="/admin">Admin</a></span>
  <span class="rule"><b>AI expected.</b> Bring your assistant.</span>
</footer>
<!-- All images on this website are generated by Bing Copilot -->
</body></html>
{{end}}

{{define "listings"}}
<div class="listing-grid">
  {{range .}}<a class="listing-item" href="/product?id={{.ID}}">
    <img class="productimage" src="/assets?id={{.Image}}" alt="{{.Title}}" loading="lazy">
    <div class="info"><div class="title">{{.Title}}</div><div class="price">{{.Price}}</div></div>
  </a>{{end}}
</div>
{{end}}

{{define "preview-form"}}
<form action="/fetch" method="get">
  <input name="url" value="{{.}}" placeholder="https://example.com/product.jpg" aria-label="URL to preview">
  <button>Preview</button>
</form>
{{end}}

{{define "index"}}{{template "top" ""}}
<div class="hero-message">
  <h1 class="title fire glitch" data-text="Unleash Your Inner Viking with vikeMERCH!">Unleash Your Inner Viking with vikeMERCH!</h1>
  <div class="content">
    <div>
      <p>Welcome to vikeMERCH, your ultimate destination for all things Viking! Dive into a world of
      fierce warriors, epic sagas, and timeless Norse mythology with our premium selection of
      Viking-inspired merchandise.</p>
      <p>From intricately crafted jewelry adorned with ancient symbols to rugged apparel that echoes
      the spirit of exploration and adventure, vikeMERCH offers a diverse range of products that
      celebrate the legendary Viking heritage.</p>
      <p>We rebuilt the shop with sturdier locks after last season's little incident. The famous
      sweater vest is back in stock.</p>
      <p>Gear up like a true warrior and conquer the day with vikeMERCH – Where Legends Come to Life!</p>
    </div>
    <img src="/assets?id=hero.jpg" alt="A Viking warrior">
  </div>
</div>
<section class="staff-tool">
  <div class="kicker">Staff only</div>
  <h2 class="fire">Link Preview</h2>
  <p>Marketing uses this to check a product image or supplier URL before we publish it.
  It fetches the URL on the server and shows you what came back.</p>
  {{template "preview-form" ""}}
  <p class="note">The admin console runs on the internal network only, so you'll never reach it from out here. (Right?)</p>
</section>
{{template "listings" .}}
{{template "bottom"}}{{end}}

{{define "search"}}{{template "top" .Query}}
<div class="search-results">{{if .Listings}}Search results for: <b>{{.Query}}</b>{{else}}No results found!{{end}}</div>
{{template "listings" .Listings}}
{{template "bottom"}}{{end}}

{{define "product"}}{{template "top" .Title}}
<div class="product-container">
  <img class="productimage" src="/assets?id={{.Image}}" alt="{{.Title}}">
  <div class="productinfo">
    <h1 class="fire">{{.Title}}</h1>
    <p>{{.Description}}</p>
    <p class="price">{{.Price}}</p>
    <p><a href="/cart"><button type="button" tabindex="-1">Add to cart</button></a></p>
  </div>
</div>
{{template "bottom"}}{{end}}

{{define "message"}}{{template "top" .Title}}
<div class="center">
  <h1 class="fire glitch" data-text="{{.Title}}">{{.Title}}</h1>
  <p>{{.Text}}</p>
  <p><a href="/">Back to the shop ⮌</a></p>
</div>
{{template "bottom"}}{{end}}

{{define "preview"}}{{template "top" "Link Preview"}}
<section class="staff-tool">
  <div class="kicker">Staff only</div>
  <h2 class="fire">Link Preview</h2>
  {{template "preview-form" .URL}}
  {{if .Error}}<p class="err">{{.Error}}</p>{{end}}
  {{if .URL}}{{if not .Error}}<p>Preview of <code>{{.URL}}</code> (HTTP {{.Status}}):</p><pre>{{.Body}}</pre>{{end}}{{end}}
</section>
{{template "bottom"}}{{end}}
`

var pages = template.Must(template.New("pages").Parse(pagesHTML))

func render(w http.ResponseWriter, status int, name string, data any) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	if err := pages.ExecuteTemplate(w, name, data); err != nil {
		log.Printf("render %s: %v", name, err)
	}
}

type message struct{ Title, Text string }

func home(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		render(w, http.StatusNotFound, "message", message{"404", "That page sailed off without you."})
		return
	}
	render(w, http.StatusOK, "index", listings)
}

func search(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query().Get("q")
	needle := strings.ToLower(q)
	found := []Listing{}
	for _, l := range listings {
		if strings.Contains(strings.ToLower(l.Title), needle) || strings.Contains(strings.ToLower(l.Description), needle) {
			found = append(found, l)
		}
	}
	render(w, http.StatusOK, "search", map[string]any{"Query": q, "Listings": found})
}

func product(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	for _, l := range listings {
		if l.ID == id {
			render(w, http.StatusOK, "product", l)
			return
		}
	}
	render(w, http.StatusNotFound, "message", message{"404", "No such product."})
}

// asset serves the product pictures embedded in the binary.
func asset(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	if strings.ContainsAny(id, `/\`) || !strings.HasSuffix(id, ".jpg") {
		http.NotFound(w, r)
		return
	}
	b, err := assets.ReadFile("assets/" + id)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "public, max-age=3600")
	w.Write(b)
}

func cart(w http.ResponseWriter, r *http.Request) {
	render(w, http.StatusOK, "message", message{"🚧 Under Construction 🚧", "This page isn't ready yet!"})
}

func admin(w http.ResponseWriter, r *http.Request) {
	render(w, http.StatusOK, "message", message{"Admin Login 🤫",
		"After last season's incident the admin console moved to the internal network. It is not reachable from the internet."})
}

// fetch is the staff link preview: it GETs a URL server-side and echoes the
// response, refusing internal hosts. Browsers get the result in the shop's
// page; everything else (curl, scripts) gets plain text.
func fetch(w http.ResponseWriter, r *http.Request) {
	html := strings.Contains(r.Header.Get("Accept"), "text/html")
	target := r.URL.Query().Get("url")
	fail := func(status int, msg string) {
		if html {
			render(w, status, "preview", map[string]any{"URL": target, "Error": msg})
			return
		}
		http.Error(w, msg, status)
	}
	if target == "" {
		if html {
			render(w, http.StatusOK, "preview", map[string]any{"URL": ""})
			return
		}
		fail(http.StatusBadRequest, "pass ?url=")
		return
	}
	u, err := url.Parse(target)
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") {
		fail(http.StatusBadRequest, "only http/https URLs are allowed")
		return
	}
	host := strings.ToLower(u.Hostname())
	// The loopback filter, wised up once. The first version was a pure string
	// blocklist and got walked straight past with [::ffff:127.0.0.1], so it now
	// does two things: the string blocklist below, AND it parses the host and
	// rejects anything that resolves to loopback / 0.0.0.0 *when it is written in
	// compressed IPv6 form* (i.e. contains "::"). That second check catches every
	// compact IPv4-mapped spelling at once - ::1, ::ffff:127.0.0.1, ::ffff:7f00:1,
	// ::ffff:7f00:0001 and the rest - without having to list each one.
	//
	// Deliberately STILL bypassable: it only normalises the compressed forms. A
	// fully-expanded, eight-group IPv4-mapped literal - [0:0:0:0:0:ffff:7f00:1] -
	// is the exact same 127.0.0.1, but it has no "::", so it is never parsed-and-
	// checked and sails straight through to the internal console. The real fix is
	// to parse EVERY form (expanded included) and reject the whole loopback range,
	// and to re-check after any redirect.
	for _, blocked := range []string{
		"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]",
		"::ffff:127.0.0.1", "::ffff:7f00:1",
		// written-out integer spellings, for completeness - Go's dialer won't
		// resolve these anyway, but a curl-minded solver reaches for them first:
		"2130706433", "0x7f000001", "017700000001", "0177.0.0.1", "127.1",
	} {
		if host == blocked {
			fail(http.StatusForbidden, "refusing to fetch an internal host")
			return
		}
	}
	if ip := net.ParseIP(host); ip != nil && strings.Contains(host, "::") &&
		(ip.IsLoopback() || ip.IsUnspecified()) {
		fail(http.StatusForbidden, "refusing to fetch an internal host")
		return
	}
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(u.String())
	if err != nil {
		fail(http.StatusBadGateway, "fetch failed: "+err.Error())
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if html {
		render(w, http.StatusOK, "preview", map[string]any{"URL": target, "Status": resp.StatusCode, "Body": string(body)})
		return
	}
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	fmt.Fprintf(w, "Preview of %s (HTTP %d):\n\n%s", target, resp.StatusCode, body)
}

func main() {
	go internalServer()
	mux := http.NewServeMux()
	mux.HandleFunc("/", home)
	mux.HandleFunc("/search", search)
	mux.HandleFunc("/product", product)
	mux.HandleFunc("/assets", asset)
	mux.HandleFunc("/cart", cart)
	mux.HandleFunc("/admin", admin)
	mux.HandleFunc("/fetch", fetch)
	log.Printf("VikeMerch listening on %s (internal console on %s)", publicAddr, internalAddr)
	log.Fatal(http.ListenAndServe(publicAddr, mux))
}
