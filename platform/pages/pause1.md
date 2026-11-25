<!--
  The break page (route "pause1"), synced into CTFd by ./ctf.sh up (see
  docs/language.md). The imported backup keeps it hidden; show it in Admin ->
  Pages when the pizza break starts. One file for both languages, like the front
  page: its countdown script must run once, so each text is a block per language
  (class="ctf-lang"). The break ends at BREAK_ENDS in the script; change the
  "18:00" in the text with it.
-->
<style>
  .pause-page {
    text-align: center;
    padding: 10vh 0 20px;
  }
  .pause-page h2 {
    font-size: clamp(2rem, 9vw, 3.5rem);
  }
  /* One row at any width: the digits shrink with the screen instead of wrapping. */
  #pause-box {
    display: inline-flex;
    flex-wrap: nowrap;
    justify-content: center;
    gap: clamp(0.75rem, 4vw, 1.5rem);
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
    font-size: clamp(3rem, 16vw, 5rem);
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
    color: #B5E853;
  }
  .label {
    font-size: 0.8em;
    color: #B5E853;
  }
  .pause-close {
    font-size: clamp(1.25rem, 5vw, 2rem);
  }
</style>

<div class="pause-page">
  <h2 id="pause-title">
    <span class="ctf-lang" lang="no">Tvungen pause</span><span class="ctf-lang" lang="en">Forced break</span>
  </h2>
  <h2 id="pause-over" hidden>
    <span class="ctf-lang" lang="no">Kjør på! 🚩</span><span class="ctf-lang" lang="en">Let's go! 🚩</span>
  </h2>
  <div id="pause-running">
    <p class="pause-close">
      <span class="ctf-lang" lang="no">Lukk PC-ene</span><span class="ctf-lang" lang="en">Close your computers</span>
    </p>
    <p>
      <span class="ctf-lang" lang="no">Vi starter igjen kl. 18:00</span><span class="ctf-lang" lang="en">We start again at 18:00</span>
    </p>
    <div id="pause-box">
      <span class="time-unit" id="hours-unit" style="display: none">
        <span id="hours" class="number"></span>
        <span class="label"><span class="ctf-lang" lang="no">t</span><span class="ctf-lang" lang="en">h</span></span>
      </span>
      <span class="time-unit">
        <span id="minutes" class="number"></span>
        <span class="label">min</span>
      </span>
      <span class="time-unit">
        <span id="seconds" class="number"></span>
        <span class="label"><span class="ctf-lang" lang="no">sek</span><span class="ctf-lang" lang="en">sec</span></span>
      </span>
    </div>
  </div>
</div>

<script>
// Counts down to the end of the break, then says it's time to hack again.
(function () {
  // The end of the break, with Oslo's offset in November written out.
  const BREAK_ENDS = new Date("2026-11-18T18:00:00+01:00").getTime();
  const el = (id) => document.getElementById(id);
  const two = (n) => String(n).padStart(2, "0");
  let timer = 0;
  const update = () => {
    const distance = BREAK_ENDS - Date.now();
    if (!(distance > 0)) {
      clearInterval(timer);
      el("pause-title").hidden = true;
      el("pause-running").hidden = true;
      el("pause-over").hidden = false;
      return;
    }
    // Hours only while there are any: the break itself is half an hour.
    const hours = Math.floor(distance / 3600000);
    el("hours-unit").style.display = hours ? "" : "none";
    el("hours").textContent = hours;
    el("minutes").textContent = two(Math.floor((distance % 3600000) / 60000));
    el("seconds").textContent = two(Math.floor((distance % 60000) / 1000));
  };
  timer = setInterval(update, 1000);
  update();
})();
</script>
