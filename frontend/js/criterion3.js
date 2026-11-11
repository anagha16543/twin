// Criterion 3 workspace — wires the dashboard to the FastAPI backend + AI agents.
(function () {
  const { icon, esc, badge, fmtDateTime, fmtScore, fmtBytes, splitTitle, $, $$, toast } = U;
  const CODE = NBA_CONFIG.CRITERION_CODE;

  if (!API.token.get()) { location.replace("login.html"); return; }
  hydrateIcons();

  // ------------------------------------------------------------------ state
  const S = {
    me: null, ay: null, dept: "", isHod: false,
    criterion: null,
    requirements: [],      // active, weighted C3 requirements (3.1–3.8)
    analytics: null,       // /digital-twin/criteria/CRITERION_3
    documents: [],         // department documents for the AY
    links: {},             // requirement_id -> RequirementEvidence[]
    gaps: [],
    notifications: null,
  };
  const reqById = (id) => S.requirements.find((r) => r.id === id);
  const summaryById = (id) => S.analytics?.requirements.find((r) => r.requirement_id === id);

  // ------------------------------------------------------------------ boot
  async function boot() {
    try {
      const [me, years, criteria] = await Promise.all([API.me(), API.academicYears(), API.criteria()]);
      S.me = me;
      S.ay = years.find((y) => y.is_active) || years[0];
      S.dept = me.faculty_profile?.department || NBA_CONFIG.DEFAULT_DEPARTMENT;
      S.isHod = me.roles.some((r) => r === "HOD" || r === "ADMIN");
      S.criterion = criteria.find((c) => c.code === CODE);
      if (!S.ay) throw new Error("No academic year configured in the backend. Run `python -m app.db.seed`.");
      if (!S.criterion) throw new Error("Criterion 3 is not seeded in the backend. Run `python -m app.db.seed`.");
      renderIdentity();
      const reqs = await API.requirements(S.criterion.id);
      S.requirements = reqs.filter((r) => r.is_active && r.weightage > 0).sort((a, b) => a.display_order - b.display_order);
      await refreshAll();
      loadNotifications();
    } catch (e) {
      $("#content").innerHTML = `<div class="card card-pad"><div class="alert err"><b>Could not load Criterion 3.</b><br>${esc(e.message)}</div>
        <p class="small muted">Check that the backend is running at <span class="code">${esc(NBA_CONFIG.API_BASE)}</span> and that its CORS_ORIGINS includes <span class="code">${esc(location.origin)}</span>.</p></div>`;
    }
  }

  async function refreshAll() {
    const ay = S.ay.id;
    const [analytics, documents, gaps] = await Promise.all([
      API.criterionAnalytics(CODE, S.dept, ay),
      API.documents(S.dept, ay).catch(() => []),
      API.gaps(S.dept, ay, S.criterion.id).catch(() => []),
    ]);
    const linkLists = await Promise.all(S.requirements.map((r) => API.requirementEvidence(r.id).catch(() => [])));
    S.analytics = analytics; S.documents = documents; S.gaps = gaps;
    S.links = {};
    S.requirements.forEach((r, i) => { S.links[r.id] = linkLists[i]; });
    renderDashboard();
    renderEvidence();
    renderGaps();
  }

  // ------------------------------------------------------------------ identity / chrome
  function renderIdentity() {
    const short = U.deptShort(S.dept);
    const p = S.me.faculty_profile;
    $("#sbDept").textContent = `Dept. of ${short}`;
    $("#sbMeta").textContent = `AY ${U.ayLong(S.ay.name)} • Tier-I UG`;
    $("#ctxChip").innerHTML = `${esc(short)} <span class="dot">•</span> AY ${esc(U.ayLong(S.ay.name))}`;
    $("#userName").textContent = p?.full_name || S.me.email;
    $("#userAvatar").textContent = U.initial(p?.full_name || S.me.email);
    $("#userRole").textContent = S.me.roles.includes("HOD") ? "HOD" : S.me.roles[0] || "";
    $("#insightAvatar").textContent = U.initial(p?.full_name || S.me.email);
  }

  // ------------------------------------------------------------------ dashboard
  function rowsForChart() {
    return S.requirements.map((r) => {
      const s = summaryById(r.id);
      const t = splitTitle(r.title);
      return { id: r.id, name: t.name, num: t.num, max: r.weightage, obtained: s?.score_attained ?? null, status: s?.status || "UNEVALUATED" };
    });
  }

  function c3Documents() {
    const linkedIds = new Set(Object.values(S.links).flat().map((l) => l.document_id));
    return S.documents.filter((d) => linkedIds.has(d.id));
  }

  function renderDashboard() {
    const a = S.analytics;
    const rows = rowsForChart();
    const evaluated = rows.filter((r) => r.status !== "UNEVALUATED").length;
    const marks = rows.reduce((s, r) => s + (r.obtained || 0), 0);
    const ready = a.readiness_percentage;
    const docs = c3Documents();
    const verified = docs.filter((d) => d.validation_status === "VALIDATED").length;

    $("#hMax").textContent = `${U.fmtNum(a.max_score)} Marks`;
    $("#hReady").textContent = ready == null ? "—" : `${U.fmtNum(ready)}%`;
    $("#hLast").textContent = fmtDateTime(a.last_evaluation_timestamp);
    $("#kReady").textContent = ready == null ? "Not evaluated" : `${U.fmtNum(ready)}%`;
    $("#kMarks").innerHTML = `${fmtScore(marks)} <small>/ ${U.fmtNum(a.max_score)}</small>`;
    $("#kMarksSub").textContent = `Out of ${fmtScore(a.max_score)} statutory marks`;
    $("#kReqs").textContent = `${evaluated} of ${rows.length}`;
    $("#kEvid").innerHTML = `${verified} <small>of ${docs.length} documents</small>`;

    renderMarksChart($("#chart"), rows, (r) => openEvaluate(r.id));
    renderTable(rows);
    renderInsights(rows);

    const lim = [...(a.limitations || [])];
    $("#limitations").innerHTML = lim.length
      ? `<div class="alert info" style="margin-top:14px">${lim.map(esc).join("<br>")}</div>` : "";
  }

  function renderTable(rows) {
    const head = `<thead><tr><th>Code</th><th>Subcriterion</th><th>Status</th><th>Score</th><th>Evidence</th><th>Last evaluated</th><th></th></tr></thead>`;
    const body = rows.map((r) => {
      const s = summaryById(r.id);
      const pct = r.obtained == null ? 0 : (r.obtained / r.max) * 100;
      const ev = s?.evidence_count || 0;
      return `<tr class="clickable" data-id="${r.id}">
        <td><span class="code">${esc(reqById(r.id).code)}</span></td>
        <td><strong>${esc(r.name)}</strong> <span class="muted small">(${r.num})</span></td>
        <td>${badge(r.status)}</td>
        <td class="score-cell"><strong>${r.obtained == null ? "—" : fmtScore(r.obtained)}</strong> <span class="muted small">/ ${fmtScore(r.max)}</span>
          <div class="progress"><div style="width:${pct}%"></div></div></td>
        <td>${ev ? `<span class="badge PASS">${icon("file", 11)} ${ev} linked</span>` : `<span class="badge FAIL">${icon("alert", 11)} none</span>`}</td>
        <td class="small muted">${fmtDateTime(s?.last_evaluated_at)}</td>
        <td><button class="btn sm" data-eval="${r.id}">${S.isHod ? "Evaluate" : "View"} ${icon("chevRight", 13)}</button></td>
      </tr>`;
    }).join("");
    $("#reqTable").innerHTML = head + `<tbody>${body}</tbody>`;
    $$("#reqTable tr.clickable").forEach((tr) => tr.addEventListener("click", () => openEvaluate(tr.dataset.id)));
  }

  // Insights are derived only from backend statuses and evidence links.
  function renderInsights(rows) {
    const items = [];
    rows.forEach((r) => {
      const s = summaryById(r.id);
      if (["WARNING", "FAIL", "NEEDS_RULE_CLARIFICATION"].includes(r.status))
        items.push({ id: r.id, sev: r.status, text: `${r.num} ${r.name}: ${r.status === "NEEDS_RULE_CLARIFICATION" ? "needs institutional rule configuration" : `${r.status.toLowerCase()} at ${fmtScore(r.obtained)}/${fmtScore(r.max)}`}` });
      else if (r.status === "UNEVALUATED")
        items.push({ id: r.id, sev: "UNEVALUATED", text: `${r.num} ${r.name}: not evaluated for this academic year` });
      if (s && !s.has_evidence && r.status !== "UNEVALUATED")
        items.push({ id: r.id, sev: "WARNING", text: `${r.num} ${r.name}: no evidence document linked` });
    });
    $("#insightLabel").textContent = `${items.length} Insight${items.length === 1 ? "" : "s"}`;
    $("#insightPop").innerHTML = `<div class="row" style="margin-bottom:8px"><strong>Readiness insights</strong><span class="spacer"></span><button class="btn ghost sm" data-close>${icon("x", 14)}</button></div>` +
      (items.length ? items.map((i) => `<div class="row" style="padding:8px 0;border-top:1px solid var(--line);align-items:flex-start;cursor:pointer" data-goto="${i.id}">${badge(i.sev)}<span class="small">${esc(i.text)}</span></div>`).join("")
        : `<div class="small muted">All C3 subcriteria pass with evidence linked.</div>`);
    $$("#insightPop [data-goto]").forEach((el) => el.addEventListener("click", () => { $("#insightPop").classList.add("hidden"); openEvaluate(el.dataset.goto); }));
    $("#insightPop [data-close]").onclick = () => $("#insightPop").classList.add("hidden");
  }

  // ------------------------------------------------------------------ drawers
  function openDrawer(html, onMount) {
    const root = $("#drawerRoot");
    root.innerHTML = `<div class="overlay" data-close></div><aside class="drawer" role="dialog" aria-modal="true">${html}</aside>`;
    hydrateIcons(root);
    $$("[data-close]", root).forEach((el) => el.addEventListener("click", closeDrawer));
    document.addEventListener("keydown", escClose);
    onMount && onMount(root.querySelector(".drawer"));
  }
  function closeDrawer() { $("#drawerRoot").innerHTML = ""; document.removeEventListener("keydown", escClose); }
  function escClose(e) { if (e.key === "Escape") closeDrawer(); }

  // Rule-specific input form. Thresholds shown mirror backend/app/business_rules/criterion3_rules.py.
  function ruleForm(req) {
    const key = req.evaluation_rule_key, max = req.weightage;
    if (key === "criterion3.co_definition_completeness" || key === "criterion3.continuous_assessment") {
      return `<div class="alert info" style="margin-bottom:14px">Scored from live curriculum data: share of subjects with at least one Course Outcome defined. PASS = 100%, WARNING ≥ 80%.</div>
        <div class="row" style="margin-bottom:12px"><button class="btn sm" type="button" id="pullCtx">${icon("refresh", 13)} Pull from Digital Twin</button><span class="small muted" id="ctxInfo"></span></div>
        <div class="grid-2" style="gap:12px">
          <div class="field"><label>Total subjects</label><input class="input" type="number" min="0" name="total_subjects" required /></div>
          <div class="field"><label>Subjects with COs</label><input class="input" type="number" min="0" name="subjects_with_cos" required /></div>
        </div>`;
    }
    if (key === "criterion3.co_attainment_tools" || key === "criterion3.po_pso_attainment") {
      return `<div class="alert info" style="margin-bottom:14px">NBA Tier-I requires an institution-approved direct + indirect attainment method. Without it the engine returns NEEDS_RULE_CLARIFICATION. PASS ≥ ${max * 0.7}, WARNING ≥ ${max * 0.4}.</div>
        <label class="check" style="margin-bottom:14px"><input type="checkbox" name="attainment_formula_configured" /> <span>Institutional attainment formula is configured and approved (IQAC)</span></label>
        <div class="field"><label>Attainment score (0 – ${max})</label><input class="input" type="number" step="0.5" min="0" max="${max}" name="attainment_score" /><span class="hint">Score produced by your approved CO/PO attainment sheet.</span></div>`;
    }
    return `<div class="alert info" style="margin-bottom:14px">Qualitative rubric scored by the reviewer. PASS ≥ ${max * 0.7}, WARNING ≥ ${max * 0.4} (of ${max}).</div>
      <div class="field"><label>Reviewer score (0 – ${max})</label><input class="input" type="number" step="0.5" min="0" max="${max}" name="reviewer_score" required /></div>`;
  }

  function buildContext(form, req) {
    const key = req.evaluation_rule_key;
    const num = (n) => { const v = form.elements[n]?.value; return v === "" || v == null ? null : Number(v); };
    if (key.includes("co_definition_completeness") || key.includes("continuous_assessment"))
      return { total_subjects: num("total_subjects"), subjects_with_cos: num("subjects_with_cos") };
    if (key.includes("attainment")) {
      const ctx = { attainment_formula_configured: form.elements.attainment_formula_configured.checked };
      const s = num("attainment_score"); if (s !== null) ctx.attainment_score = s;
      return ctx;
    }
    const s = num("reviewer_score");
    return s === null ? {} : { reviewer_score: s };
  }

  function evalResultHtml(e) {
    if (!e) return `<div class="empty">No evaluation recorded for ${esc(S.ay.name)} yet.</div>`;
    const metrics = Object.entries(e.deterministic_metrics || {});
    return `<div class="row wrap" style="margin-bottom:10px">${badge(e.status)}<strong style="font-size:18px">${fmtScore(e.score_attained)}</strong><span class="muted">/ ${fmtScore(e.max_score)}</span><span class="spacer"></span><span class="small muted">${fmtDateTime(e.evaluated_at)} · ${esc(e.mode)}</span></div>
      ${metrics.length ? `<dl class="kv">${metrics.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</dd>`).join("")}</dl>` : ""}
      ${(e.limitations || []).length ? `<div class="alert warn" style="margin-top:10px">${e.limitations.map(esc).join("<br>")}</div>` : ""}
      ${e.notes ? `<p class="small muted" style="margin:8px 0 0">Note: ${esc(e.notes)}</p>` : ""}
      ${e.ai_interpretation ? (() => {
        const txt = e.ai_findings?.findings?.[0]?.description || e.ai_interpretation;
        return `<details class="alert ok" style="margin-top:10px"><summary style="cursor:pointer"><b>${icon("sparkles", 13)} AI advisory</b> <span class="small">(advisory only${e.ai_confidence != null ? ` · confidence ${e.ai_confidence}` : ""})</span></summary><div class="small" style="white-space:pre-wrap;margin-top:6px">${esc(txt.slice(0, 1500))}${txt.length > 1500 ? "…" : ""}</div></details>`;
      })() : ""}`;
  }

  async function openEvaluate(reqId) {
    const req = reqById(reqId);
    const t = splitTitle(req.title);
    const s = summaryById(reqId);
    openDrawer(`
      <div class="drawer-head">
        <div><div class="eyebrow">${esc(req.code)} · ${fmtScore(req.weightage)} marks</div><h3 style="margin:4px 0 4px;font-size:18px">${esc(t.name)} (${t.num})</h3>
          <p class="small muted" style="margin:0">${esc(req.description || "")}</p></div>
        <button class="btn ghost sm" data-close aria-label="Close">${icon("x", 16)}</button>
      </div>
      <div class="drawer-body">
        <h4 class="section-title" style="font-size:13px;margin-bottom:10px">Latest result</h4>
        <div id="latest" class="card card-pad" style="padding:14px 16px;margin-bottom:20px"><div class="skeleton" style="height:60px"></div></div>
        ${S.isHod ? `<h4 class="section-title" style="font-size:13px;margin-bottom:10px">Run deterministic evaluation</h4>
        <form id="evalForm" novalidate>${ruleForm(req)}
          <div class="field"><label>Notes (optional)</label><input class="input" name="notes" maxlength="300" placeholder="e.g. Reviewed by IQAC on 10 Nov" /></div>
          <div id="evalMsg"></div>
          <div class="row"><button class="btn primary" type="submit">${icon("play", 13)} Evaluate with rule engine</button>
          <button class="btn" type="button" id="askAi">${icon("sparkles", 14)} Ask AI agents</button></div>
        </form>` : `<div class="alert info">Only HOD or Admin accounts can trigger evaluations.</div>`}
        <div id="aiOut" style="margin-top:16px"></div>
        <h4 class="section-title" style="font-size:13px;margin:22px 0 10px">Evidence linked (${s?.evidence_count || 0})</h4>
        <div id="evList"></div>
        <h4 class="section-title" style="font-size:13px;margin:22px 0 10px">Evaluation history</h4>
        <div id="history"><div class="skeleton" style="height:60px"></div></div>
      </div>
      <div class="drawer-foot"><span class="small muted" style="margin-right:auto">Rule: <span class="code">${esc(req.evaluation_rule_key)}</span></span><button class="btn" data-close>Close</button></div>`,
      async (drawer) => {
        const links = S.links[reqId] || [];
        $("#evList", drawer).innerHTML = links.length ? links.map((l) => {
          const d = S.documents.find((x) => x.id === l.document_id);
          return `<div class="row" style="padding:7px 0;border-bottom:1px solid var(--line)">${icon("file", 15)}<span class="small">${esc(d?.original_filename || l.document_id)}</span><span class="spacer"></span>${d ? badge(d.validation_status) : ""}</div>`;
        }).join("") : `<div class="small muted">No evidence linked. Upload and link documents in the Evidence Repository below.</div>`;

        const loadHistory = async () => {
          const hist = await API.evaluations(reqId, S.dept, S.ay.id, 10).catch(() => []);
          $("#latest", drawer).innerHTML = evalResultHtml(hist[0]);
          $("#history", drawer).innerHTML = hist.length
            ? `<table class="tbl"><thead><tr><th>When</th><th>Status</th><th>Score</th><th>Mode</th></tr></thead><tbody>${hist.map((h) => `<tr><td class="small">${fmtDateTime(h.evaluated_at)}</td><td>${badge(h.status)}</td><td>${fmtScore(h.score_attained)} / ${fmtScore(h.max_score)}</td><td class="small muted">${esc(h.mode)}</td></tr>`).join("")}</tbody></table>`
            : `<div class="small muted">No history yet.</div>`;
          return hist;
        };
        const hist = await loadHistory();

        const form = $("#evalForm", drawer);
        if (!form) return;
        // Pre-fill from the last evaluation's metrics.
        const m = hist[0]?.deterministic_metrics || {};
        Object.entries(m).forEach(([k, v]) => { const f = form.elements[k]; if (f && f.type !== "checkbox") f.value = v; });
        if (form.elements.attainment_formula_configured && hist[0] && hist[0].status !== "NEEDS_RULE_CLARIFICATION" && "attainment_score" in m)
          form.elements.attainment_formula_configured.checked = true;

        const pull = $("#pullCtx", drawer);
        const doPull = async () => {
          $("#ctxInfo", drawer).textContent = "Loading…";
          try {
            const c = await API.c3Context(S.dept, S.ay.id);
            form.elements.total_subjects.value = c.total_subjects;
            form.elements.subjects_with_cos.value = c.subjects_with_cos;
            $("#ctxInfo", drawer).textContent = `${c.total_subjects} subjects · ${c.total_cos} COs · ${c.cos_with_po_map} mapped to POs`;
          } catch (e) { $("#ctxInfo", drawer).textContent = e.message; }
        };
        if (pull) { pull.addEventListener("click", doPull); if (!("total_subjects" in m)) doPull(); }

        form.addEventListener("submit", async (e) => {
          e.preventDefault();
          const btn = form.querySelector("button[type=submit]");
          btn.disabled = true;
          $("#evalMsg", drawer).innerHTML = "";
          try {
            const res = await API.evaluate(reqId, { academic_year_id: S.ay.id, department: S.dept, context: buildContext(form, req), notes: form.elements.notes.value || null });
            toast(`${req.code}: ${res.status} — ${fmtScore(res.score_attained)}/${fmtScore(res.max_score)}`);
            await loadHistory();
            await refreshAll();
          } catch (err) {
            $("#evalMsg", drawer).innerHTML = `<div class="alert err" style="margin-bottom:12px">${esc(err.message)}</div>`;
          } finally { btn.disabled = false; }
        });

        $("#askAi", drawer).addEventListener("click", async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          $("#aiOut", drawer).innerHTML = `<div class="alert info">${icon("loader", 14, "spin")} Assessment, Student and Coordinator agents are analysing ${esc(req.code)}…</div>`;
          try {
            const r = await API.aiAnalysis({ requirement_id: reqId, academic_year_id: S.ay.id, department: S.dept });
            $("#aiOut", drawer).innerHTML = aiResultHtml(r);
            if (r.status === "SUCCESS") await loadHistory();
          } catch (err) {
            $("#aiOut", drawer).innerHTML = `<div class="alert err">${esc(err.message)}</div>`;
          } finally { btn.disabled = false; }
        });
      });
  }

  function aiResultHtml(r) {
    const ok = r.status === "SUCCESS";
    return `<div class="card card-pad" style="padding:14px 16px;border-color:${ok ? "#cde2d6" : "#f0d2cb"}">
      <div class="row" style="margin-bottom:8px"><strong>${icon("sparkles", 14)} AI agent analysis</strong><span class="spacer"></span><span class="badge ${ok ? "PASS" : "FAIL"}">${esc(r.status)}</span></div>
      ${r.summary ? `<p class="small" style="margin:0 0 8px">${esc(r.summary)}</p>` : ""}
      ${(r.findings || []).map((f) => `<div class="msg bot" style="margin-right:0"><span class="badge IDENTIFIED" style="margin-bottom:6px">${esc(f.category)}</span>\n${esc(f.description)}</div>`).join("")}
      ${(r.recommended_actions || []).length ? `<b class="small">Recommended actions</b><ul class="small">${r.recommended_actions.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
      ${(r.limitations || []).length ? `<div class="alert warn small">${r.limitations.map(esc).join("<br>")}</div>` : ""}
      <p class="small muted" style="margin:8px 0 0">Advisory only — AI never changes the deterministic score${r.execution_time_ms != null ? ` · ${r.execution_time_ms} ms` : ""}.</p>
    </div>`;
  }

  // ------------------------------------------------------------------ evidence tab
  function linkedReqsFor(docId) {
    return S.requirements.filter((r) => (S.links[r.id] || []).some((l) => l.document_id === docId));
  }

  function renderEvidence() {
    const docs = S.documents;
    $("#ctEvid").textContent = c3Documents().length;
    const reqOptions = S.requirements.map((r) => `<option value="${r.id}">${esc(splitTitle(r.title).num)} — ${esc(splitTitle(r.title).name)}</option>`).join("");
    $("#tab-evidence").innerHTML = `
      ${S.isHod ? `<div class="dropzone" id="dz">
        <div class="row" style="justify-content:center;margin-bottom:10px">${icon("upload", 18)}<strong>Upload evidence</strong><span class="muted small">PDF, PNG or JPEG · max 25 MB</span></div>
        <div class="row wrap" style="justify-content:center">
          <input type="file" id="fileIn" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" class="input" style="max-width:280px" />
          <select id="linkReq" class="input" style="max-width:300px"><option value="">Link to subcriterion…</option>${reqOptions}</select>
          <button class="btn primary" id="uploadBtn">${icon("upload", 14)} Upload &amp; link</button>
        </div>
        <div class="small muted" style="margin-top:8px">or drag a file onto this box</div>
      </div>` : ""}
      <div style="overflow-x:auto;margin-top:16px">
      ${docs.length ? `<table class="tbl"><thead><tr><th>Document</th><th>Linked to</th><th>Processing</th><th>Verification</th><th>Uploaded</th><th></th></tr></thead><tbody>
        ${docs.map((d) => {
          const linked = linkedReqsFor(d.id);
          return `<tr>
            <td><div class="row">${icon("file", 16)}<div><strong class="small">${esc(d.original_filename)}</strong><div class="small muted">${fmtBytes(d.file_size_bytes)} · v${d.version}</div></div></div></td>
            <td>${linked.length ? linked.map((r) => `<span class="badge LOW">${esc(splitTitle(r.title).num)}</span>`).join(" ")
              : S.isHod ? `<select class="input" style="padding:5px 8px;font-size:12px;min-width:150px" data-link="${d.id}"><option value="">Link…</option>${reqOptions}</select>` : `<span class="muted small">—</span>`}</td>
            <td><span class="small muted">${esc(d.processing_status)}</span></td>
            <td>${badge(d.validation_status)}</td>
            <td class="small muted">${fmtDateTime(d.created_at)}</td>
            <td><div class="row" style="gap:4px;justify-content:flex-end">
              ${S.isHod && d.validation_status !== "VALIDATED" ? `<button class="btn sm" data-verify="${d.id}" title="Mark verified">${icon("check", 13)} Verify</button>` : ""}
              ${S.isHod && d.validation_status !== "REJECTED" ? `<button class="btn sm danger" data-reject="${d.id}" title="Reject">${icon("xCircle", 13)}</button>` : ""}
              <button class="btn sm" data-dl="${d.id}" title="Download">${icon("download", 13)}</button>
            </div></td></tr>`;
        }).join("")}</tbody></table>` : `<div class="empty">No evidence uploaded for ${esc(S.dept)} in ${esc(S.ay.name)}.</div>`}
      </div>`;

    const doUpload = async (file) => {
      if (!file) { toast("Choose a file first", "err"); return; }
      const reqId = $("#linkReq").value;
      const btn = $("#uploadBtn"); btn.disabled = true;
      try {
        const up = await API.upload(file, S.dept, S.ay.id);
        if (reqId) {
          try { await API.linkEvidence(reqId, up.document_id); }
          catch (e) { if (e.status !== 409) throw e; }
        }
        toast(up.is_duplicate ? "Duplicate file — existing document reused" : `Uploaded ${up.original_filename}`);
        await refreshAll();
      } catch (e) { toast(e.message, "err"); } finally { btn.disabled = false; }
    };
    const up = $("#uploadBtn");
    if (up) {
      up.onclick = () => doUpload($("#fileIn").files[0]);
      const dz = $("#dz");
      dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
      dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
      dz.addEventListener("drop", (e) => { e.preventDefault(); dz.classList.remove("drag"); doUpload(e.dataTransfer.files[0]); });
    }
    $$("[data-link]").forEach((sel) => sel.addEventListener("change", async () => {
      if (!sel.value) return;
      try { await API.linkEvidence(sel.value, sel.dataset.link); toast("Evidence linked"); await refreshAll(); }
      catch (e) { toast(e.message, "err"); }
    }));
    const setVal = async (id, st) => {
      try { await API.setValidation(id, st); toast(st === "VALIDATED" ? "Marked as verified" : "Marked as rejected"); await refreshAll(); }
      catch (e) { toast(e.message, "err"); }
    };
    $$("[data-verify]").forEach((b) => (b.onclick = () => setVal(b.dataset.verify, "VALIDATED")));
    $$("[data-reject]").forEach((b) => (b.onclick = () => setVal(b.dataset.reject, "REJECTED")));
    $$("[data-dl]").forEach((b) => (b.onclick = () => API.download(S.documents.find((d) => d.id === b.dataset.dl)).catch((e) => toast(e.message, "err"))));
  }

  // ------------------------------------------------------------------ gaps tab
  function renderGaps() {
    const open = S.gaps.filter((g) => g.status === "IDENTIFIED" || g.status === "IN_PROGRESS");
    $("#ctGaps").textContent = open.length;
    $("#tab-gaps").innerHTML = `
      <div class="row" style="margin-bottom:16px">
        <p class="small muted" style="margin:0">Gaps are generated by the backend from WARNING / FAIL evaluations and missing evidence. Track corrective actions until closure.</p>
        <span class="spacer"></span>
        ${S.isHod ? `<button class="btn primary" id="genGaps">${icon("refresh", 14)} Generate C3 gaps</button>` : ""}
      </div>
      <div id="genMsg">${S.genMsg || ""}</div>
      ${S.gaps.length ? S.gaps.map(gapCard).join("") : `<div class="empty">No gaps recorded for Criterion 3. Run gap generation after evaluating.</div>`}`;

    const gen = $("#genGaps");
    if (gen) gen.onclick = async () => {
      gen.disabled = true;
      try {
        const r = await API.generateGaps(S.dept, S.ay.id, S.criterion.id);
        S.genMsg = `<div class="alert ${r.gaps_created ? "warn" : "ok"}" style="margin-bottom:14px">${r.gaps_created} new gap(s), ${r.gaps_existing} already open · ${r.total_open_gaps} open in total.${r.gaps_created + r.gaps_existing === 0 ? " No WARNING/FAIL evaluations or unevaluated requirements without evidence." : ""}</div>`;
        S.gaps = await API.gaps(S.dept, S.ay.id, S.criterion.id);
        renderGaps();
        setTimeout(() => { S.genMsg = ""; }, 0);
        S.analytics = await API.criterionAnalytics(CODE, S.dept, S.ay.id);
      } catch (e) { toast(e.message, "err"); gen.disabled = false; }
    };
    $$("[data-gap-status]").forEach((sel) => sel.addEventListener("change", async () => {
      try { await API.updateGap(sel.dataset.gapStatus, { status: sel.value }); toast("Gap updated"); S.gaps = await API.gaps(S.dept, S.ay.id, S.criterion.id); renderGaps(); }
      catch (e) { toast(e.message, "err"); }
    }));
    $$("[data-act-status]").forEach((sel) => sel.addEventListener("change", async () => {
      try { await API.updateAction(sel.dataset.actStatus, { status: sel.value }); toast("Action updated"); S.gaps = await API.gaps(S.dept, S.ay.id, S.criterion.id); renderGaps(); }
      catch (e) { toast(e.message, "err"); }
    }));
    $$("form[data-add-action]").forEach((f) => f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = { title: f.elements.title.value.trim(), description: f.elements.description.value.trim(), priority: f.elements.priority.value, due_date: f.elements.due.value ? new Date(f.elements.due.value).toISOString() : null };
      if (body.title.length < 3 || body.description.length < 5) { toast("Title ≥ 3 and description ≥ 5 characters", "err"); return; }
      try { await API.createAction(f.dataset.addAction, body); toast("Corrective action added"); S.gaps = await API.gaps(S.dept, S.ay.id, S.criterion.id); renderGaps(); }
      catch (err) { toast(err.message, "err"); }
    }));
    $$("[data-toggle-add]").forEach((b) => (b.onclick = () => $(`#add-${b.dataset.toggleAdd}`).classList.toggle("hidden")));
  }

  function gapCard(g) {
    const statuses = ["IDENTIFIED", "IN_PROGRESS", "COMPLETED", "CANCELLED"];
    const opt = (cur) => statuses.map((s) => `<option ${s === cur ? "selected" : ""} value="${s}">${U.statusLabel(s)}</option>`).join("");
    return `<div class="card" style="padding:14px 16px;margin-bottom:12px">
      <div class="row wrap">${badge(g.severity)}<span class="code">${esc(g.requirement_code || "")}</span><strong>${esc(g.title)}</strong><span class="spacer"></span>
        ${S.isHod ? `<select class="input" style="width:auto;padding:5px 8px;font-size:12px" data-gap-status="${g.id}">${opt(g.status)}</select>` : badge(g.status)}</div>
      <p class="small" style="margin:8px 0 4px">${esc(g.description)}</p>
      ${g.recommended_action ? `<p class="small muted" style="margin:0 0 8px"><b>Recommended:</b> ${esc(g.recommended_action)}</p>` : ""}
      ${(g.actions || []).map((a) => `<div class="row wrap" style="padding:7px 0;border-top:1px solid var(--line)">${badge(a.priority)}<span class="small"><strong>${esc(a.title)}</strong> — ${esc(a.description)}</span>
          ${a.due_date ? `<span class="small ${a.is_overdue ? "" : "muted"}" style="${a.is_overdue ? "color:var(--red);font-weight:600" : ""}">due ${fmtDateTime(a.due_date).split(",")[0]}${a.is_overdue ? " · overdue" : ""}</span>` : ""}
          <span class="spacer"></span>
          ${S.isHod ? `<select class="input" style="width:auto;padding:4px 8px;font-size:12px" data-act-status="${a.id}">${opt(a.status)}</select>` : badge(a.status)}</div>`).join("")}
      ${S.isHod ? `<button class="btn sm ghost" data-toggle-add="${g.id}" style="margin-top:6px">${icon("plus", 13)} Add corrective action</button>
      <form class="hidden" id="add-${g.id}" data-add-action="${g.id}" style="margin-top:8px">
        <div class="row wrap"><input class="input" name="title" placeholder="Action title" style="flex:2;min-width:180px" />
        <select class="input" name="priority" style="width:auto"><option>HIGH</option><option selected>MEDIUM</option><option>LOW</option></select>
        <input class="input" type="date" name="due" style="width:auto" /></div>
        <div class="row" style="margin-top:8px"><input class="input" name="description" placeholder="What will be done and what evidence will prove it" />
        <button class="btn primary sm" type="submit">Add</button></div>
      </form>` : ""}
    </div>`;
  }

  // ------------------------------------------------------------------ AI assistant (FAB)
  function openAssistant() {
    const reqOptions = S.requirements.map((r) => `<option value="${r.id}">${esc(splitTitle(r.title).num)} — ${esc(splitTitle(r.title).name)}</option>`).join("");
    openDrawer(`
      <div class="drawer-head"><div><div class="eyebrow">Criterion 3</div><h3 style="margin:4px 0 0;font-size:18px">${icon("sparkles", 18)} NBA AI Assistant</h3>
        <p class="small muted" style="margin:4px 0 0">Assessment → Student → Coordinator agents, grounded in backend-verified data and RAG evidence.</p></div>
        <button class="btn ghost sm" data-close aria-label="Close">${icon("x", 16)}</button></div>
      <div class="drawer-body" id="chatLog">
        <div class="msg bot">Pick a subcriterion and run the agent analysis, or search your uploaded evidence. I explain results — I never change marks.</div>
      </div>
      <div class="drawer-foot" style="flex-direction:column;align-items:stretch">
        <div class="row">
          <select class="input" id="aiReq">${reqOptions}</select>
          <button class="btn primary" id="aiRun" ${S.isHod ? "" : "disabled title='HOD/Admin only'"}>${icon("play", 13)} Analyse</button>
        </div>
        <form class="row" id="ragForm"><input class="input" id="ragQ" placeholder="Search evidence, e.g. “CO attainment sheet”" minlength="3" />
          <button class="btn" type="submit">${icon("search", 14)}</button></form>
      </div>`, (drawer) => {
      const log = $("#chatLog", drawer);
      const push = (cls, html) => { const d = document.createElement("div"); d.className = "msg " + cls; d.innerHTML = html; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; };
      $("#aiRun", drawer).onclick = async (e) => {
        const btn = e.currentTarget; const id = $("#aiReq", drawer).value; const r = reqById(id);
        btn.disabled = true;
        push("user", `Analyse ${esc(r.code)} — ${esc(splitTitle(r.title).name)}`);
        const wait = push("bot", `${icon("loader", 14, "spin")} Running agents…`);
        try {
          const res = await API.aiAnalysis({ requirement_id: id, academic_year_id: S.ay.id, department: S.dept });
          wait.outerHTML = `<div style="margin-bottom:10px">${aiResultHtml(res)}</div>`;
        } catch (err) { wait.innerHTML = esc(err.message); } finally { btn.disabled = false; }
      };
      $("#ragForm", drawer).onsubmit = async (e) => {
        e.preventDefault();
        const q = $("#ragQ", drawer).value.trim();
        if (q.length < 3) return;
        push("user", esc(q));
        $("#ragQ", drawer).value = "";
        const wait = push("bot", `${icon("loader", 14, "spin")} Searching evidence…`);
        try {
          const r = await API.retrieve({ query: q, top_k: 5, department: S.dept, academic_year_id: S.ay.id });
          wait.innerHTML = r.results.length
            ? `<b>${r.total} passage(s)</b>${r.embedding_available ? "" : " <span class='muted small'>(embeddings unavailable — recency order)</span>"}` +
              r.results.map((m) => `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--line)"><span class="code">${esc(m.document_name)} · p.${m.page_number}</span>${m.similarity_score != null ? ` <span class="small muted">sim ${m.similarity_score.toFixed(2)}</span>` : ""}<div class="small">${esc(m.content.slice(0, 320))}${m.content.length > 320 ? "…" : ""}</div></div>`).join("")
            : "No matching evidence passages. Upload and process documents first.";
        } catch (err) { wait.innerHTML = esc(err.message); }
      };
    });
  }

  // ------------------------------------------------------------------ notifications
  async function loadNotifications() {
    try { S.notifications = await API.notifications(); } catch { S.notifications = { unread_count: 0, notifications: [] }; }
    const n = S.notifications.unread_count;
    $("#bellCount").textContent = n;
    $("#bellCount").classList.toggle("hidden", !n);
    const list = S.notifications.notifications;
    $("#notifPop").innerHTML = `<div class="row" style="padding:12px 14px;border-bottom:1px solid var(--line)"><strong>Notifications</strong><span class="spacer"></span>${n ? `<button class="btn sm ghost" id="readAll">Mark all read</button>` : ""}</div>
      <div style="max-height:360px;overflow-y:auto">${list.length ? list.map((x) => `<div style="padding:10px 14px;border-bottom:1px solid var(--line);${x.is_read ? "opacity:.6" : ""}"><div class="small"><strong>${esc(x.title)}</strong></div><div class="small muted">${esc(x.message)}</div><div class="small muted" style="margin-top:3px">${fmtDateTime(x.created_at)}</div></div>`).join("") : `<div class="empty">You're all caught up.</div>`}</div>`;
    const ra = $("#readAll");
    if (ra) ra.onclick = async () => { await API.markAllRead().catch(() => {}); loadNotifications(); };
  }

  // ------------------------------------------------------------------ events
  const togglePop = (id) => { const el = $(id); el.classList.toggle("hidden"); };
  $("#bellBtn").onclick = (e) => { e.stopPropagation(); togglePop("#notifPop"); };
  $("#navNotif").onclick = (e) => { e.stopPropagation(); $("#notifPop").classList.remove("hidden"); };
  $("#insightBtn").onclick = (e) => { e.stopPropagation(); togglePop("#insightPop"); };
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#notifPop, #bellBtn, #navNotif")) $("#notifPop").classList.add("hidden");
    if (!e.target.closest("#insightPop, #insightBtn")) $("#insightPop").classList.add("hidden");
  });
  $("#logoutBtn").onclick = () => { API.token.clear(); location.replace("login.html"); };
  $("#aiFab").onclick = () => S.criterion && openAssistant();
  $("#refreshBtn").onclick = async () => { try { await refreshAll(); toast("Refreshed from backend"); } catch (e) { toast(e.message, "err"); } };
  $("#criteriaToggle").onclick = () => {
    const l = $("#criteriaList"); l.classList.toggle("hidden");
    $("#criteriaToggle").setAttribute("aria-expanded", String(!l.classList.contains("hidden")));
  };
  $$(".tab").forEach((t) => t.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
    $("#tab-evidence").classList.toggle("hidden", t.dataset.tab !== "evidence");
    $("#tab-gaps").classList.toggle("hidden", t.dataset.tab !== "gaps");
  }));
  let rt;
  window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => S.analytics && renderMarksChart($("#chart"), rowsForChart(), (r) => openEvaluate(r.id)), 150); });

  boot();
})();
