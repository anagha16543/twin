// Horizontal grouped bar chart (obtained vs maximum), hand-built SVG.
window.renderMarksChart = function (el, rows, onSelect) {
  const tip = document.getElementById("chartTip");
  const W = Math.max(520, el.clientWidth || 900);
  const labelW = Math.min(190, W * 0.24);
  const rowH = 27, barH = 11, top = 6, bottomAxis = 26;
  const H = top + rows.length * rowH + bottomAxis;
  const plotW = W - labelW - 24;
  const maxVal = Math.max(1, ...rows.map((r) => Math.max(r.max, r.obtained || 0)));
  const domain = maxVal * 1.06;
  const step = maxVal > 15 ? 7 : maxVal > 6 ? 2 : 1;
  const x = (v) => labelW + (v / domain) * plotW;

  const wrap = (text, maxChars) => {
    const words = text.split(" "), lines = [];
    let cur = "";
    words.forEach((w) => {
      if ((cur + " " + w).trim().length > maxChars && cur) { lines.push(cur); cur = w; }
      else cur = (cur + " " + w).trim();
    });
    if (cur) lines.push(cur);
    return lines.slice(0, 2);
  };

  let svg = `<svg width="100%" viewBox="0 0 ${W} ${H}" role="img" aria-label="Criterion 3 marks obtained versus maximum per subcriterion">`;
  for (let t = 0; t <= domain; t += step) {
    const gx = x(t);
    svg += `<line x1="${gx}" x2="${gx}" y1="${top}" y2="${H - bottomAxis}" stroke="#e8e6df" stroke-dasharray="${t === 0 ? "" : "3 4"}"/>`;
    svg += `<text x="${gx}" y="${H - 8}" font-size="11" fill="#7b827e" text-anchor="middle">${t}</text>`;
  }
  rows.forEach((r, i) => {
    const y0 = top + i * rowH + (rowH - barH * 2) / 2;
    const label = `${r.name} (${r.num})`;
    const lines = wrap(label, Math.floor(labelW / 6.6));
    const ly = y0 + barH - (lines.length - 1) * 6;
    svg += `<g class="bar-hit" data-i="${i}">`;
    svg += `<rect x="0" y="${top + i * rowH}" width="${W}" height="${rowH}" fill="transparent"/>`;
    lines.forEach((ln, k) => {
      svg += `<text x="${labelW - 8}" y="${ly + k * 12 + 3}" font-size="10.5" font-weight="600" fill="#2b302d" text-anchor="end">${U.esc(ln)}</text>`;
    });
    const ow = r.obtained == null ? 0 : x(r.obtained) - labelW;
    svg += `<rect class="obt" x="${labelW}" y="${y0}" width="${Math.max(0, ow)}" height="${barH}" rx="2" fill="${r.status === "UNEVALUATED" ? "#cfd5d1" : "#1d5a45"}"/>`;
    svg += `<rect x="${labelW}" y="${y0 + barH}" width="${x(r.max) - labelW}" height="${barH}" rx="2" fill="#e4e3dc"/>`;
    svg += `</g>`;
  });
  svg += `</svg>`;
  el.innerHTML = svg;

  el.querySelectorAll(".bar-hit").forEach((g) => {
    const r = rows[+g.dataset.i];
    g.addEventListener("mousemove", (e) => {
      tip.innerHTML = `<b>${U.esc(r.name)} (${r.num})</b>
        <div class="row"><span class="muted">Obtained</span><span class="spacer"></span><strong>${r.obtained == null ? "Not evaluated" : U.fmtScore(r.obtained)}</strong></div>
        <div class="row"><span class="muted">Maximum</span><span class="spacer"></span><strong>${U.fmtScore(r.max)}</strong></div>
        <div style="margin-top:6px">${U.badge(r.status)}</div>`;
      tip.classList.remove("hidden");
      tip.style.left = Math.min(e.clientX + 14, innerWidth - 220) + "px";
      tip.style.top = e.clientY + 14 + "px";
    });
    g.addEventListener("mouseleave", () => tip.classList.add("hidden"));
    g.addEventListener("click", () => { tip.classList.add("hidden"); onSelect && onSelect(r); });
  });
};
