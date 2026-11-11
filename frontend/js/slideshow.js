// Title slideshow: autoplay, arrows, dots, keyboard, swipe, pause.
(function () {
  hydrateIcons();
  const slides = Array.from(document.querySelectorAll(".slide"));
  const dots = document.getElementById("dots");
  const bar = document.getElementById("bar");
  const DURATION = 6500;
  let idx = 0, start = 0, paused = false, raf = null;

  slides.forEach((_, i) => {
    const b = document.createElement("button");
    b.className = "dot" + (i === 0 ? " active" : "");
    b.setAttribute("role", "tab");
    b.setAttribute("aria-label", "Go to slide " + (i + 1));
    b.onclick = () => go(i, true);
    dots.appendChild(b);
  });

  function go(i, user) {
    idx = (i + slides.length) % slides.length;
    slides.forEach((s, k) => s.classList.toggle("is-active", k === idx));
    Array.from(dots.children).forEach((d, k) => d.classList.toggle("active", k === idx));
    // Stop autoplay on the last slide so the call to action stays visible.
    if (idx === slides.length - 1 && !user) setPaused(true);
    else restart();
  }

  function tick(t) {
    if (paused) return;
    const p = Math.min(1, (t - start) / DURATION);
    bar.style.width = p * 100 + "%";
    if (p >= 1) { go(idx + 1); return; }
    raf = requestAnimationFrame(tick);
  }
  function restart() {
    cancelAnimationFrame(raf);
    start = performance.now();
    bar.style.width = "0%";
    if (!paused) raf = requestAnimationFrame(tick);
  }
  function setPaused(v) {
    paused = v;
    document.getElementById("pauseIcon").textContent = paused ? "▶" : "❚❚";
    document.getElementById("pause").setAttribute("aria-label", paused ? "Resume autoplay" : "Pause autoplay");
    if (paused) { cancelAnimationFrame(raf); bar.style.width = "0%"; } else restart();
  }

  document.getElementById("next").onclick = () => go(idx + 1, true);
  document.getElementById("prev").onclick = () => go(idx - 1, true);
  document.getElementById("pause").onclick = () => setPaused(!paused);

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === "PageDown") go(idx + 1, true);
    else if (e.key === "ArrowLeft" || e.key === "PageUp") go(idx - 1, true);
    else if (e.key === " ") { e.preventDefault(); setPaused(!paused); }
    else if (e.key === "Enter" && idx === slides.length - 1) window.location.href = "login.html";
  });

  let x0 = null;
  document.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) go(idx + (dx < 0 ? 1 : -1), true);
    x0 = null;
  });

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) setPaused(true);
  restart();
})();
