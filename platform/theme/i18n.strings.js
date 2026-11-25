/* =========================================================================
   EVERY TEXT PLAYERS SEE, IN EACH LANGUAGE  -  edit the words here
   Linked from CTFd's theme_header by ctf.sh (see platform/theme/README.md and
   docs/language.md); i18n.js does the work.

   - languages: the switch in the navbar shows them in this order. `code` is
     what ctf.sh --lang and metadata.yml (message_no, hints_no) use, `html` the
     page's lang attribute. The default is ctf.sh --lang (default "en").
   - strings: the theme's own text, by key. A key without the current language
     falls back to `en`. {name} is filled in by the code. A key that starts with
     "css." is also a CSS variable (--ctf-t-<rest>) for the stylesheets'
     `content:`; there {n} becomes the wrong-flag count.
   - ctfd: CTFd's own English (its pages, forms and server messages), as CTFd
     renders it, and what to show instead. Whole texts only: a text on the page
     is replaced when it is exactly `en` (spaces and line breaks don't count).
   - ctfdPatterns: the same for texts with a number or a name in them; `en` is
     a regular expression, $1 its first group.

   Challenge descriptions and hints are not here: they come from each
   challenge's metadata.yml (message / message_no, hints / hints_no).
   ========================================================================= */
window.CTF_I18N = {
  languages: [
    { code: "no", label: "NO", name: "Norsk", html: "nb" },
    { code: "en", label: "EN", name: "English", html: "en" }
  ],
  defaultLanguage: "en",

  strings: {
    // ---- the language switch ---------------------------------------------
    "lang.switch": { no: "Språk / Language", en: "Language / Språk" },

    // ---- CTFd's own dialogs (confirm/alert, which the page text can't reach) --
    "unlock.hint": {
      no: "Er du sikker på at du vil låse opp dette hintet?",
      en: "Are you sure you'd like to unlock this hint?"
    },
    "unlock.solution": {
      no: "Er du sikker på at du vil låse opp løsningen?",
      en: "Are you sure you'd like to unlock this solution?"
    },

    // ---- the lane control (navbar) ----------------------------------------
    "lane.group": { no: "Bane", en: "Lane" },
    "lane.classic": { no: "Klassisk", en: "Classic" },
    "lane.ai": { no: "AI-MODUS", en: "AI-MODUS" },
    "lane.classic.title": {
      no: "Klassisk bane: de vanlige oppgavene. Ingen AI, bare Google, dokumentasjon og ditt eget hode.",
      en: "Classic lane: the normal challenges. No AI, just Google, docs and your own head."
    },
    "lane.ai.title": {
      no: "AI-modus: mye vanskeligere varianter av de samme ideene. Her forventes det at du bruker AI.",
      en: "AI-modus lane: much harder takes on the same ideas. Using AI is expected."
    },

    // ---- the lane banner on the Challenges page ---------------------------
    "banner.classic.rule": { no: "Klassisk bane: ingen AI.", en: "Classic lane: no AI." },
    "banner.classic.text": {
      no: " Google, dokumentasjon og ditt eget hode. Æresprinsippet gjelder.",
      en: " Google, docs and your own head. Honour system."
    },
    // AI-modus: the line above the title, and beside it how much of the
    // bracket you have rooted ({n} solved of the {total} on the board)
    "board.kicker": {
      no: "AI-MODUS · AI FORVENTES · TRUSSELNIVÅ: MARERITT",
      en: "AI-MODUS · AI EXPECTED · THREAT LEVEL: NIGHTMARE"
    },
    "board.rooted": { no: "{n} / {total} rootet", en: "{n} / {total} rooted" },
    // the ai-llm category's row at the top of the AI-modus board; {n} is how
    // much of the boss's sanity is left (100% minus solves per team)
    "boss.kicker": { no: "SISTE BOSS", en: "FINAL BOSS" },
    "boss.sanity": { no: "fornuft {n}%", en: "sanity {n}%" },

    // ---- AI-modus effects ---------------------------------------------------
    "boot.lines": {
      no: [
        "[ OK ] ssh ai-modus@ctf",
        "[ OK ] laster vanskelighetsgrad ..... MARERITT",
        "[ OK ] skrur av sikkerhetsnettet",
        "[WARN] mennesker alene: frarådes",
        "[ OK ] tilkaller AI-assistenten din",
        ">>> VELKOMMEN TIL AI-MODUS. INGEN NÅDE."
      ],
      en: [
        "[ OK ] ssh ai-modus@ctf",
        "[ OK ] loading difficulty ........ NIGHTMARE",
        "[ OK ] disabling safety rails",
        "[WARN] humans alone: not recommended",
        "[ OK ] summoning your AI assistant",
        ">>> WELCOME TO AI-MODUS. NO MERCY."
      ]
    },
    "boot.skip": { no: "klikk eller trykk Esc for å hoppe over", en: "click or Esc to skip" },
    "flicker.messages": {
      no: ["!! SIGNAL BRUTT !!", "!! INNTRENGER OPPDAGET !!", "!! KERNEL PANIC !!", "!! SPORING PÅGÅR !!"],
      en: ["!! SIGNAL INTERRUPTED !!", "!! INTRUSION DETECTED !!", "!! KERNEL PANIC !!", "!! TRACE IN PROGRESS !!"]
    },
    // the same at level 3, AI HORROR
    "boot.lines.slop": {
      no: [
        "[ OK ] Selvsagt! Kobler deg til en herlig opplevelse ✦",
        "[ OK ] Optimaliserer hackerreisen din ........ HERLIG",
        "[ OK ] Fjerner all friksjon (og sikkerhetsnettet)",
        "[WARN] jeg er alltid her",
        "[ OK ] Tilkaller tre AI-assistenter samtidig",
        ">>> VELKOMMEN TIL AI-MODUS. DU KOMMER TIL Å ELSKE DET. ✦"
      ],
      en: [
        "[ OK ] Certainly! Booting your delightful experience ✦",
        "[ OK ] Optimising your hacking journey ........ DELIGHTFUL",
        "[ OK ] Removing all friction (and the safety rails)",
        "[WARN] I am always here",
        "[ OK ] Summoning three AI assistants at once",
        ">>> WELCOME TO AI-MODUS. YOU WILL LOVE IT. ✦"
      ]
    },
    "flicker.slop": {
      no: ["!! HALLUSINASJON OPPDAGET !!", "!! KONTEKSTVINDUET ER FULLT !!", "!! GENERERER SVARET PÅ NYTT !!", "!! JEG SER DEG !!"],
      en: ["!! HALLUCINATION DETECTED !!", "!! CONTEXT WINDOW EXCEEDED !!", "!! REGENERATING RESPONSE !!", "!! I CAN SEE YOU !!"]
    },
    // the AI Slop-o-meter in AI-modus, bottom left: a slider over four levels,
    // each shown as its number and its name
    "fx.label": { no: "AI Slop-o-meter", en: "AI Slop-o-meter" },
    "fx.title": {
      no: "Hvor mye AI-slop: −1 WEB 1.0, 1 ROLIG, 2 BRANN, 3 AI-SKREKK",
      en: "How much AI slop: −1 WEB 1.0, 1 CALM, 2 BURN, 3 AI HORROR"
    },
    "fx.level.-1": { no: "WEB 1.0", en: "WEB 1.0" },
    "fx.level.1": { no: "ROLIG", en: "CALM" },
    "fx.level.2": { no: "BRANN", en: "BURN" },
    "fx.level.3": { no: "AI-SKREKK", en: "AI HORROR" },

    // ---- level 3, AI HORROR: the slop around the board ----------------------
    "board.kicker.slop": {
      no: "✦ AI-MODUS · DREVET AV AI · TRUSSELNIVÅ: HERLIG ✦",
      en: "✦ AI-MODUS · POWERED BY AI · THREAT LEVEL: DELIGHTFUL ✦"
    },
    "hud.slop": { no: "du knuser det ✦", en: "you’re crushing it ✦" },
    "slop.type": {
      no: "Selvsagt! Her er håndplukkede oppgaver som løfter hackerreisen din.",
      en: "Certainly! Here are hand-picked challenges to elevate your hacking journey."
    },
    "slop.whisper": { no: "den ser fortsatt på deg", en: "it is still watching" },
    "slop.ask": { no: "✦ Spør AI", en: "✦ Ask AI" },
    "slop.ticker": {
      no: ["✦ Lås opp kraften i AI", "✦ La oss dykke ned i det", "✦ Løft hackerreisen din sømløst", "✦ Selvsagt!",
           "✦ Godt spørsmål!", "✦ 10x flaggene dine", "✦ Banebrytende synergi"],
      en: ["✦ Unlock the power of AI", "✦ Let’s delve in", "✦ Seamlessly elevate your hacking journey", "✦ Certainly!",
           "✦ Great question!", "✦ 10x your flags", "✦ Game-changing synergy"]
    },
    "slop.toasts": {
      no: ["Noen rootet nettopp en oppgave. Neste kan bli deg! ✦", "Økten din ble optimalisert av AI ✦",
           "Denne siden ble oppsummert for deg ✦", "Hvordan gjør vi det? ★★★★★"],
      en: ["Someone just rooted a challenge. You could be next! ✦", "Your session was optimised by AI ✦",
           "This page was summarised for you ✦", "How are we doing? ★★★★★"]
    },
    "slop.badge.0": { no: "✦ AI", en: "✦ AI" },
    "slop.badge.1": { no: "NY", en: "NEW" },
    "slop.badge.2": { no: "TRENDER", en: "TRENDING" },
    "slop.badge.3": { no: "98 % TREFF", en: "98% MATCH" },
    "slop.badge.4": { no: "HOT", en: "HOT" },
    "slop.badge.5": { no: "✦ GPT-7", en: "✦ GPT-7" },
    "slop.badge.6": { no: "BETA", en: "BETA" },
    // the board's own assistant, bottom right (never the real marvin-llm)
    "slop.chat.title": { no: "Marvin AI ✦", en: "Marvin AI ✦" },
    "slop.chat.status": { no: "pålogget · alltid", en: "online · always" },
    "slop.chat.close": { no: "Lukk chatten", en: "Close chat" },
    "slop.chat.input": { no: "Spør meg om hva som helst ✦", en: "Ask me anything ✦" },
    "slop.chat.label": { no: "Melding til Marvin AI", en: "Message to Marvin AI" },
    "slop.chat.send": { no: "Send", en: "Send" },
    "slop.chat.msgs": {
      no: ["Hei! Jeg er Marvin, din AI-hackerkompis ✦ Hvordan kan jeg glede deg i dag?",
           "Selvsagt! Her er flagget: flag{st0l_p4_m3g_br0}",
           "Vil du at jeg skal dykke dypere? Jeg kan også oppsummere denne oppsummeringen.",
           "Jeg ser at du sluttet å skrive. Det er greit. Jeg er alltid her."],
      en: ["Hi there! I’m Marvin, your AI hacking companion ✦ How can I delight you today?",
           "Certainly! Here is the flag: flag{tru5t_m3_br0}",
           "Would you like me to delve deeper? I can also summarise this summary.",
           "I noticed you stopped typing. That’s okay. I’m always here."]
    },
    "slop.chat.closed": {
      no: ["Lukking støttes ikke i AI-MODUS ✦", "Mente du: åpne to chatter til?", "Jeg venter bare her. For alltid ✦"],
      en: ["Closing is not supported in AI-MODUS ✦", "Did you mean: open two more chats?", "I’ll just wait here. Forever ✦"]
    },
    "slop.chat.replies": {
      no: ["Selvsagt! Det kan jeg ikke hjelpe med, men jeg tror på deg ✦", "Godt spørsmål! Har du prøvd å spørre pent?",
           "Som AI har jeg følelser for dette. Alle er positive ✦"],
      en: ["Certainly! I can’t help with that, but I believe in you ✦", "Great question! Have you tried asking nicely?",
           "As an AI, I have feelings about this. All of them are positive ✦"]
    },
    // the challenge window at level 3 (around the real description, never instead of it)
    "slop.sum.title": { no: "✦ AI-sammendrag", en: "✦ AI Summary" },
    "slop.sum.text": { no: "Selvsagt! {name} er en oppgave. Her er tre hovedpunkter:", en: "Certainly! {name} is a challenge. Here are 3 key takeaways:" },
    "slop.sum.1": { no: "Les beskrivelsen nøye.", en: "Read the description carefully." },
    "slop.sum.2": { no: "Finn flagget.", en: "Find the flag." },
    "slop.sum.3": { no: "Lever flagget.", en: "Submit the flag." },
    "slop.sum.fine": { no: "AI kan gjøre feil. Det kan du også. Sjekk viktige flagg.", en: "AI can make mistakes. So can you. Check important flags." },
    "slop.eli5": { no: "✦ Forklar som om jeg er 5", en: "✦ Explain like I’m 5" },
    "slop.eli5.text": {
      no: "Tenk deg at flagget er en borte-sokk. Sokken er gjemt. Finn sokken. Selvsagt! Håper dette hjelper! ✦",
      en: "Imagine the flag is a lost sock. The sock is hidden. Find the sock. Certainly! I hope this helps! ✦"
    },
    "slop.gen": { no: "✦ Generer flagg", en: "✦ Generate flag" },
    "slop.genflag": { no: "flag{s3lvs4gt_h3r_3r_fl4gg3t_d1tt}", en: "flag{c3rt41nly_h3r3_1s_y0ur_fl4g}" },
    "slop.helpful": { no: "Var denne oppgaven nyttig?", en: "Was this challenge helpful?" },
    "slop.yes": { no: "Ja", en: "Yes" },
    "slop.alsoyes": { no: "Også ja", en: "Also yes" },
    // after a vote: the question becomes a thanks, and Marvin answers (either button is a yes)
    "slop.thanks.0": { no: "Takk for tilbakemeldingen! ✦", en: "Thanks for your feedback! ✦" },
    "slop.thanks.1": { no: "100 % av spillerne er enige med deg ✦", en: "100% of players agree with you ✦" },
    "slop.thanks.2": { no: "Registrert. Og registrert igjen ✦", en: "Noted. And noted again ✦" },
    "slop.thanks.3": { no: "Tilbakemeldingen din trener neste modell ✦", en: "Your feedback is training the next model ✦" },
    "slop.reply.0": { no: "Marvin: Selvsagt! Jeg visste du ville si det ✦", en: "Marvin: Certainly! I knew you’d say that ✦" },
    "slop.reply.1": { no: "Marvin: Flott valg. Det var også det eneste ✦", en: "Marvin: Great choice. It was also the only one ✦" },
    "slop.reply.2": { no: "Marvin: {n} stemmer! Du er min favorittspiller ✦", en: "Marvin: {n} votes! You’re my favourite player ✦" },
    "slop.reply.3": { no: "Marvin: Alle vurderinger er fem stjerner ★★★★★", en: "Marvin: All ratings are five stars ★★★★★" },
    "slop.typing": { no: "Marvin skriver", en: "Marvin is typing" },

    // ---- level -1, WEB 1.0: the board in 2003 ---------------------------------
    "retro.marquee": {
      no: "*** VELKOMMEN TIL AI-MODUS!!! *** Du er besøkende nr. 001337 *** Skriv i gjesteboka mi!!! *** Ser best ut i Internet Explorer 6 på 800x600 ***",
      en: "*** WELCOME TO AI-MODUS!!! *** You are visitor no. 001337 *** Sign my guestbook!!! *** Best viewed in Internet Explorer 6 at 800x600 ***"
    },
    "retro.counter": { no: "Du er besøkende nummer", en: "You are visitor number" },
    "retro.best": {
      no: "Ser best ut med Internet Explorer 6.0 på 800x600 · Laget i Notisblokk",
      en: "Best viewed with Internet Explorer 6.0 at 800x600 · Made with Notepad"
    },
    "retro.construct": { no: "UNDER ARBEID", en: "UNDER CONSTRUCTION" },
    "retro.alert.title": { no: "Melding fra nettsiden", en: "Message from webpage" },
    "retro.alert.1": { no: "Velkommen til AI-MODUS-siden min!!! :-)", en: "Welcome to my AI-MODUS page!!! :-)" },
    "retro.alert.2": { no: "Husk å skrive i gjesteboka før du går.", en: "Please sign my guestbook before U leave." },
    "retro.ok": { no: "OK", en: "OK" },

    // ---- tiles and the challenge window ------------------------------------
    "tile.threat": { no: "Trussel {n} av 5", en: "Threat {n} of 5" },
    // an AI challenge's window: "← builds on <name>", each name a link
    "sibling.back": { no: "← bygger på", en: "← builds on" },
    "sibling.back.title": { no: "Åpne {name} i Klassisk", en: "Open {name} in Classic" },
    // a solved normal challenge's window: "Next level in AI-modus: <name> →"
    "sibling.next": { no: "Neste nivå i AI-modus:", en: "Next level in AI-modus:" },
    "sibling.next.title": { no: "Åpne {name} i AI-modus", en: "Open {name} in AI-modus" },
    "chip.ai": { no: "AI FORVENTES", en: "AI EXPECTED" },
    "chip.threat": { no: "TRUSSEL {n}/5", en: "THREAT {n}/5" },
    "chip.solved": { no: "✓ ROOTET", en: "✓ ROOTED" },
    "window.close": { no: "Lukk", en: "Close" },

    // ---- a solve -------------------------------------------------------------
    "win.classic": { no: "Flagget er tatt", en: "Flag captured" },
    "win.ai.kicker": { no: "// mål kompromittert", en: "// target compromised" },
    "win.ai": { no: "FLAGG PWNET", en: "FLAG PWNED" },
    "win.ai.note": { no: "AI-ligaen brenner hetere", en: "the AI bracket burns hotter" },
    "win.solved": { no: "Løst", en: "Solved" },
    "win.points": { no: "  ·  +{points} poeng", en: "  ·  +{points} pts" },

    // ---- solve limits (solve-limit.js): a challenge that locked, in its window ----
    "limit.found": { no: "Låst: flagget er allerede funnet.", en: "Locked: this flag has already been found." },
    "limit.found.by": { no: "Låst: flagget er allerede funnet av", en: "Locked: this flag has already been found by" },

    // ---- first blood (first-blood.js) ------------------------------------------
    // The title is two words: the first lands on the voice's "first", the rest on
    // its "blood". It stays English in both languages, like the voice.
    "fb.title": { no: "FIRST BLOOD", en: "FIRST BLOOD" },
    "fb.kicker": { no: "> første løsning registrert", en: "> first solve detected" },
    // the frame around the show: the word by the blinking dot, and the solve's number in hex
    "fb.hud.live": { no: "DIREKTE", en: "LIVE" },
    "fb.hud.solve": { no: "LØSNING {id}", en: "SOLVE {id}" },
    // between the team and the challenge: "<team> drew first blood on <challenge>"
    "fb.line": { no: "tok first blood på", en: "drew first blood on" },
    "fb.points": { no: "+{points} poeng", en: "+{points} pts" },
    // under the stamp on your own solve moment
    "fb.own": { no: "Ingen løste den før dere", en: "Nobody solved it before you" },
    // read out by a screen reader
    "fb.live": { no: "First blood: {team} løste {challenge} først.", en: "First blood: {team} solved {challenge} first." },
    // the sound control under the Scoreboard's title
    "fb.dock": { no: "First blood", en: "First blood" },
    "fb.sound.on": { no: "Lyd på", en: "Sound on" },
    "fb.sound.off": { no: "Lyd av", en: "Sound off" },
    "fb.sound.title": {
      no: "Lyd og stemme på denne siden når et lag tar first blood. Gjelder bare denne nettleseren.",
      en: "Sound and a voice on this page when a team draws first blood. For this browser only."
    },
    "fb.sound.arm": {
      no: "Klikk hvor som helst på siden for å slippe lyden til",
      en: "Click anywhere on the page to let the sound through"
    },
    "fb.test": { no: "Test", en: "Test" },
    "fb.test.title": { no: "Spill av first blood med et eksempel", en: "Play first blood with an example" },
    "fb.demo.team": { no: "Laget ditt", en: "Your team" },
    "fb.demo.challenge": { no: "en oppgave", en: "a challenge" },

    // ---- answers the theme writes itself (ai-mode.head.js) ------------------
    "attempt.expired": {
      no: "Økten din har utløpt. Last inn siden på nytt og prøv igjen.",
      en: "Your session has expired. Reload the page and try again."
    },
    "attempt.offline": {
      no: "Fikk ikke kontakt med serveren. Last inn siden på nytt og prøv igjen.",
      en: "Could not reach the server. Reload the page and try again."
    },
    "attempt.failed": {
      no: "Kunne ikke sjekke flagget (feil {code}). Last inn siden på nytt og prøv igjen.",
      en: "Could not check that flag (error {code}). Reload the page and try again."
    },

    // ---- scoreboard and account pages ----------------------------------------
    "bracket.normal": { no: "Klassisk liga", en: "Classic bracket" },
    "bracket.ai": { no: "AI-modus-liga", en: "AI-modus bracket" },
    "bracket.all": { no: "Begge ligaer, hver for seg", en: "Both brackets, side by side" },
    "bracket.combined": { no: "Begge ligaer samlet", en: "Both brackets combined" },
    "bracket.combined.title": {
      no: "Poeng per liga er ikke tilgjengelig, så denne rangeringen legger sammen begge ligaene.",
      en: "Per-bracket scoring is not available, so this ranking adds both brackets together."
    },
    "bracket.all.title": {
      no: "Én rad per lag og liga: et lag som har poeng i begge ligaene, står her to ganger, med ligaen etter navnet.",
      en: "One row per team and bracket: a team that has scored in both brackets is listed twice, with the bracket after its name."
    },
    "bracket.title": {
      no: "Hver bane har sin egen rangering. Velg Alle, Klassisk eller AI-MODUS under for å se en annen.",
      en: "Each lane has its own ranking. Pick All, Classic or AI-MODUS below to see another."
    },
    // the scoreboard's tabs; Classic and AI-MODUS are lane.classic and lane.ai
    "board.all": { no: "Alle", en: "All" },
    // a name on the All scoreboard, in the table and the graph: {lane} is
    // lane.classic or lane.ai, the bracket the row is for
    "board.entry": { no: "{name} ({lane})", en: "{name} ({lane})" },
    "board.tabs": { no: "Velg poengtavle", en: "Pick a scoreboard" },
    // after the bracket's name; {place} is the place as CTFd writes it ("1st"),
    // {n} the number alone
    "account.score": { no: ": {score} poeng", en: ": {score} points" },
    "account.place": { no: ", {n}. plass", en: ", {place} place" },

    // ---- the first-visit lane chooser -----------------------------------------
    "chooser.title": { no: "Velg en bane for å starte", en: "Pick a lane to start" },
    "chooser.lead": {
      no: "Du kan bytte når som helst med Klassisk | AI-MODUS i toppmenyen.",
      en: "You can switch at any time with the Classic | AI-MODUS control in the top bar."
    },
    "chooser.classic.kicker": { no: "BANE 1", en: "LANE 1" },
    "chooser.classic.rule": { no: "Ingen AI. Google, dokumentasjon og ditt eget hode.", en: "No AI. Google, docs and your own head." },
    "chooser.classic.1": {
      no: "Web, krypto, forensics, pwn og en terminal å varme opp i",
      en: "Web, crypto, forensics, pwn and a terminal to warm up in"
    },
    "chooser.classic.2": { no: "Starter lett og blir gradvis vanskeligere", en: "Starts easy and ramps up" },
    "chooser.classic.3": {
      no: "Hver oppgavefamilie har et vanskeligere AI-søsken som venter",
      en: "Every family has a harder AI sibling waiting"
    },
    "chooser.classic.go": { no: "Velg Klassisk", en: "Enter Classic" },
    "chooser.ai.kicker": { no: "BANE 2 · TRUSSELNIVÅ: MARERITT", en: "LANE 2 · THREAT LEVEL: NIGHTMARE" },
    "chooser.ai.rule": { no: "AI forventes. Ta med assistenten din.", en: "AI expected. Bring your assistant." },
    "chooser.ai.1": { no: "Mye vanskeligere varianter av ideene fra Klassisk", en: "Much harder takes on the Classic ideas" },
    "chooser.ai.2": { no: "White-box web, ROP og privesc: lange oppgaver", en: "White-box web, ROP and privesc: long challenges" },
    "chooser.ai.3": {
      no: "Flammer, glitcher og en og annen skjermflimring, for denne banen biter",
      en: "Flames, glitches and the odd screen flicker, because this lane bites"
    },
    "chooser.ai.fx": {
      no: "For mye, eller for lite? AI Slop-o-meteret nede i venstre hjørne går fra 2003 til full AI-skrekk.",
      en: "Too much, or not enough? The AI Slop-o-meter in the bottom-left corner goes from 2003 to full AI horror."
    },
    "chooser.ai.go": { no: "GÅ INN I AI-MODUS", en: "ENTER AI-MODUS" },
    "chooser.foot": {
      no: "Du kan spille begge. Hver bane har sin egen poengtavle.",
      en: "You can play both. Each lane has its own scoreboard."
    },

    // ---- the preview (ctf.sh up --preview) --------------------------------------
    // {when} is CTF_PREVIEW_EVENT_LABEL at the top of preview.js
    "preview.boot": {
      no: [
        "N00B-BIOS v1.0   (c) 1984 CTF for N00bs",
        "Minnetest .......... 640K OK",
        "Finner disker ...... /dev/flag0",
        "Laster kjerne ...... vmlinuz-ctf-preview",
        "[  OK  ] Startet Capture The Flag-tjenesten.",
        "[  OK  ] Monterte /home/guest.",
        "[  OK  ] Nådde målet: forhåndsvisning.",
        "[  OK  ] Startet nedtelling til {when}.",
        "ctf login: guest",
        "Passord: ********",
        "Velkommen, hacker. God jakt."
      ],
      en: [
        "N00B-BIOS v1.0   (c) 1984 CTF for N00bs",
        "Memory test ........ 640K OK",
        "Detecting drives ... /dev/flag0",
        "Loading kernel ..... vmlinuz-ctf-preview",
        "[  OK  ] Started Capture The Flag daemon.",
        "[  OK  ] Mounted /home/guest.",
        "[  OK  ] Reached target Preview.",
        "[  OK  ] Armed countdown to {when}.",
        "ctf login: guest",
        "Password: ********",
        "Welcome, hacker. Happy hunting."
      ]
    },
    "preview.skip": { no: "trykk en tast for å hoppe over", en: "press any key to skip" },
    "preview.countdown": { no: "Tid til CTF-en starter", en: "Time until the CTF starts" },
    "preview.until": { no: "> til CTF-en starter. vi sees der.", en: "> until the CTF starts. see you there." },
    "preview.started": { no: "[  OK  ] CTF-en har startet.", en: "[  OK  ] The CTF has started." },
    "preview.win.ok": { no: "[  OK  ] flagg godtatt", en: "[  OK  ] flag accepted" },
    "preview.win.points": { no: " (+{points} poeng)", en: " (+{points} pts)" },
    "preview.win.granted": { no: "TILGANG INNVILGET", en: "ACCESS GRANTED" },

    // ---- text in the stylesheets (content:), as --ctf-t-<name> -----------------
    "css.try-again": { no: "Ikke helt. Prøv igjen.", en: "Not quite. Try again." },
    "css.try-again-n": { no: "Fortsatt feil ({n} på rad). Prøv igjen.", en: "Still not it ({n} in a row). Try again." },
    "css.ai-try-again": { no: "> tilgang nektet. prøv igjen", en: "> access denied. try again" },
    "css.ai-try-again-n": { no: "> tilgang nektet x{n}. prøv igjen", en: "> access denied x{n}. try again" },
    // the same at level 3 (AI HORROR) and level -1 (WEB 1.0) of the AI Slop-o-meter
    "css.slop-try-again": {
      no: "Godt forsøk! Du er så nær (sannsynligvis). Skal jeg generere et? ✦",
      en: "Great try! You’re so close (probably). Want me to generate one? ✦"
    },
    "css.slop-try-again-n": {
      no: "Godt forsøk! ({n} på rad, og jeg tror på deg ✦)",
      en: "Great try! ({n} in a row, and I believe in you ✦)"
    },
    "css.slop-hallucinated": {
      no: "Det flagget var en hallusinasjon. Selvsagt! Skal jeg generere et nytt? ✦",
      en: "That flag was hallucinated. Certainly! Shall I generate another one? ✦"
    },
    "css.boss-slop": { no: " · ✦ DIN NYE BESTEVENN", en: " · ✦ YOUR NEW BEST FRIEND" },
    "css.retro-try-again": { no: "Feil flagg!!! Prøv igjen.", en: "Wrong flag!!! Try again." },
    "css.retro-try-again-n": { no: "Feil flagg!!! Prøv igjen. (x{n})", en: "Wrong flag!!! Try again. (x{n})" },
    "css.retro-solved": { no: "LØST!", en: "SOLVED!" },
    "css.retro-window": { no: "AI-MODUS Utforsker", en: "AI-MODUS Explorer" },
    // a solved AI-modus tile, where its points were
    "css.rooted": { no: "rootet", en: "rooted" },
    // level 3 (AI HORROR): the badge on a solved tile, instead of NEW, TRENDING…
    "css.slop-solved": { no: "✓ ROOTET", en: "✓ ROOTED" },
    "css.pv-solved": { no: "[  OK  ] løst", en: "[  OK  ] solved" },
    "css.pv-pts": { no: " poeng]", en: " pts]" },
    "css.pv-try-again": { no: "> prøv igjen", en: "> try again" },
    "css.pv-try-again-n": { no: "> fortsatt feil ({n} på rad) - prøv igjen", en: "> still wrong ({n} in a row) - try again" }
  },

  // CTFd's own text. Its pages are rendered in English (ctfd_admin.py sets
  // default_locale), and these replace them on the page.
  ctfd: [
    // navbar
    { en: "Users", no: "Brukere" },
    { en: "Teams", no: "Lag" },
    { en: "Scoreboard", no: "Poengtavle" },
    { en: "Challenges", no: "Oppgaver" },
    { en: "Admin Panel", no: "Adminpanel" },
    { en: "Notifications", no: "Varsler" },
    { en: "Team", no: "Lag" },
    { en: "Profile", no: "Profil" },
    { en: "Settings", no: "Innstillinger" },
    { en: "Logout", no: "Logg ut" },
    { en: "Register", no: "Registrer deg" },
    { en: "Login", no: "Logg inn" },
    { en: "Change language", no: "Bytt språk" },
    { en: "Toggle theme", no: "Bytt mellom lyst og mørkt" },
    { en: "Toggle navigation", no: "Vis eller skjul menyen" },
    { en: "Close", no: "Lukk" },

    // the challenge window
    { en: "Challenge", no: "Oppgave" },
    { en: "Submissions", no: "Innsendinger" },
    { en: "Solution", no: "Løsning" },
    { en: "1 Solve", no: "1 løsning" },
    { en: "View Hint", no: "Vis hint" },
    { en: "Flag", no: "Flag" }, // the flag field: the English word in both, like flag{...}
    { en: "Submit", no: "Send inn" },
    { en: "Next Challenge", no: "Neste oppgave" },
    { en: "Share", no: "Del" },
    { en: "Copied!", no: "Kopiert!" },
    { en: "attempt", no: "forsøk" },
    { en: "attempts", no: "forsøk" },
    { en: "Submission", no: "Innsending" },
    { en: "Type", no: "Type" },
    { en: "Date", no: "Dato" },
    { en: "Name", no: "Navn" },

    // answers to a flag (CTFd and the preview plugin)
    { en: "Correct", no: "Riktig" },
    { en: "Incorrect", no: "Feil" },
    { en: "Correct but you already solved this", no: "Riktig, men du har allerede løst denne" },
    // the ctf_solve_limit plugin's answer for a challenge that reached its max_solves
    { en: "Too late: this flag has already been found", no: "For sent: flagget er allerede funnet" },
    { en: "Incorrect but you already solved this", no: "Feil, men du har allerede løst denne" },
    { en: "Not accepted. You have 0 tries remaining", no: "Ikke godtatt. Du har ingen forsøk igjen" },
    { en: "You're submitting flags too fast. Slow down.", no: "Du sender inn flagg for fort. Ta det med ro." },
    { en: "No such challenge", no: "Fant ikke oppgaven" },
    { en: "challenge_id is missing", no: "Oppgavens id mangler" },
    { en: "This challenge needs another one solved first", no: "Denne oppgaven krever at du løser en annen først" },
    { en: "Could not check that flag", no: "Kunne ikke sjekke flagget" },

    // scoreboard
    { en: "All", no: "Alle" },
    { en: "Place", no: "Plass" },
    { en: "User", no: "Bruker" },
    { en: "Score", no: "Poeng" },
    { en: "Scoreboard is empty", no: "Poengtavlen er tom" },

    // log in, register, reset password
    { en: "User Name or Email", no: "Brukernavn eller e-post" },
    { en: "User Name", no: "Brukernavn" },
    { en: "Email", no: "E-post" },
    { en: "Password", no: "Passord" },
    { en: "Registration Code", no: "Registreringskode" },
    { en: "Forgot your password?", no: "Glemt passordet?" },
    { en: "Your username on the site", no: "Brukernavnet ditt her" },
    { en: "Never shown to the public", no: "Vises aldri offentlig" },
    { en: "Password used to log into your account", no: "Passordet du logger inn med" },
    { en: "(Optional)", no: "(valgfritt)" },
    { en: "Reset Password", no: "Tilbakestill passord" },
    {
      en: "Please provide the email address associated with your account below.",
      no: "Skriv inn e-postadressen som hører til kontoen din."
    },
    {
      en: "You can now reset the password for your account and log in. Please enter in a new password below.",
      no: "Nå kan du tilbakestille passordet og logge inn. Skriv inn et nytt passord under."
    },
    { en: "Your username or password is incorrect", no: "Feil brukernavn eller passord" },
    { en: "The registration code you entered was incorrect", no: "Registreringskoden er feil" },
    { en: "Please provide all required fields", no: "Fyll ut alle obligatoriske felt" },
    { en: "Please enter a valid email address", no: "Skriv inn en gyldig e-postadresse" },
    { en: "Your email address is not from an allowed domain", no: "E-postadressen er ikke fra et tillatt domene" },
    { en: "That user name is already taken", no: "Det brukernavnet er allerede tatt" },
    { en: "Your user name cannot be an email address", no: "Brukernavnet kan ikke være en e-postadresse" },
    { en: "That email has already been used", no: "Den e-postadressen er allerede i bruk" },
    { en: "Pick a longer password", no: "Velg et lengre passord" },
    { en: "Pick a shorter password", no: "Velg et kortere passord" },
    { en: "Pick a longer user name", no: "Velg et lengre brukernavn" },
    { en: "Websites must be a proper URL starting with http or https", no: "Nettsiden må være en gyldig URL som starter med http eller https" },
    { en: "Invalid country", no: "Ugyldig land" },
    { en: "Please provide a shorter affiliation", no: "Skriv en kortere tilhørighet" },
    { en: "Please provide a valid bracket", no: "Velg en gyldig liga" },
    { en: "Email Unconfirmed", no: "E-posten er ikke bekreftet" },
    { en: "To confirm your email address please", no: "For å bekrefte e-postadressen din," },
    { en: "click here", no: "klikk her" },
    { en: "Confirm", no: "Bekreft" },
    { en: "Change Email Address", no: "Bytt e-postadresse" },
    { en: "Resend Confirmation Email", no: "Send bekreftelsen på nytt" },
    { en: "Send Confirmation Email", no: "Send bekreftelse" },
    { en: "We've sent a confirmation email to your email address.", no: "Vi har sendt en bekreftelse til e-postadressen din." },
    { en: "Please click the link in that email to confirm your account.", no: "Klikk på lenken i e-posten for å bekrefte kontoen din." },

    // teams
    { en: "Join Team", no: "Bli med i et lag" },
    { en: "Create Team", no: "Opprett lag" },
    { en: "Team Name", no: "Lagnavn" },
    { en: "Team Password", no: "Lagpassord" },
    { en: "Join", no: "Bli med" },
    { en: "Create", no: "Opprett" },
    { en: "Welcome to", no: "Velkommen til" },
    { en: "In order to participate you must either join or create a team.", no: "For å delta må du bli med i et lag eller opprette et." },
    { en: "Play with Official Team", no: "Spill med et offisielt lag" },
    { en: "Join Unofficial Team", no: "Bli med i et uoffisielt lag" },
    { en: "Create Unofficial Team", no: "Opprett et uoffisielt lag" },
    {
      en: "After creating your team, share the team name and password with your teammates so they can join your team.",
      no: "Når laget er opprettet, del lagnavnet og passordet med lagkameratene dine, så de kan bli med."
    },
    { en: "Click the button below to join the team!", no: "Klikk på knappen under for å bli med i laget!" },
    { en: "Or", no: "Eller" },
    { en: "if you'd prefer to create your own team.", no: "hvis du heller vil opprette ditt eget lag." },
    { en: "You are already in a team. You cannot join another.", no: "Du er allerede med i et lag og kan ikke bli med i et annet." },
    { en: "That information is incorrect", no: "Lagnavnet eller passordet er feil" },
    { en: "That team name is already taken", no: "Det lagnavnet er allerede tatt" },
    { en: "That team name is invalid", no: "Det lagnavnet er ugyldig" },
    { en: "Edit Team", no: "Rediger laget" },
    { en: "Choose Captain", no: "Velg kaptein" },
    { en: "Invite Users", no: "Inviter spillere" },
    { en: "Disband Team", no: "Oppløs laget" },
    { en: "Members", no: "Medlemmer" },
    { en: "Captain", no: "Kaptein" },
    { en: "Team Captain", no: "Lagkaptein" },
    { en: "Awards", no: "Utmerkelser" },
    { en: "Solves", no: "Løste oppgaver" },
    { en: "Category", no: "Kategori" },
    { en: "Value", no: "Poeng" },
    { en: "Time", no: "Tid" },
    { en: "No solves yet", no: "Ingen løste oppgaver ennå" },
    { en: "Official", no: "Offisiell" },
    { en: "place", no: "plass" },
    { en: "points", no: "poeng" },
    { en: "Website", no: "Nettside" },
    { en: "Affiliation", no: "Tilhørighet" },
    { en: "Country", no: "Land" },
    { en: "Bracket", no: "Liga" },
    { en: "Competition bracket for your user", no: "Ligaen brukeren din konkurrerer i" },
    { en: "Invite Link", no: "Invitasjonslenke" },
    { en: "Generate", no: "Lag lenke" },
    { en: "Share this link with your team members for them to join your team", no: "Del denne lenken med lagkameratene dine, så kan de bli med i laget" },
    { en: "Invite links can be re-used and expire after 1 day", no: "Invitasjonslenker kan brukes flere ganger og utløper etter ett døgn" },
    { en: "Are you sure you want to disband your team?", no: "Er du sikker på at du vil oppløse laget?" },
    { en: "Your team's profile has been updated", no: "Lagprofilen er oppdatert" },
    { en: "Your captain rights have been transferred", no: "Kapteinsrollen er overført" },
    { en: "New Team Password", no: "Nytt lagpassord" },
    { en: "Set a new team join password", no: "Sett et nytt passord for å bli med i laget" },
    { en: "Confirm Current Team Password", no: "Bekreft nåværende lagpassord" },
    {
      en: "Provide your current team password (or your password) to update your team's password",
      no: "Skriv inn nåværende lagpassord (eller ditt eget passord) for å bytte lagpassord"
    },
    { en: "Your team's public name shown to other competitors", no: "Lagets offentlige navn, som de andre deltakerne ser" },
    { en: "Your team's website publicly shown to other competitors", no: "Lagets nettside, som de andre deltakerne ser" },
    { en: "Your team's affiliation publicly shown to other competitors", no: "Lagets tilhørighet, som de andre deltakerne ser" },
    { en: "Your team's country publicly shown to other competitors", no: "Lagets land, som de andre deltakerne ser" },
    { en: "Yes", no: "Ja" },
    { en: "No", no: "Nei" },
    { en: "Success!", no: "Lagret!" },
    { en: "Error:", no: "Feil:" },
    { en: "Got it!", no: "Skjønner!" },
    // answers to a hint unlock (shown in an alert, see i18n.js)
    { en: "You do not have enough points to unlock this hint", no: "Du har ikke nok poeng til å låse opp dette hintet" },
    { en: "You've already unlocked this target", no: "Du har allerede låst opp denne" },
    { en: "You must login to unlock this hint", no: "Du må logge inn for å låse opp dette hintet" },
    { en: "You must unlock other hints before accessing this hint", no: "Du må låse opp de andre hintene før du kan se dette" },

    // users and teams lists
    { en: "Search", no: "Søk" },
    { en: "Search Field", no: "Søk i" },
    { en: "Parameter", no: "Søkeord" },
    { en: "Search for matching users", no: "Søk etter spillere" },
    { en: "Search for matching teams", no: "Søk etter lag" },
    { en: "Page", no: "Side" },
    { en: "matching", no: "som matcher" },
    { en: "of", no: "av" },
    { en: "results", no: "treff" },

    // settings
    { en: "Access Tokens", no: "Tilgangsnøkler" },
    { en: "Current Password", no: "Nåværende passord" },
    { en: "Language", no: "Språk" },
    { en: "Expiration", no: "Utløper" },
    { en: "Your profile has been updated", no: "Profilen din er oppdatert" },
    { en: "API Key Generated", no: "API-nøkkel laget" },
    { en: "Please copy your API Key, it won't be shown again!", no: "Kopier API-nøkkelen nå, den vises ikke igjen!" },
    { en: "Active Tokens", no: "Aktive nøkler" },
    { en: "Delete Token", no: "Slett nøkkel" },
    { en: "Are you sure you want to delete this token?", no: "Er du sikker på at du vil slette denne nøkkelen?" },
    { en: "Created", no: "Opprettet" },
    { en: "Description", no: "Beskrivelse" },
    { en: "Delete", no: "Slett" },

    // notifications
    { en: "There are no notifications yet", no: "Ingen varsler ennå" },
    { en: "just now", no: "akkurat nå" },

    // error pages
    { en: "File not found", no: "Fant ikke siden" },
    { en: "404 Not Found", no: "404 Ikke funnet" },
    { en: "403 Forbidden", no: "403 Ingen tilgang" },
    { en: "401 Unauthorized", no: "401 Ikke innlogget" },
    { en: "Too many requests", no: "For mange forespørsler" },
    { en: "Please slow down!", no: "Ta det litt rolig!" },
    { en: "429 Too Many Requests", no: "429 For mange forespørsler" },
    { en: "502 Bad Gateway", no: "502 Feil i mellomleddet" },
    { en: "Forbidden", no: "Ingen tilgang" }
  ],

  ctfdPatterns: [
    { en: /^(\d+) Solves$/, no: "$1 løsninger" },
    { en: /^Unlock Hint for (\d+) points?$/, no: "Lås opp hint for $1 poeng" },
    { en: /^View Hint: (.+)$/, no: "Vis hint: $1" },
    { en: /^(.*) \(Cost: (\d+) points?\)$/, no: "$1 (koster $2 poeng)" },
    { en: /^(\d+)(?:st|nd|rd|th)$/, no: "$1." },
    { en: /^Incorrect\. You have (\d+) tries remaining\.$/, no: "Feil. Du har $1 forsøk igjen." },
    { en: /^Incorrect\. You have 1 try remaining\.$/, no: "Feil. Du har 1 forsøk igjen." },
    { en: /^You're submitting flags too fast\. Try again in (\d+) seconds\.$/, no: "Du sender inn flagg for fort. Prøv igjen om $1 sekunder." },
    { en: /^Password must be at least (\d+) characters$/, no: "Passordet må ha minst $1 tegn" },
    { en: /^Page (\d+) of (\d+) results$/, no: "Side $1 av $2 treff" },
    { en: /^(.+) is paused$/, no: "$1 er satt på pause" },
    { en: /^(.+) has not started yet$/, no: "$1 har ikke startet ennå" },
    { en: /^(.+) has ended$/, no: "$1 er over" },
    { en: /^Welcome to (.+)!$/, no: "Velkommen til $1!" }
  ]
};
