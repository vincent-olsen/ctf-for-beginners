<!--
  The front page (route "index"), synced into CTFd by ./ctf.sh up (see
  docs/language.md). One file for both languages: the style and the countdown
  script are shared, and each text is a block per language (class="ctf-lang"),
  of which the page shows the player's. Without the theme (CTF_AI_MODE=off) only
  the default language's blocks are kept.
-->
<style>
  .countdown-container {
    text-align: center;
    padding: 20px 0;
  }
  /* One row at any width: the digits shrink with the screen instead of wrapping. */
  #countdown-box {
    display: inline-flex;
    flex-wrap: nowrap;
    justify-content: center;
    gap: clamp(0.5rem, 3vw, 1.5rem);
    max-width: 100%;
    padding: 10px 0;
  }
  .time-unit {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 0;
  }
  .number {
    font-size: clamp(2.5rem, 12vw, 5rem);
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
    color: #B5E853;
  }
  .label {
    font-size: 0.8em;
    color: #B5E853;
  }
  .welcome-message, .action-message, .info-link, .start-here {
    text-align: center;
  }
  .welcome-message {
    margin-top: 2.5rem;
  }
  .start-here {
    max-width: 40rem;
    margin: 2rem auto;
    padding: 1rem 1.25rem 0.25rem;
    border: 1px solid rgba(181, 232, 83, 0.35);
    border-radius: 8px;
  }
  .start-here h5 {
    color: #B5E853;
  }
</style>

<div class="countdown-container" id="countdown" hidden>
  <p id="countdown-before" hidden>
    <span class="ctf-lang" lang="no">Starter om</span><span class="ctf-lang" lang="en">Starts in</span>
  </p>
  <p id="countdown-running" hidden>
    <span class="ctf-lang" lang="no">Tid igjen</span><span class="ctf-lang" lang="en">Time left</span>
  </p>
  <p id="countdown-over" hidden>
    <span class="ctf-lang" lang="no">Det var det! Takk for i dag 🙌</span><span class="ctf-lang" lang="en">That's a wrap! Thanks for today 🙌</span>
  </p>
  <div id="countdown-box">
    <span class="time-unit" id="days-unit" style="display: none">
      <span id="days" class="number"></span>
      <span class="label"><span class="ctf-lang" lang="no">Dager</span><span class="ctf-lang" lang="en">Days</span></span>
    </span>
    <span class="time-unit">
      <span id="hours" class="number"></span>
      <span class="label"><span class="ctf-lang" lang="no">Timer</span><span class="ctf-lang" lang="en">Hours</span></span>
    </span>
    <span class="time-unit">
      <span id="minutes" class="number"></span>
      <span class="label"><span class="ctf-lang" lang="no">Minutter</span><span class="ctf-lang" lang="en">Minutes</span></span>
    </span>
    <span class="time-unit">
      <span id="seconds" class="number"></span>
      <span class="label"><span class="ctf-lang" lang="no">Sekunder</span><span class="ctf-lang" lang="en">Seconds</span></span>
    </span>
  </div>
</div>

<div class="welcome-message">
  <p class="ctf-lang" lang="no">Velkommen til en ettermiddag med lovlig hacking, pizza og øl 🚩</p>
  <p class="ctf-lang" lang="en">Welcome to an afternoon of legal hacking, pizza and beer 🚩</p>
</div>
<div class="action-message">
  <h4 class="ctf-lang" lang="no">
    Lag deg en konto og bli med i et lag, så får du tilgang til <a href="challenges">oppgavene</a>.
  </h4>
  <h4 class="ctf-lang" lang="en">
    Create an account and join a team, and the <a href="challenges">challenges</a> are yours.
  </h4>
  <p class="ctf-lang" lang="no">Registreringskoden får du når eventet starter.</p>
  <p class="ctf-lang" lang="en">You'll get the registration code when the event starts.</p>
</div>
<div class="start-here">
  <h5 class="ctf-lang" lang="no">Første gang? Start her</h5>
  <h5 class="ctf-lang" lang="en">First time? Start here</h5>
  <p class="ctf-lang" lang="no">Begynn med <strong>meow1</strong>, eller <strong>overflow1</strong> hvis du vil prøve pwn. Ha klar <code>nc</code> (på Windows: <code>ncat</code> fra Nmap), CyberChef og nettleserens utviklerverktøy (F12).</p>
  <p class="ctf-lang" lang="en">Begin with <strong>meow1</strong>, or <strong>overflow1</strong> if you want to try pwn. Have <code>nc</code> (on Windows: <code>ncat</code> from Nmap), CyberChef and your browser's developer tools (F12) ready.</p>
</div>
<div class="info-link">
  <h4 class="ctf-lang" lang="no">
    Alt du trenger å vite står på <a href="/info">infosiden</a>.
  </h4>
  <h4 class="ctf-lang" lang="en">
    Everything you need to know is on the <a href="/info">Info page</a>.
  </h4>
</div>

<script>
// Counts down to the start of the CTF, then to its end. A time that isn't set
// in CTFd is skipped; with neither set the countdown stays hidden.
(function () {
  const start = new Date("{{ ctf_start }}").getTime();
  const end = new Date("{{ ctf_end }}").getTime();
  if (isNaN(start) && isNaN(end)) return;
  const el = (id) => document.getElementById(id);
  const box = el("countdown");
  box.hidden = false;
  let timer = 0;
  const show = (phase) => {
    el("countdown-before").hidden = phase !== "before";
    el("countdown-running").hidden = phase !== "running";
    el("countdown-over").hidden = phase !== "over";
    el("countdown-box").style.display = phase === "over" ? "none" : "";
  };
  const update = () => {
    const now = Date.now();
    // NaN never compares true, so an unset time falls through to the next phase.
    let target;
    if (now < start) {
      show("before");
      target = start;
    } else if (now < end) {
      show("running");
      target = end;
    } else {
      clearInterval(timer);
      // Over, or started with no end set: nothing left to count down to.
      if (isNaN(end)) box.hidden = true;
      else show("over");
      return;
    }
    const distance = target - now;
    // Days only while there are any, so the last day reads as before.
    const days = Math.floor(distance / 86400000);
    el("days-unit").style.display = days ? "" : "none";
    el("days").textContent = days;
    el("hours").textContent = Math.floor((distance % 86400000) / 3600000);
    el("minutes").textContent = Math.floor((distance % 3600000) / 60000);
    el("seconds").textContent = Math.floor((distance % 60000) / 1000);
  };
  timer = setInterval(update, 1000);
  update();
})();
</script>
