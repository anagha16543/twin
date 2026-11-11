// Criterion 3 pages: dashboard, sub-criterion workspace (3.1-3.8), courses & marks, attainment.
(function () {
  const { icon, esc, badge, fmtDateTime, fmtScore, fmtBytes, splitTitle, $, $$, toast } = U;
  const S = App.S;
  const lvl = (v, target) => v == null ? `<span class="lv na">—</span>` : `<span class="lv ${target == null ? "" : v >= target ? "ok" : "bad"}">${Number(v).toFixed(2)}</span>`;

  async function evidenceState() {
    const [docs, ...links] = await Promise.all([
      API.documents(S.dept, S.ay.id).catch(() => []),
      ...S.requirements.map((r) => API.requirementEvidence(r.id).catch(() => [])),
    ]);
    const byReq = {}; S.requirements.forEach((r, i) => { byReq[r.id] = links[i]; });
    const linkedIds = new Set(links.flat().map((l) => l.document_id));
    const c3docs = docs.filter((d) => linkedIds.has(d.id));
    return { docs, byReq, c3docs, verified: c3docs.filter((d) => d.validation_status === "VALIDATED").length };
  }
  App.evidenceState = evidenceState;

  // ==================================================================== DASHBOARD
  App.pages.dashboard = async (view) => {
    const [ev, courses, cfg, scores, att, surveys] = await Promise.all([
      evidenceState(), API.c3Courses(S.dept, S.ay.id), API.c3Config(S.dept, S.ay.id),
      API.c3RubricScores(S.dept, S.ay.id), API.c3Attainment(S.dept, S.ay.id), API.c3PoIndirect(S.dept, S.ay.id),
    ]);
    const a = S.analytics;
    const rows = S.requirements.map((r) => {
      const s = App.summary(r.id), t = splitTitle(r.title);
      return { id: r.id, rubric: r.rubric, code: r.code, name: t.name, num: t.num, max: r.weightage, obtained: s?.score_attained ?? null, status: s?.status || "UNEVALUATED", s };
    });
    const evaluated = rows.filter((r) => r.status !== "UNEVALUATED").length;
    const marks = rows.reduce((t, r) => t + (r.obtained || 0), 0);
    const ready = a.readiness_percentage;

    const reviewerTotal = Object.values(S.rubric).reduce((t, rb) => t + rb.components.filter((c) => c.kind === "reviewer").length, 0);
    const reviewerDone = Object.entries(S.rubric).reduce((t, [code, rb]) => t + rb.components.filter((c) => c.kind === "reviewer" && scores[code]?.[c.key]).length, 0);
    const withMaps = courses.filter((c) => c.mapping_count > 0).length;
    const withMarks = courses.filter((c) => c.students_with_marks > 0).length;
    const withSurvey = courses.filter((c) => c.co_count && c.indirect_entries >= c.co_count).length;
    const reqWithEv = rows.filter((r) => r.s?.has_evidence).length;
    const step = (done, warn, ico, title, sub, href) =>
      `<a class="pipe-step ${done ? "done" : warn ? "warn" : ""}" href="${href}"><span class="ico">${icon(done ? "check" : ico, 14)}</span><div><b>${title}</b><span>${sub}</span></div></a>`;
    const pipeline = [
      step(courses.length > 0, false, "plus", "1. Courses", `${courses.length} course(s) created`, "#/courses"),
      step(courses.length && withMaps === courses.length, withMaps > 0, "link", "2. CO-PO matrix", `${withMaps}/${courses.length} courses mapped`, "#/courses"),
      step(courses.length && withMarks === courses.length, withMarks > 0, "upload", "3. Marks uploaded", `${withMarks}/${courses.length} courses · question→CO`, "#/courses"),
      step(cfg.is_approved, false, "settings", "4. Attainment levels", cfg.is_approved ? "Methodology approved" : "Approve methodology", "#/settings"),
      step(withSurvey === courses.length && courses.length && surveys.length, withSurvey > 0 || surveys.length, "user", "5. Surveys", `Exit ${withSurvey}/${courses.length} · PO surveys ${surveys.length}`, "#/attainment"),
      step(reviewerDone === reviewerTotal, reviewerDone > 0, "award", "6. Rubric scoring", `${reviewerDone}/${reviewerTotal} reviewer items`, "#/c3/3.1"),
      step(reqWithEv === rows.length, reqWithEv > 0, "file", "7. Evidence", `${reqWithEv}/${rows.length} sub-criteria · ${ev.verified} verified`, "#/evidence"),
      step(evaluated === rows.length, evaluated > 0, "play", "8. Evaluate C3", a.last_evaluation_timestamp ? `Last run ${fmtDateTime(a.last_evaluation_timestamp)}` : "Not run yet", "#/inspection"),
    ].join("");

    const sm = att.summary;
    view.innerHTML = `
      <section class="card card-pad h-card">
        <div>
          <div class="eyebrow">Tier-I Accreditation Core Criterion</div>
          <h1 class="h-title">Teaching-Learning and Assessment</h1>
          <p class="h-desc">Evaluation of course delivery, internal assessments, rubrics, attainment of Course Outcomes (COs) and Program Outcomes (POs).</p>
          ${S.isHod ? `<div class="row" style="margin-top:14px"><button class="btn primary" id="runBtn">${icon("play", 13)} Run Criterion 3 evaluation</button><a class="btn" href="#/courses">${icon("upload", 13)} Upload marks</a></div>` : ""}
        </div>
        <div class="h-pills">
          <div class="h-pill"><div class="lbl">Maximum Marks</div><div class="val">${U.fmtNum(a.max_score)} Marks</div></div>
          <div class="h-pill green"><div class="lbl">Readiness</div><div class="val">${ready == null ? "—" : U.fmtNum(ready) + "%"}</div></div>
          <div class="h-pill"><div class="lbl">${icon("clock", 12)}Last Evaluated</div><div class="val">${fmtDateTime(a.last_evaluation_timestamp)}</div></div>
        </div>
      </section>

      <section class="kpis">
        <a class="card kpi" href="#/inspection" style="text-decoration:none;color:inherit"><div class="kpi-head">Readiness ${icon("shield", 20)}</div><div class="kpi-val">${ready == null ? "Not evaluated" : U.fmtNum(ready) + "%"}</div><div class="kpi-sub">Statutory C3 compliance indicator</div></a>
        <a class="card kpi" href="#/c3/3.7" style="text-decoration:none;color:inherit"><div class="kpi-head">Evaluated Marks ${icon("award", 20)}</div><div class="kpi-val green">${fmtScore(marks)} <small>/ ${U.fmtNum(a.max_score)}</small></div><div class="kpi-sub">Out of ${fmtScore(a.max_score)} statutory marks</div></a>
        <a class="card kpi" href="#/c3/3.1" style="text-decoration:none;color:inherit"><div class="kpi-head">Requirements Evaluated ${icon("layers", 20)}</div><div class="kpi-val">${evaluated} of ${rows.length}</div><div class="kpi-sub">Subcriteria evaluated in C3</div></a>
        <a class="card kpi" href="#/evidence" style="text-decoration:none;color:inherit"><div class="kpi-head">Verified Evidence ${icon("checkCircle", 20)}</div><div class="kpi-val green">${ev.verified} <small>of ${ev.c3docs.length} documents</small></div><div class="kpi-sub">Verified by Department HOD</div></a>
      </section>

      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">C3 Subcriteria Marks Distribution (Obtained vs Maximum)</h2>
          <p class="section-sub">Official NBA mark allocations based on deterministic rule execution — click a bar to open the sub-criterion</p></div></div>
        <div class="chart-wrap" id="chart"></div>
        <div class="chart-legend"><span><i style="background:var(--green-700)"></i>Marks Obtained</span><span><i style="background:var(--bar-max)"></i>Maximum Marks</span></div>
      </section>

      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Criterion 3 pipeline</h2><p class="section-sub">Collect → Store → Check → Analyze → Fix → Prove. Each step opens the page where it is done.</p></div></div>
        <div class="pipeline">${pipeline}</div>
      </section>

      <div class="grid-2">
        <section class="card card-pad">
          <div class="section-head"><div><h2 class="section-title">Subcriteria</h2><p class="section-sub">Rubric per NBA Tier-I 2026 Annexure VII</p></div></div>
          <table class="tbl"><thead><tr><th>Sub-criterion</th><th>Status</th><th>Score</th></tr></thead><tbody>
            ${rows.map((r) => `<tr class="clickable" data-href="#/c3/${r.rubric}"><td><strong>${r.num}</strong> ${esc(r.name)}</td><td>${badge(r.status)}</td>
              <td class="score-cell"><strong>${r.obtained == null ? "—" : fmtScore(r.obtained)}</strong> <span class="muted small">/ ${fmtScore(r.max)}</span><div class="progress"><div style="width:${r.obtained == null ? 0 : r.obtained / r.max * 100}%"></div></div></td></tr>`).join("")}
          </tbody></table>
        </section>
        <section class="card card-pad">
          <div class="section-head"><div><h2 class="section-title">Outcome attainment</h2><p class="section-sub">Computed from uploaded marks · target CO level ${cfg.co_target_level}</p></div><a class="btn sm" href="#/attainment">Open ${icon("chevRight", 13)}</a></div>
          <div class="grid-2" style="gap:12px">
            <div class="mini-kpi"><div class="l">COs meeting target</div><div class="v">${sm.cos_assessed ? `${sm.cos_met}/${sm.cos_assessed}` : "—"}</div></div>
            <div class="mini-kpi"><div class="l">Avg CO level</div><div class="v">${sm.avg_co_level ?? "—"} <small class="muted">/ 3</small></div></div>
            <div class="mini-kpi"><div class="l">POs/PSOs meeting target</div><div class="v">${sm.pos_total ? `${sm.pos_met}/${sm.pos_total}` : "—"}</div></div>
            <div class="mini-kpi"><div class="l">Avg PO/PSO level</div><div class="v">${sm.avg_po_level ?? "—"} <small class="muted">/ 3</small></div></div>
          </div>
          <h4 class="small" style="margin:16px 0 6px">Weak COs (below target)</h4>
          ${sm.weak_cos.length ? sm.weak_cos.map((w) => `<a href="#/attainment" class="row" style="padding:6px 0;border-top:1px solid var(--line);text-decoration:none;color:inherit"><span class="badge FAIL">${esc(w.course)} ${esc(w.code)}</span><span class="small">level ${w.final} vs target ${w.target}</span></a>`).join("")
            : `<div class="small muted">${sm.cos_assessed ? "None — every assessed CO meets its target." : "Upload marks to compute CO attainment."}</div>`}
          ${att.limitations.length ? `<div class="alert info small" style="margin-top:12px">${att.limitations.map(esc).join("<br>")}</div>` : ""}
        </section>
      </div>`;
    renderMarksChart($("#chart"), rows, (r) => { location.hash = `#/c3/${r.rubric}`; });
    $$("tr[data-href]", view).forEach((tr) => tr.addEventListener("click", () => { location.hash = tr.dataset.href; }));
    const run = $("#runBtn", view);
    if (run) run.onclick = async () => { if (await App.runC3(run)) App.rerender(); };
    window.onresize = () => { const c = $("#chart"); if (c) renderMarksChart(c, rows, (r) => { location.hash = `#/c3/${r.rubric}`; }); };
  };

  // ==================================================================== SUB-CRITERION
  App.pages.sub = async (view, code, setTitle) => {
    const req = App.reqByCode(code);
    if (!req) { view.innerHTML = `<div class="card card-pad"><div class="alert err">Unknown sub-criterion ${esc(code)}.</div></div>`; return; }
    const rb = S.rubric[code];
    const t = splitTitle(req.title);
    setTitle(`${code} ${rb.title}`);
    const [hist, scores, ev, att] = await Promise.all([
      API.evaluations(req.id, S.dept, S.ay.id, 10).catch(() => []),
      API.c3RubricScores(S.dept, S.ay.id), evidenceState(),
      code === "3.7" || code === "3.8" ? API.c3Attainment(S.dept, S.ay.id) : Promise.resolve(null),
    ]);
    const latest = hist[0];
    const comps = latest?.deterministic_metrics?.components || {};
    const supporting = latest?.deterministic_metrics?.supporting_metrics || {};
    const mine = scores[code] || {};
    const links = ev.byReq[req.id] || [];

    const compRows = rb.components.map((c) => {
      const isComp = c.kind === "computed";
      const cur = isComp ? comps[c.key]?.score : mine[c.key]?.score;
      return `<div class="rubric-row">
        <div class="rubric-key ${isComp ? "computed" : ""}">${c.key}</div>
        <div><div class="kind ${c.kind}">${isComp ? "Computed from uploaded data" : "Reviewer score (from evidence)"}</div>
          <div style="font-weight:600;margin:3px 0">${esc(c.label)}</div>
          <div class="small muted">Exhibit: ${esc(c.exhibit)}</div>
          ${isComp ? `<div class="small" style="margin-top:4px"><span class="code">${esc(c.formula)}</span></div>` : ""}</div>
        <div>${isComp
          ? `<div class="score-big">${cur == null ? "—" : fmtScore(cur)} <small>/ ${fmtScore(c.max)}</small></div>`
          : S.isHod ? `<label class="small muted">Score (0–${fmtScore(c.max)})</label><input class="input" type="number" step="0.5" min="0" max="${c.max}" data-score="${c.key}" value="${cur ?? ""}" />`
            : `<div class="score-big">${cur == null ? "—" : fmtScore(cur)} <small>/ ${fmtScore(c.max)}</small></div>`}</div>
        <div>${isComp ? `<span class="small muted">Recomputed on every Criterion 3 run.</span>` : S.isHod
          ? `<label class="small muted">Evidence note</label><input class="input" data-note="${c.key}" maxlength="300" placeholder="e.g. QP scrutiny minutes, p.4" value="${esc(mine[c.key]?.note || "")}" />`
          : `<span class="small muted">${esc(mine[c.key]?.note || "")}</span>`}</div>
      </div>`;
    }).join("");

    const supportKv = Object.entries(supporting).filter(([, v]) => v !== null && v !== undefined && !(Array.isArray(v) && !v.length));
    view.innerHTML = `
      <section class="card card-pad h-card">
        <div><div class="eyebrow">${esc(req.code)} · ${fmtScore(req.weightage)} marks · Rubric: NBA Tier-I 2026 Annexure VII</div>
          <h1 class="h-title">${esc(code)} ${esc(rb.title)}</h1>
          <p class="h-desc">${esc(req.description || "")}</p>
          <div class="row wrap" style="margin-top:14px">
            ${S.isHod ? `<button class="btn primary" id="runBtn">${icon("play", 13)} Run Criterion 3 evaluation</button>` : ""}
            <button class="btn" id="aiBtn">${icon("sparkles", 13)} Ask AI agents</button>
            ${code === "3.7" || code === "3.8" ? `<a class="btn" href="#/attainment">${icon("target", 13)} Attainment tables</a>` : ""}
          </div></div>
        <div class="h-pills">
          <div class="h-pill ${latest?.status === "PASS" ? "green" : ""}"><div class="lbl">Status</div><div class="val">${badge(latest?.status || "UNEVALUATED")}</div></div>
          <div class="h-pill"><div class="lbl">Score</div><div class="val">${latest ? `${fmtScore(latest.score_attained)} / ${fmtScore(latest.max_score)}` : "—"}</div></div>
          <div class="h-pill"><div class="lbl">${icon("clock", 12)}Last Evaluated</div><div class="val">${fmtDateTime(latest?.evaluated_at)}</div></div>
        </div>
      </section>

      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Rubric components</h2>
          <p class="section-sub">Blue items are calculated by the backend from marks / mapping and cannot be typed in. Green items are scored by the reviewer from course-file evidence.</p></div>
          ${S.isHod && rb.components.some((c) => c.kind === "reviewer") ? `<button class="btn primary" id="saveBtn">${icon("check", 13)} Save &amp; re-evaluate</button>` : ""}</div>
        <div id="rubricMsg"></div>
        ${compRows}
      </section>

      <div class="grid-2">
        <section class="card card-pad">
          <div class="section-head"><div><h2 class="section-title">Evidence for ${esc(code)}</h2><p class="section-sub">${links.length} linked document(s)</p></div></div>
          ${links.length ? links.map((l) => { const d = ev.docs.find((x) => x.id === l.document_id); return `<div class="row" style="padding:8px 0;border-bottom:1px solid var(--line)">${icon("file", 15)}<span class="small">${esc(d?.original_filename || l.document_id)}</span><span class="spacer"></span>${d ? badge(d.validation_status) : ""}</div>`; }).join("")
            : `<div class="alert warn small">No evidence linked. NBA evaluators verify each rubric item against course-file documents.</div>`}
          ${S.isHod ? `<div class="row wrap" style="margin-top:12px"><input type="file" id="evFile" class="input" accept=".pdf,.png,.jpg,.jpeg" style="max-width:260px" /><button class="btn" id="evUpload">${icon("upload", 13)} Upload &amp; link</button></div>` : ""}
        </section>
        <section class="card card-pad">
          <div class="section-head"><div><h2 class="section-title">Latest evaluation</h2><p class="section-sub">Computed by the deterministic rule engine</p></div></div>
          ${latest ? `${supportKv.length ? `<dl class="kv">${supportKv.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(Array.isArray(v) ? v.join(", ") : v)}</dd>`).join("")}</dl>` : ""}
            ${(latest.limitations || []).length ? `<div class="alert warn small" style="margin-top:10px">${latest.limitations.map(esc).join("<br>")}</div>` : `<div class="alert ok small" style="margin-top:10px">No limitations reported.</div>`}`
            : `<div class="empty">Not evaluated yet. ${S.isHod ? "Click <b>Run Criterion 3 evaluation</b>." : ""}</div>`}
          <div id="aiOut" style="margin-top:12px"></div>
        </section>
      </div>

      ${att ? attainmentMini(code, att) : ""}

      <section class="card card-pad">
        <h2 class="section-title" style="margin-bottom:12px">Evaluation history</h2>
        ${hist.length ? `<table class="tbl"><thead><tr><th>When</th><th>Status</th><th>Score</th><th>Notes</th></tr></thead><tbody>${hist.map((h) => `<tr><td class="small">${fmtDateTime(h.evaluated_at)}</td><td>${badge(h.status)}</td><td>${fmtScore(h.score_attained)} / ${fmtScore(h.max_score)}</td><td class="small muted">${esc(h.notes || "")}</td></tr>`).join("")}</tbody></table>` : `<div class="small muted">No history yet.</div>`}
      </section>`;

    const run = $("#runBtn", view);
    if (run) run.onclick = async () => { if (await App.runC3(run)) App.rerender(); };
    $("#aiBtn", view).onclick = async (e) => {
      const b = e.currentTarget; b.disabled = true;
      $("#aiOut", view).innerHTML = `<div class="alert info small">${icon("loader", 14, "spin")} Agents are analysing ${esc(code)}…</div>`;
      try { $("#aiOut", view).innerHTML = App.aiResultHtml(await API.aiAnalysis({ requirement_id: req.id, academic_year_id: S.ay.id, department: S.dept })); }
      catch (err) { App.showError(err, $("#aiOut", view)); } finally { b.disabled = false; }
    };
    const save = $("#saveBtn", view);
    if (save) save.onclick = async () => {
      const payload = {};
      $$("[data-score]", view).forEach((inp) => {
        const k = inp.dataset.score, note = $(`[data-note="${k}"]`, view)?.value || null;
        payload[k] = { score: inp.value === "" ? null : Number(inp.value), note };
      });
      save.disabled = true;
      try {
        await API.c3SaveRubric(code, S.dept, S.ay.id, payload);
        await App.runC3();
        App.rerender();
      } catch (err) { App.showError(err, $("#rubricMsg", view)); save.disabled = false; }
    };
    const up = $("#evUpload", view);
    if (up) up.onclick = async () => {
      const f = $("#evFile", view).files[0]; if (!f) { toast("Choose a file first", "err"); return; }
      up.disabled = true;
      try {
        const r = await API.upload(f, S.dept, S.ay.id);
        try { await API.linkEvidence(req.id, r.document_id); } catch (e) { if (e.status !== 409) throw e; }
        toast(`Linked ${r.original_filename} to ${code}`); await App.refreshAnalytics(); App.rerender();
      } catch (e) { App.showError(e); up.disabled = false; }
    };
  };

  function attainmentMini(code, att) {
    if (code === "3.7") {
      const rows = att.courses.flatMap((c) => c.cos.map((co) => ({ ...co, course: c.code })));
      return `<section class="card card-pad"><div class="section-head"><div><h2 class="section-title">3.7.2 CO attainment of all courses</h2><p class="section-sub">Target level ${att.config.co_target_level} · ${att.summary.cos_met ?? 0}/${att.summary.cos_assessed} COs meet target</p></div><a class="btn sm" href="#/attainment">Details ${icon("chevRight", 13)}</a></div>
        ${rows.length ? `<div style="overflow-x:auto"><table class="matrix"><thead><tr><th class="l">Course</th><th>CO</th><th>Direct</th><th>Indirect</th><th>Final</th><th>Met</th></tr></thead><tbody>
        ${rows.map((r) => `<tr><td class="l">${esc(r.course)}</td><td>${esc(r.code)}</td><td>${lvl(r.direct)}</td><td>${lvl(r.indirect)}</td><td>${lvl(r.final, r.target)}</td><td>${r.assessed ? (r.met ? "✓" : "✗") : "—"}</td></tr>`).join("")}</tbody></table></div>` : `<div class="small muted">No marks uploaded yet.</div>`}</section>`;
    }
    const p = att.po;
    return `<section class="card card-pad"><div class="section-head"><div><h2 class="section-title">Table 3.8.3 — Overall PO/PSO attainment</h2><p class="section-sub">Target level ${p.target}</p></div><a class="btn sm" href="#/attainment">Details ${icon("chevRight", 13)}</a></div>
      ${p.codes.length ? `<div style="overflow-x:auto"><table class="matrix"><thead><tr><th class="l">Assessment</th>${p.codes.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>
      <tr><td class="l">Direct</td>${p.codes.map((c) => `<td>${lvl(p.direct[c])}</td>`).join("")}</tr>
      <tr><td class="l">Indirect</td>${p.codes.map((c) => `<td>${lvl(p.indirect[c])}</td>`).join("")}</tr>
      <tr class="total"><td class="l">Overall</td>${p.codes.map((c) => `<td>${lvl(p.overall[c], p.target)}</td>`).join("")}</tr></tbody></table></div>` : `<div class="small muted">Upload marks and the CO-PO matrix first.</div>`}</section>`;
  }

  // ==================================================================== COURSES & MARKS
  App.pages.courses = async (view) => {
    const courses = await API.c3Courses(S.dept, S.ay.id);
    view.innerHTML = `
      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">How data flows into Criterion 3</h2>
          <p class="section-sub">Question papers → question-to-CO mapping → student marks → CO attainment → PO/PSO attainment → 3.1 / 3.7 / 3.8 scores</p></div></div>
        <div class="pipeline">
          <div class="pipe-step"><span class="ico">1</span><div><b>Create the course</b><span>code, name, semester</span></div></div>
          <div class="pipe-step"><span class="ico">2</span><div><b>Upload CO-PO matrix</b><span>CSV: CO, Description, PO1…PO11, PSO1… (1/2/3)</span></div></div>
          <div class="pipe-step"><span class="ico">3</span><div><b>Upload marks</b><span>header <span class="code">CIE-I Q1|CO1|10</span>, SEE columns start with "SEE"</span></div></div>
          <div class="pipe-step"><span class="ico">4</span><div><b>Course exit survey</b><span>% students agreeing each CO was achieved</span></div></div>
        </div>
        <p class="small muted" style="margin:12px 0 0">Sample files are in the project's <span class="code">sample_data/</span> folder. Re-uploading a marks file replaces the marks for the same students and questions (use it for re-assessment after remedial classes).</p>
      </section>
      ${S.isHod ? `<section class="card card-pad"><h2 class="section-title" style="margin-bottom:12px">Add a course</h2>
        <form id="addCourse" class="row wrap">
          <input class="input" name="code" placeholder="Code e.g. 22UAI608C" style="max-width:180px" required />
          <input class="input" name="name" placeholder="Course name" style="max-width:300px" required />
          <input class="input" name="semester" type="number" min="1" max="10" placeholder="Sem" style="max-width:90px" required />
          <input class="input" name="credits" type="number" min="1" max="10" step="0.5" value="3" style="max-width:90px" />
          <button class="btn primary" type="submit">${icon("plus", 13)} Add course</button>
        </form><div id="addMsg"></div></section>` : ""}
      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Courses — ${esc(S.ay.name)}</h2><p class="section-sub">${courses.length} course(s)</p></div>
          ${S.isHod ? `<button class="btn primary" id="runBtn">${icon("play", 13)} Run Criterion 3 evaluation</button>` : ""}</div>
        <div id="courseList">${courses.length ? courses.map(courseCard).join("") : `<div class="empty">No courses yet. Add one above, then upload its CO-PO matrix and marks.</div>`}</div>
      </section>`;

    const add = $("#addCourse", view);
    if (add) add.onsubmit = async (e) => {
      e.preventDefault();
      const f = add.elements;
      try {
        await API.c3CreateCourse({ department: S.dept, academic_year_id: S.ay.id, code: f.code.value, name: f.name.value, semester: Number(f.semester.value), credits: Number(f.credits.value || 3) });
        toast(`Course ${f.code.value.toUpperCase()} added`); App.rerender();
      } catch (err) { App.showError(err, $("#addMsg", view)); }
    };
    const run = $("#runBtn", view);
    if (run) run.onclick = async () => { const r = await App.runC3(run); if (r) location.hash = "#/dashboard"; };

    courses.forEach((c) => {
      const card = $(`[data-course="${c.id}"]`, view);
      const msg = $(".cmsg", card);
      const onFile = (sel, fn, label) => { const inp = $(sel, card); if (inp) inp.onchange = async () => {
        const file = inp.files[0]; if (!file) return;
        msg.innerHTML = `<div class="alert info small" style="margin-top:10px">${icon("loader", 14, "spin")} Uploading ${esc(file.name)}…</div>`;
        try { const r = await fn(c.id, file); msg.innerHTML = `<div class="alert ok small" style="margin-top:10px">${label(r)}</div>`; toast("Upload saved"); setTimeout(App.rerender, 900); }
        catch (err) { App.showError(err, msg); } finally { inp.value = ""; }
      }; };
      onFile(".copo-in", API.c3UploadCoPo, (r) => `CO-PO matrix saved: ${r.course_outcomes} COs, ${r.mappings} mappings.`);
      onFile(".marks-in", API.c3UploadMarks, (r) => `Marks saved: ${r.students} students (${r.new_students} new), ${r.components} questions (${r.cie_components} CIE, ${r.see_components} SEE), ${r.marks_written} marks.${r.created_course_outcomes.length ? ` New COs created: ${r.created_course_outcomes.join(", ")} — add their statements via the CO-PO matrix.` : ""}`);
      const tpl = $(".tpl", card); if (tpl) tpl.onclick = () => API.c3Template(c.id, c.code).catch(App.showError);
      const view_ = $(".viewmarks", card); if (view_) view_.onclick = () => openMarks(c);
      const del = $(".del", card); if (del) del.onclick = async () => {
        if (del.dataset.confirm !== "1") { del.dataset.confirm = "1"; del.innerHTML = "Click again to delete"; return; }
        try { await API.c3DeleteCourse(c.id); toast(`${c.code} deleted`); App.rerender(); } catch (err) { App.showError(err); }
      };
      const sv = $(".survey-save", card); if (sv) sv.onclick = async () => {
        const values = {}; $$("[data-survey]", card).forEach((i) => { values[i.dataset.survey] = i.value === "" ? null : Number(i.value); });
        try { await API.c3SaveIndirect(c.id, values); toast(`Course exit survey saved for ${c.code}`); }
        catch (err) { App.showError(err, msg); }
      };
    });
  };

  function courseCard(c) {
    const ok = (b, t) => `<span class="chk ${b ? "ok" : ""}">${icon(b ? "check" : "x", 11)} ${t}</span>`;
    return `<div class="course-card" data-course="${c.id}">
      <div class="course-head"><span class="code" style="font-size:13px">${esc(c.code)}</span><strong>${esc(c.name)}</strong><span class="muted small">Sem ${c.semester} · ${c.credits} credits</span><span class="spacer"></span>
        ${ok(c.co_count, `${c.co_count} COs`)} ${ok(c.mapping_count, `${c.mapping_count} CO-PO links`)} ${ok(c.students_with_marks, `${c.students_with_marks} students`)} ${ok(c.co_count && c.indirect_entries >= c.co_count, "exit survey")}</div>
      ${c.course_outcomes.length ? `<div style="overflow-x:auto;margin-top:10px"><table class="matrix"><thead><tr><th class="l">CO</th><th class="l">Statement</th><th>Mapped to</th><th>Exit survey %</th></tr></thead><tbody>
        ${c.course_outcomes.map((co) => `<tr><td>${esc(co.code)}</td><td class="l" style="white-space:normal;min-width:260px">${esc(co.description)}</td>
          <td class="small">${Object.entries({ ...co.po_map, ...co.pso_map }).map(([k, v]) => `${k}:${v}`).join(" ") || "—"}</td>
          <td>${S.canUpload ? `<input type="number" min="0" max="100" step="1" data-survey="${co.code}" />` : "—"}</td></tr>`).join("")}</tbody></table></div>` : ""}
      ${c.components.length ? `<p class="small muted" style="margin:8px 0 0">${c.components.length} assessment questions: ${c.components.slice(0, 8).map((x) => `${esc(x.name)} (${x.type}/${x.max})`).join(", ")}${c.components.length > 8 ? "…" : ""}</p>` : ""}
      ${S.canUpload ? `<div class="row wrap" style="margin-top:12px">
        <label class="btn sm file-btn">${icon("link", 13)} Upload CO-PO matrix<input type="file" accept=".csv" class="copo-in" /></label>
        <label class="btn sm primary file-btn">${icon("upload", 13)} Upload marks<input type="file" accept=".csv" class="marks-in" /></label>
        <button class="btn sm tpl">${icon("download", 13)} Marks template</button>
        ${c.students_with_marks ? `<button class="btn sm viewmarks">${icon("search", 13)} View marks</button>` : ""}
        ${c.co_count ? `<button class="btn sm survey-save">${icon("check", 13)} Save exit survey</button>` : ""}
        <span class="spacer"></span>${S.isHod ? `<button class="btn sm danger del">${icon("x", 13)} Delete</button>` : ""}</div>` : ""}
      <div class="cmsg"></div></div>`;
  }

  async function openMarks(c) {
    App.openDrawer(`<div class="drawer-head"><div><div class="eyebrow">${esc(c.code)}</div><h3 style="margin:4px 0 0;font-size:18px">Marks sheet</h3></div><button class="btn ghost sm" data-close>${icon("x", 16)}</button></div>
      <div class="drawer-body" id="mk"><div class="skeleton" style="height:200px"></div></div>`, async (d) => {
      try {
        const m = await API.c3Marks(c.id);
        $("#mk", d).innerHTML = `<div style="overflow:auto"><table class="matrix"><thead><tr><th class="l">USN</th><th class="l">Name</th>${m.components.map((x) => `<th title="${esc(x.name)}">${esc(x.name)}<br><span class="muted">${esc(x.co || "")}/${x.max}</span></th>`).join("")}</tr></thead><tbody>
          ${m.rows.map((r) => `<tr><td class="l">${esc(r.usn)}</td><td class="l">${esc(r.name)}</td>${m.components.map((x) => { const v = r.marks[x.id]; return `<td>${v == null ? '<span class="muted">AB</span>' : v}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
      } catch (e) { App.showError(e, $("#mk", d)); }
    });
    // Drawer is narrow for wide sheets
    const dr = document.querySelector(".drawer"); if (dr) dr.style.width = "min(1000px, 100vw)";
  }

  // ==================================================================== ATTAINMENT
  App.pages.attainment = async (view) => {
    const [att, surveys] = await Promise.all([API.c3Attainment(S.dept, S.ay.id), API.c3PoIndirect(S.dept, S.ay.id)]);
    const cfg = att.config, p = att.po, sm = att.summary;
    const marked = att.courses.filter((c) => c.has_marks && c.cos.length);
    const allCodes = [...new Set([...p.codes, ...Array.from({ length: 11 }, (_, i) => `PO${i + 1}`)])].sort((a, b) => {
      const k = (x) => [x.startsWith("PSO") ? 1 : 0, Number(x.replace(/\D/g, ""))]; const [a1, a2] = k(a), [b1, b2] = k(b); return a1 - b1 || a2 - b2;
    });
    const notAddressed = allCodes.filter((c) => !p.codes.includes(c));

    view.innerHTML = `
      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Attainment methodology ${cfg.is_approved ? '<span class="badge PASS">APPROVED</span>' : '<span class="badge WARNING">NOT APPROVED — 3.7/3.8 cannot be scored</span>'}</h2>
          <p class="section-sub">A student attains a CO at ≥ ${cfg.student_threshold_pct}% of its marks · Level 3 ≥ ${cfg.level3_pct}% students, Level 2 ≥ ${cfg.level2_pct}%, Level 1 ≥ ${cfg.level1_pct}% · Direct = ${cfg.cie_weight}% CIE + ${cfg.see_weight}% SEE · Final = ${cfg.direct_weight}% direct + ${cfg.indirect_weight}% indirect · CO target ${cfg.co_target_level}, PO target ${cfg.po_target_level}</p></div>
          <div class="row">${S.isHod ? `<a class="btn sm" href="#/settings">${icon("settings", 13)} Edit</a><button class="btn primary sm" id="runBtn">${icon("play", 13)} Run Criterion 3</button>` : ""}</div></div>
        <div class="grid-4">
          <div class="mini-kpi"><div class="l">Courses with marks</div><div class="v">${sm.courses_with_marks}/${sm.courses_total}</div></div>
          <div class="mini-kpi"><div class="l">COs meeting target</div><div class="v">${sm.cos_assessed ? `${sm.cos_met}/${sm.cos_assessed}` : "—"}</div></div>
          <div class="mini-kpi"><div class="l">Avg CO level</div><div class="v">${sm.avg_co_level ?? "—"}</div></div>
          <div class="mini-kpi"><div class="l">Avg PO/PSO level</div><div class="v">${sm.avg_po_level ?? "—"}</div></div>
        </div>
        ${att.limitations.length ? `<div class="alert info small" style="margin-top:12px">${att.limitations.map(esc).join("<br>")}</div>` : ""}
      </section>

      ${marked.map((c) => `<section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">${esc(c.code)} — ${esc(c.name)}</h2><p class="section-sub">${c.students} students · ${c.components} questions · CO attainment (3.7.2)</p></div></div>
        <div style="overflow-x:auto"><table class="matrix"><thead><tr><th>CO</th><th>CIE: % students ≥ ${cfg.student_threshold_pct}%</th><th>CIE level</th><th>SEE: % students</th><th>SEE level</th><th>Direct</th><th>Exit survey %</th><th>Indirect</th><th>Final</th><th>Target</th><th>Status</th></tr></thead><tbody>
        ${c.cos.map((r) => `<tr><td><b>${esc(r.code)}</b></td><td>${r.cie_attained_pct ?? "—"}</td><td>${r.cie_level ?? "—"}</td><td>${r.see_attained_pct ?? "—"}</td><td>${r.see_level ?? "—"}</td><td>${lvl(r.direct)}</td><td>${r.indirect_pct ?? "—"}</td><td>${r.indirect ?? "—"}</td><td>${lvl(r.final, r.target)}</td><td>${r.target}</td><td>${r.assessed ? (r.met ? '<span class="badge PASS">MET</span>' : '<span class="badge FAIL">WEAK</span>') : "—"}</td></tr>`).join("")}
        </tbody></table></div></section>`).join("") || `<section class="card card-pad"><div class="empty">No marks uploaded yet. Go to <a href="#/courses">Courses &amp; Marks</a>.</div></section>`}

      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Table 3.8.1 — PO/PSO attainment using direct assessment</h2><p class="section-sub">Course value = Σ(correlation × CO level) / Σ correlation. Direct attainment = average across courses addressing the PO/PSO.</p></div></div>
        ${p.codes.length ? `<div style="overflow-x:auto"><table class="matrix"><thead><tr><th class="l">Course</th>${allCodes.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>
          ${marked.map((c) => `<tr><td class="l">${esc(c.code)}</td>${allCodes.map((k) => `<td>${c.po_values[k] != null ? c.po_values[k].toFixed(2) : ""}</td>`).join("")}</tr>`).join("")}
          <tr class="total"><td class="l">Direct attainment</td>${allCodes.map((k) => `<td>${p.direct[k] != null ? p.direct[k].toFixed(2) : "—"}</td>`).join("")}</tr></tbody></table></div>
          ${notAddressed.length ? `<div class="alert warn small" style="margin-top:10px">Not addressed by any course with marks: ${notAddressed.join(", ")}. An NBA evaluator will ask how these outcomes are attained.</div>` : ""}` : `<div class="small muted">Upload the CO-PO matrix and marks first.</div>`}
      </section>

      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Table 3.8.2 — PO/PSO attainment using indirect assessment</h2><p class="section-sub">Survey results converted to levels 0–3 (program exit, alumni, employer surveys).</p></div>
          ${S.isHod ? `<div class="row"><button class="btn sm" id="addSurvey">${icon("plus", 13)} Add survey</button><button class="btn sm primary" id="saveSurveys">${icon("check", 13)} Save surveys</button></div>` : ""}</div>
        <div style="overflow-x:auto"><table class="matrix" id="surveyTbl"><thead><tr><th class="l">Survey</th>${allCodes.map((c) => `<th>${c}</th>`).join("")}${S.isHod ? "<th></th>" : ""}</tr></thead><tbody>
          ${(surveys.length ? surveys : [{ name: "Program Exit Survey", values: {} }]).map((s) => surveyRow(s, allCodes)).join("")}
          <tr class="total"><td class="l">Indirect attainment</td>${allCodes.map((k) => `<td>${p.indirect[k] != null ? p.indirect[k].toFixed(2) : "—"}</td>`).join("")}${S.isHod ? "<td></td>" : ""}</tr>
        </tbody></table></div><div id="surveyMsg"></div>
      </section>

      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Table 3.8.3 — Overall PO/PSO attainment</h2><p class="section-sub">Overall = ${cfg.direct_weight}% direct + ${cfg.indirect_weight}% indirect · target ${p.target}</p></div></div>
        ${p.codes.length ? `<div style="overflow-x:auto"><table class="matrix"><thead><tr><th class="l">Assessment</th>${p.codes.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>
          <tr><td class="l">Direct</td>${p.codes.map((c) => `<td>${lvl(p.direct[c])}</td>`).join("")}</tr>
          <tr><td class="l">Indirect</td>${p.codes.map((c) => `<td>${lvl(p.indirect[c])}</td>`).join("")}</tr>
          <tr class="total"><td class="l">Overall</td>${p.codes.map((c) => `<td>${lvl(p.overall[c], p.target)}</td>`).join("")}</tr></tbody></table></div>
          <div class="chart-wrap" id="poChart" style="margin-top:18px"></div>
          <div class="chart-legend"><span><i style="background:var(--green-700)"></i>Overall attainment</span><span><i style="background:var(--bar-max)"></i>Maximum level (3)</span></div>` : `<div class="small muted">Nothing to show yet.</div>`}
      </section>`;

    if (p.codes.length) renderMarksChart($("#poChart", view), p.codes.map((c) => ({ name: c, num: `target ${p.target}`, max: 3, obtained: p.overall[c], status: p.met[c] ? "PASS" : "WARNING" })));
    const run = $("#runBtn", view);
    if (run) run.onclick = async () => { if (await App.runC3(run)) App.rerender(); };
    const tbody = $("#surveyTbl tbody", view);
    const add = $("#addSurvey", view);
    if (add) add.onclick = () => { tbody.insertAdjacentHTML("afterbegin", surveyRow({ name: "", values: {} }, allCodes)); bindDel(); };
    const bindDel = () => $$("[data-del-survey]", view).forEach((b) => (b.onclick = () => b.closest("tr").remove()));
    bindDel();
    const save = $("#saveSurveys", view);
    if (save) save.onclick = async () => {
      const surveysOut = $$("tr[data-survey-row]", view).map((tr) => {
        const values = {}; $$("input[data-po]", tr).forEach((i) => { if (i.value !== "") values[i.dataset.po] = Number(i.value); });
        return { name: $("input[data-name]", tr).value.trim(), values };
      }).filter((s) => s.name);
      try { await API.c3SavePoIndirect(S.dept, S.ay.id, surveysOut); toast("Surveys saved"); App.rerender(); }
      catch (err) { App.showError(err, $("#surveyMsg", view)); }
    };
  };

  function surveyRow(s, codes) {
    return `<tr data-survey-row><td class="l">${S.isHod ? `<input data-name value="${esc(s.name)}" placeholder="Survey name" style="width:180px;text-align:left" />` : esc(s.name)}</td>
      ${codes.map((c) => `<td>${S.isHod ? `<input data-po="${c}" type="number" min="0" max="3" step="0.1" value="${s.values[c] ?? ""}" />` : (s.values[c] ?? "")}</td>`).join("")}
      ${S.isHod ? `<td><button class="btn sm ghost" data-del-survey>${icon("x", 12)}</button></td>` : ""}</tr>`;
  }
})();
