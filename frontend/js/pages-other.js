// Evidence, gaps, virtual inspection, faculty approvals, notifications, profile, settings, out-of-scope.
(function () {
  const { icon, esc, badge, fmtDateTime, fmtScore, fmtBytes, splitTitle, $, $$, toast } = U;
  const S = App.S;
  const reqOptions = () => S.requirements.map((r) => `<option value="${r.id}">${r.rubric} — ${esc(splitTitle(r.title).name)}</option>`).join("");

  // ==================================================================== EVIDENCE
  App.pages.evidence = async (view) => {
    const ev = await App.evidenceState();
    const linkedTo = (docId) => S.requirements.filter((r) => (ev.byReq[r.id] || []).some((l) => l.document_id === docId));
    view.innerHTML = `
      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Evidence coverage</h2><p class="section-sub">Every rubric item must be provable from a course-file document.</p></div></div>
        <div class="grid-4">${S.requirements.map((r) => { const n = (ev.byReq[r.id] || []).length; return `<a class="mini-kpi" href="#/c3/${r.rubric}" style="text-decoration:none;color:inherit"><div class="l">${r.rubric} ${esc(splitTitle(r.title).name)}</div><div class="v">${n ? `<span style="color:var(--green-700)">${n} linked</span>` : `<span style="color:var(--red)">none</span>`}</div></a>`; }).join("")}</div>
      </section>
      <section class="card card-pad">
        ${S.isHod ? `<div class="dropzone" id="dz">
          <div class="row" style="justify-content:center;margin-bottom:10px">${icon("upload", 18)}<strong>Upload evidence</strong><span class="muted small">PDF, PNG or JPEG · max 25 MB</span></div>
          <div class="row wrap" style="justify-content:center">
            <input type="file" id="fileIn" accept=".pdf,.png,.jpg,.jpeg" class="input" style="max-width:280px" />
            <select id="linkReq" class="input" style="max-width:320px"><option value="">Link to sub-criterion…</option>${reqOptions()}</select>
            <button class="btn primary" id="uploadBtn">${icon("upload", 14)} Upload &amp; link</button>
          </div><div class="small muted" style="margin-top:8px">or drag a file onto this box</div></div>` : ""}
        <div style="overflow-x:auto;margin-top:16px">
        ${ev.docs.length ? `<table class="tbl"><thead><tr><th>Document</th><th>Linked to</th><th>Processing</th><th>Verification</th><th>Uploaded</th><th></th></tr></thead><tbody>
          ${ev.docs.map((d) => { const l = linkedTo(d.id); return `<tr>
            <td><div class="row">${icon("file", 16)}<div><strong class="small">${esc(d.original_filename)}</strong><div class="small muted">${fmtBytes(d.file_size_bytes)} · v${d.version}</div></div></div></td>
            <td>${l.map((r) => `<span class="badge LOW">${r.rubric}</span>`).join(" ")} ${S.isHod ? `<select class="input" style="padding:4px 8px;font-size:12px;width:auto" data-link="${d.id}"><option value="">+ link…</option>${reqOptions()}</select>` : ""}</td>
            <td class="small muted">${esc(d.processing_status)}</td><td>${badge(d.validation_status)}</td><td class="small muted">${fmtDateTime(d.created_at)}</td>
            <td><div class="row" style="gap:4px;justify-content:flex-end">
              ${S.isHod && d.validation_status !== "VALIDATED" ? `<button class="btn sm" data-verify="${d.id}">${icon("check", 13)} Verify</button>` : ""}
              ${S.isHod && d.validation_status !== "REJECTED" ? `<button class="btn sm danger" data-reject="${d.id}" title="Reject">${icon("xCircle", 13)}</button>` : ""}
              <button class="btn sm" data-dl="${d.id}" title="Download">${icon("download", 13)}</button></div></td></tr>`; }).join("")}
          </tbody></table>` : `<div class="empty">No evidence uploaded for ${esc(S.dept)} in ${esc(S.ay.name)}.</div>`}</div>
      </section>`;

    const upload = async (file) => {
      if (!file) { toast("Choose a file first", "err"); return; }
      const reqId = $("#linkReq").value, btn = $("#uploadBtn"); btn.disabled = true;
      try {
        const up = await API.upload(file, S.dept, S.ay.id);
        if (reqId) { try { await API.linkEvidence(reqId, up.document_id); } catch (e) { if (e.status !== 409) throw e; } }
        toast(up.is_duplicate ? "Duplicate file — existing document reused" : `Uploaded ${up.original_filename}`);
        await App.refreshAnalytics(); App.rerender();
      } catch (e) { App.showError(e); btn.disabled = false; }
    };
    if ($("#uploadBtn", view)) {
      $("#uploadBtn").onclick = () => upload($("#fileIn").files[0]);
      const dz = $("#dz");
      dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
      dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
      dz.addEventListener("drop", (e) => { e.preventDefault(); dz.classList.remove("drag"); upload(e.dataTransfer.files[0]); });
    }
    $$("[data-link]", view).forEach((sel) => sel.addEventListener("change", async () => {
      if (!sel.value) return;
      try { await API.linkEvidence(sel.value, sel.dataset.link); toast("Evidence linked"); await App.refreshAnalytics(); App.rerender(); } catch (e) { App.showError(e); }
    }));
    const setVal = async (id, st) => { try { await API.setValidation(id, st); toast(st === "VALIDATED" ? "Marked as verified" : "Marked as rejected"); App.rerender(); } catch (e) { App.showError(e); } };
    $$("[data-verify]", view).forEach((b) => (b.onclick = () => setVal(b.dataset.verify, "VALIDATED")));
    $$("[data-reject]", view).forEach((b) => (b.onclick = () => setVal(b.dataset.reject, "REJECTED")));
    $$("[data-dl]", view).forEach((b) => (b.onclick = () => API.download(ev.docs.find((d) => d.id === b.dataset.dl)).catch(App.showError)));
  };

  // ==================================================================== GAPS
  App.pages.gaps = async (view) => {
    const gaps = await API.gaps(S.dept, S.ay.id, S.criterion.id);
    const sev = { HIGH: 0, MEDIUM: 1, LOW: 2 };
    gaps.sort((a, b) => (sev[a.severity] ?? 3) - (sev[b.severity] ?? 3));
    const open = gaps.filter((g) => g.status === "IDENTIFIED" || g.status === "IN_PROGRESS");
    const statuses = ["IDENTIFIED", "IN_PROGRESS", "COMPLETED", "CANCELLED"];
    const opt = (cur) => statuses.map((s) => `<option ${s === cur ? "selected" : ""} value="${s}">${U.statusLabel(s)}</option>`).join("");
    const card = (g) => `<div class="card" style="padding:14px 16px;margin-bottom:12px;${g.status === "COMPLETED" ? "opacity:.75" : ""}">
      <div class="row wrap">${badge(g.severity)}<span class="code">${esc(g.requirement_code || "")}</span><strong>${esc(g.title)}</strong><span class="spacer"></span>
        ${S.isHod ? `<select class="input" style="width:auto;padding:5px 8px;font-size:12px" data-gap="${g.id}">${opt(g.status)}</select>` : badge(g.status)}</div>
      <p class="small" style="margin:8px 0 4px">${esc(g.description)}</p>
      ${g.recommended_action ? `<p class="small muted" style="margin:0 0 6px"><b>Recommended:</b> ${esc(g.recommended_action)}</p>` : ""}
      ${g.reason ? `<p class="small muted" style="margin:0 0 6px"><b>Why:</b> ${esc(g.reason)}</p>` : ""}
      ${(g.actions || []).map((a) => `<div class="row wrap" style="padding:7px 0;border-top:1px solid var(--line)">${badge(a.priority)}<span class="small"><strong>${esc(a.title)}</strong> — ${esc(a.description)}</span>
        ${a.due_date ? `<span class="small" style="${a.is_overdue ? "color:var(--red);font-weight:600" : "color:var(--ink-3)"}">due ${fmtDateTime(a.due_date).split(",")[0]}${a.is_overdue ? " · overdue" : ""}</span>` : ""}<span class="spacer"></span>
        ${S.isHod ? `<select class="input" style="width:auto;padding:4px 8px;font-size:12px" data-act="${a.id}">${opt(a.status)}</select>` : badge(a.status)}</div>`).join("")}
      ${S.isHod && g.status !== "COMPLETED" ? `<form class="row wrap" data-add="${g.id}" style="margin-top:8px">
        <input class="input" name="title" placeholder="Corrective action (e.g. Remedial class for CO2)" style="flex:2;min-width:200px" />
        <input class="input" name="description" placeholder="Who does what, and what evidence proves it" style="flex:3;min-width:220px" />
        <select class="input" name="priority" style="width:auto"><option>HIGH</option><option selected>MEDIUM</option><option>LOW</option></select>
        <input class="input" type="date" name="due" style="width:auto" /><button class="btn sm primary" type="submit">${icon("plus", 13)} Add</button></form>` : ""}
    </div>`;
    view.innerHTML = `
      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Continuous improvement loop</h2>
          <p class="section-sub">Gap identified → corrective action → re-assessment (upload new marks) → Run Criterion 3 → gap auto-closes when the CO meets its target.</p></div>
          ${S.isHod ? `<button class="btn primary" id="runBtn">${icon("play", 13)} Run Criterion 3 (refresh gaps)</button>` : ""}</div>
        <div class="grid-4">
          <div class="mini-kpi"><div class="l">Open gaps</div><div class="v">${open.length}</div></div>
          <div class="mini-kpi"><div class="l">High severity</div><div class="v">${open.filter((g) => g.severity === "HIGH").length}</div></div>
          <div class="mini-kpi"><div class="l">Weak-CO gaps</div><div class="v">${open.filter((g) => g.title.startsWith("Weak CO")).length}</div></div>
          <div class="mini-kpi"><div class="l">Closed</div><div class="v">${gaps.filter((g) => g.status === "COMPLETED").length}</div></div>
        </div>
      </section>
      <section class="card card-pad"><h2 class="section-title" style="margin-bottom:12px">Open gaps</h2>${open.length ? open.map(card).join("") : `<div class="empty">No open gaps for Criterion 3.</div>`}</section>
      ${gaps.length > open.length ? `<section class="card card-pad"><h2 class="section-title" style="margin-bottom:12px">Closed / cancelled</h2>${gaps.filter((g) => !open.includes(g)).map(card).join("")}</section>` : ""}`;

    const reload = () => App.rerender();
    const run = $("#runBtn", view); if (run) run.onclick = async () => { if (await App.runC3(run)) reload(); };
    $$("[data-gap]", view).forEach((s) => s.addEventListener("change", async () => { try { await API.updateGap(s.dataset.gap, { status: s.value }); toast("Gap updated"); reload(); } catch (e) { App.showError(e); } }));
    $$("[data-act]", view).forEach((s) => s.addEventListener("change", async () => { try { await API.updateAction(s.dataset.act, { status: s.value }); toast("Action updated"); reload(); } catch (e) { App.showError(e); } }));
    $$("form[data-add]", view).forEach((f) => f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = { title: f.elements.title.value.trim(), description: f.elements.description.value.trim(), priority: f.elements.priority.value, due_date: f.elements.due.value ? new Date(f.elements.due.value).toISOString() : null };
      if (body.title.length < 3 || body.description.length < 5) { toast("Title ≥ 3 and description ≥ 5 characters", "err"); return; }
      try { await API.createAction(f.dataset.add, body); toast("Corrective action added"); reload(); } catch (err) { App.showError(err); }
    }));
  };

  // ==================================================================== VIRTUAL INSPECTION
  App.pages.inspection = async (view) => {
    view.innerHTML = `
      <section class="card card-pad">
        <div class="section-head"><div><h2 class="section-title">Run a virtual NBA inspection for Criterion 3</h2>
          <p class="section-sub">Recomputes CO/PO attainment from the uploaded marks, scores 3.1–3.8 with the Annexure VII rubric, checks evidence and opens/closes gaps.</p></div>
          ${S.isHod ? `<button class="btn primary" id="go">${icon("shield", 14)} Run Virtual NBA Inspection</button>` : `<span class="small muted">HOD/Admin only</span>`}</div>
        <div class="inspect-console" id="console">Ready. ${S.analytics.last_evaluation_timestamp ? `Last inspection: ${fmtDateTime(S.analytics.last_evaluation_timestamp)}.` : "No inspection run yet."}</div>
      </section>
      <div id="result"></div>`;
    const showResult = async (run) => {
      const [gaps, ev] = await Promise.all([API.gaps(S.dept, S.ay.id, S.criterion.id), App.evidenceState()]);
      const sev = { HIGH: 0, MEDIUM: 1, LOW: 2 };
      const open = gaps.filter((g) => g.status === "IDENTIFIED" || g.status === "IN_PROGRESS").sort((a, b) => (sev[a.severity] ?? 3) - (sev[b.severity] ?? 3));
      const st = S.analytics.requirements;
      const n = (s) => st.filter((r) => r.status === s).length;
      const pendingActions = open.reduce((t, g) => t + (g.actions || []).filter((a) => a.status !== "COMPLETED" && a.status !== "CANCELLED").length, 0);
      $("#result", view).innerHTML = `
        <section class="card card-pad">
          <div class="section-head"><div><h2 class="section-title">Virtual NBA Inspection — Criterion 3</h2><p class="section-sub">${fmtDateTime(S.analytics.last_evaluation_timestamp)} · internal readiness indicator, not an official NBA score</p></div>
            <div class="score-big">${fmtScore(st.reduce((t, r) => t + (r.score_attained || 0), 0))} <small>/ ${fmtScore(S.analytics.max_score)}</small></div></div>
          <div class="grid-4">
            <div class="big-stat PASS"><b>${n("PASS")}</b><span>Pass</span></div>
            <div class="big-stat WARNING"><b>${n("WARNING") + n("NEEDS_RULE_CLARIFICATION")}</b><span>Warning</span></div>
            <div class="big-stat FAIL"><b>${n("FAIL")}</b><span>Fail</span></div>
            <div class="big-stat NEUTRAL"><b>${S.analytics.readiness_percentage ?? "—"}%</b><span>Overall readiness</span></div>
          </div>
          <div class="grid-3" style="margin-top:14px">
            <div class="mini-kpi"><div class="l">Missing evidence</div><div class="v">${st.filter((r) => !r.has_evidence).length} sub-criteria</div></div>
            <div class="mini-kpi"><div class="l">Evidence awaiting HOD verification</div><div class="v">${ev.c3docs.length - ev.verified}</div></div>
            <div class="mini-kpi"><div class="l">Open gaps / pending actions</div><div class="v">${open.length} / ${pendingActions}</div></div>
          </div>
        </section>
        <section class="card card-pad"><h2 class="section-title" style="margin-bottom:12px">Findings</h2>
          ${open.length ? open.map((g) => `<div class="row wrap" style="padding:10px 0;border-top:1px solid var(--line);align-items:flex-start">
            ${badge(g.severity)}<div style="flex:1;min-width:240px"><strong class="small">${esc(g.title)}</strong><div class="small muted">${esc(g.recommended_action || g.description)}</div></div>
            <a class="btn sm" href="#/gaps">Assign action ${icon("chevRight", 12)}</a></div>`).join("") : `<div class="alert ok small">No open findings — Criterion 3 is inspection-ready on current data.</div>`}
          ${run && run.limitations?.length ? `<div class="alert info small" style="margin-top:10px">${run.limitations.map(esc).join("<br>")}</div>` : ""}
        </section>`;
      hydrateIcons(view);
    };
    if (S.analytics.last_evaluation_timestamp) showResult(null);
    const go = $("#go", view);
    if (go) go.onclick = async () => {
      const con = $("#console", view);
      const line = (t, cls = "") => { con.innerHTML += `<div class="${cls}">${t}</div>`; };
      con.innerHTML = ""; go.disabled = true;
      line("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"); line("VIRTUAL NBA INSPECTION · CRITERION 3"); line("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      line("Collecting marks, CO-PO matrix and surveys…");
      const r = await App.runC3();
      if (!r) { line("Inspection failed — see the message above.", "fail"); go.disabled = false; return; }
      for (const req of S.requirements) {
        const s = r.statuses[req.rubric];
        await new Promise((ok) => setTimeout(ok, 160));
        line(`${req.rubric} ${splitTitle(req.title).name.padEnd(36, ".")} ${s}`, s === "PASS" ? "ok" : s === "FAIL" ? "fail" : "warn");
      }
      line(`Weak COs: ${r.attainment_summary.weak_cos.map((w) => `${w.course} ${w.code}`).join(", ") || "none"}`);
      line(`Gaps opened: ${r.gaps_created} · closed: ${r.gaps_closed}`);
      line(`Overall readiness: ${r.readiness_percentage}% · Score ${fmtScore(r.total_score)}/${fmtScore(r.max_score)}`, "ok");
      go.disabled = false;
      await showResult(r);
    };
  };

  // ==================================================================== APPROVALS
  App.pages.approvals = async (view) => {
    if (!S.isHod) { view.innerHTML = `<div class="card card-pad"><div class="alert info">Faculty approvals are available to HOD and Admin accounts.</div></div>`; return; }
    const users = await API.pendingUsers();
    view.innerHTML = `<section class="card card-pad">
      <div class="section-head"><div><h2 class="section-title">Pending faculty registrations</h2><p class="section-sub">Faculty register from the login page; approved faculty can upload marks and evidence.</p></div></div>
      ${users.length ? `<table class="tbl"><thead><tr><th>Name</th><th>Email</th><th>Faculty ID</th><th>Department</th><th>Registered</th><th></th></tr></thead><tbody>
        ${users.map((u) => `<tr><td><strong>${esc(u.faculty_profile?.full_name || "—")}</strong><div class="small muted">${esc(u.faculty_profile?.designation || "")}</div></td><td class="small">${esc(u.email)}</td><td class="code">${esc(u.faculty_profile?.faculty_id || "")}</td><td class="small">${esc(u.faculty_profile?.department || "")}</td><td class="small muted">${fmtDateTime(u.created_at)}</td>
          <td><div class="row" style="gap:6px;justify-content:flex-end"><button class="btn sm primary" data-ok="${u.id}">${icon("check", 13)} Approve</button><button class="btn sm danger" data-no="${u.id}">Reject</button></div></td></tr>`).join("")}</tbody></table>`
        : `<div class="empty">No pending registrations. Faculty can register at <span class="code">login.html → Faculty registration</span>.</div>`}</section>`;
    $$("[data-ok]", view).forEach((b) => (b.onclick = async () => { try { await API.approveUser(b.dataset.ok); toast("Faculty approved"); App.rerender(); } catch (e) { App.showError(e); } }));
    $$("[data-no]", view).forEach((b) => (b.onclick = async () => { try { await API.rejectUser(b.dataset.no); toast("Registration rejected"); App.rerender(); } catch (e) { App.showError(e); } }));
  };

  // ==================================================================== NOTIFICATIONS
  App.pages.notifications = async (view) => {
    const data = await App.loadNotifications();
    view.innerHTML = `<section class="card card-pad"><div class="section-head"><div><h2 class="section-title">Notifications</h2><p class="section-sub">${data.unread_count} unread</p></div>
      ${data.unread_count ? `<button class="btn sm" id="readAll">Mark all read</button>` : ""}</div>
      ${data.notifications.length ? data.notifications.map((x) => `<div style="padding:12px 0;border-top:1px solid var(--line);${x.is_read ? "opacity:.6" : ""}"><div class="row">${badge(x.is_read ? "LOW" : "IDENTIFIED").replace(/LOW|IDENTIFIED/, esc(x.notification_type))}<strong class="small">${esc(x.title)}</strong><span class="spacer"></span><span class="small muted">${fmtDateTime(x.created_at)}</span></div><div class="small muted" style="margin-top:4px">${esc(x.message)}</div></div>`).join("")
        : `<div class="empty">You're all caught up.</div>`}</section>`;
    const ra = $("#readAll", view); if (ra) ra.onclick = async () => { await API.markAllRead().catch(() => {}); App.rerender(); };
  };

  // ==================================================================== PROFILE
  App.pages.profile = async (view) => {
    const p = S.me.faculty_profile;
    view.innerHTML = `<section class="card card-pad"><div class="row" style="gap:18px">
      <div class="avatar" style="width:64px;height:64px;font-size:26px">${esc(U.initial(p?.full_name || S.me.email))}</div>
      <div><h2 style="margin:0">${esc(p?.full_name || S.me.email)}</h2><div class="muted">${esc(p?.designation || "")} · ${esc(S.me.roles.join(", "))}</div></div></div>
      <dl class="kv" style="margin-top:20px">
        <dt>email</dt><dd>${esc(S.me.email)}</dd><dt>faculty id</dt><dd>${esc(p?.faculty_id || "—")}</dd>
        <dt>department</dt><dd>${esc(S.dept)}</dd><dt>academic year</dt><dd>${esc(S.ay.name)}</dd>
        <dt>account status</dt><dd>${esc(S.me.status)}</dd><dt>last login</dt><dd>${fmtDateTime(S.me.last_login)}</dd>
        <dt>permissions</dt><dd>${S.isHod ? "Run Criterion 3, approve methodology, score rubric, verify evidence, manage gaps" : "Upload marks, CO-PO matrices, surveys and evidence"}</dd>
      </dl></section>`;
  };

  // ==================================================================== SETTINGS (attainment methodology)
  App.pages.settings = async (view) => {
    const cfg = await API.c3Config(S.dept, S.ay.id);
    const f = (k, label, hint, step = 1, min = 0, max = 100) => `<div class="field"><label>${label}</label><input class="input" type="number" name="${k}" value="${cfg[k]}" step="${step}" min="${min}" max="${max}" ${S.isHod ? "" : "disabled"} /><span class="hint">${hint}</span></div>`;
    view.innerHTML = `<section class="card card-pad">
      <div class="section-head"><div><h2 class="section-title">CO / PO attainment methodology ${cfg.is_approved ? '<span class="badge PASS">APPROVED</span>' : '<span class="badge WARNING">NOT APPROVED</span>'}</h2>
        <p class="section-sub">NBA 3.7.2: "Program shall set course outcome attainment levels for each course." Until this is approved, 3.7 and 3.8 return NEEDS CLARIFICATION.</p></div></div>
      <form id="cfg">
        <div class="grid-3">
          ${f("student_threshold_pct", "Student attains a CO at (% of CO marks)", "e.g. 60 → a student scoring ≥ 60% of a CO's marks attains it")}
          ${f("level3_pct", "Level 3 if ≥ (% of students)", "Highest attainment level")}
          ${f("level2_pct", "Level 2 if ≥ (% of students)", "")}
          ${f("level1_pct", "Level 1 if ≥ (% of students)", "Below this → level 0")}
          ${f("cie_weight", "CIE weight in direct attainment (%)", "CIE + SEE must be 100")}
          ${f("see_weight", "SEE weight in direct attainment (%)", "")}
          ${f("direct_weight", "Direct weight in final attainment (%)", "Direct + indirect must be 100")}
          ${f("indirect_weight", "Indirect (survey) weight (%)", "")}
          ${f("co_target_level", "CO target level (0–3)", "COs below this become weak-CO gaps", 0.1, 0.1, 3)}
          ${f("po_target_level", "PO/PSO target level (0–3)", "", 0.1, 0.1, 3)}
        </div>
        <div id="cfgMsg"></div>
        ${S.isHod ? `<div class="row"><button class="btn primary" type="submit">${icon("check", 13)} Save &amp; approve methodology</button><span class="small muted">${cfg.approved_at ? `Approved ${fmtDateTime(cfg.approved_at)}` : ""}</span></div>` : `<div class="alert info small">Only HOD/Admin can change the methodology.</div>`}
      </form></section>
      <section class="card card-pad"><h2 class="section-title" style="margin-bottom:10px">System</h2>
        <dl class="kv"><dt>API</dt><dd>${esc(NBA_CONFIG.API_BASE)}</dd><dt>API docs</dt><dd><a href="/docs" target="_blank">/docs</a></dd><dt>AI service</dt><dd>http://localhost:8001 (set GROQ_API_KEY in ai-service/.env for real answers)</dd></dl></section>`;
    const form = $("#cfg", view);
    form.onsubmit = async (e) => {
      e.preventDefault();
      const body = { department: S.dept, academic_year_id: S.ay.id, approve: true };
      ["student_threshold_pct", "level3_pct", "level2_pct", "level1_pct", "cie_weight", "see_weight", "direct_weight", "indirect_weight", "co_target_level", "po_target_level"].forEach((k) => { body[k] = Number(form.elements[k].value); });
      try { await API.c3SaveConfig(body); toast("Methodology approved — run Criterion 3 to apply it"); App.rerender(); }
      catch (err) { App.showError(err, $("#cfgMsg", view)); }
    };
  };

  // ==================================================================== OUT OF SCOPE
  App.pages.scope = async (view, c, setTitle) => {
    const names = { C4: "Students' Performance", C5: "Faculty Information", C6: "Faculty Contributions" };
    setTitle(`Criterion ${String(c || "").replace("C", "")}: ${names[c] || ""}`);
    view.innerHTML = `<section class="card scope-card">${icon("lock", 36)}<h2>${esc(c)} is not part of this build</h2>
      <p class="muted" style="max-width:520px;margin:8px auto 18px">This release implements Criterion 3 end to end. The backend already has rules for ${esc(c)}, but the frontend workflow is out of scope.</p>
      <a class="btn primary" href="#/dashboard">Go to the Criterion 3 dashboard</a></section>`;
  };
})();
