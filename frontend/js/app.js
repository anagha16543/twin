// App shell: session, shared state, hash router, drawers, sidebar, insights, notifications, AI assistant.
(function () {
  const { icon, esc, badge, fmtDateTime, fmtScore, splitTitle, $, $$, toast } = U;
  const CODE = NBA_CONFIG.CRITERION_CODE;

  const S = {
    me: null, ay: null, dept: "", isHod: false, canUpload: false,
    criterion: null, requirements: [], rubric: null, analytics: null,
  };

  const App = {
    S, pages: {},
    reqByCode: (rc) => S.requirements.find((r) => r.rubric === rc),
    reqById: (id) => S.requirements.find((r) => r.id === id),
    summary: (id) => S.analytics?.requirements.find((r) => r.requirement_id === id),
  };

  // ---------------------------------------------------------------- boot
  App.start = async function () {
    if (!API.token.get()) { location.replace("login.html"); return; }
    hydrateIcons();
    try {
      const [me, years, criteria, rub] = await Promise.all([API.me(), API.academicYears(), API.criteria(), API.c3Rubric()]);
      S.me = me;
      S.ay = years.find((y) => y.is_active) || years[0];
      S.dept = me.faculty_profile?.department || NBA_CONFIG.DEFAULT_DEPARTMENT;
      S.isHod = me.roles.some((r) => r === "HOD" || r === "ADMIN");
      S.canUpload = S.isHod || me.roles.includes("FACULTY");
      S.criterion = criteria.find((c) => c.code === CODE);
      S.rubric = rub.rubric;
      if (!S.ay) throw new Error("No academic year configured. Restart with `python run.py`.");
      if (!S.criterion) throw new Error("Criterion 3 is not seeded. Restart with `python run.py`.");
      const reqs = await API.requirements(S.criterion.id);
      S.requirements = reqs
        .filter((r) => r.is_active && r.weightage > 0 && rub.requirement_map[r.code])
        .sort((a, b) => a.display_order - b.display_order)
        .map((r) => ({ ...r, rubric: rub.requirement_map[r.code] }));
      renderIdentity();
      await App.refreshAnalytics();
      bindChrome();
      window.addEventListener("hashchange", route);
      route();
      App.loadNotifications();
    } catch (e) {
      $("#view").innerHTML = `<div class="card card-pad"><div class="alert err"><b>Could not load the workspace.</b><br>${esc(e.message)}</div>
        <p class="small muted">Make sure the backend is running (<span class="code">python run.py</span>) and open <span class="code">http://localhost:8000/app/</span>.</p></div>`;
    }
  };

  App.refreshAnalytics = async function () {
    S.analytics = await API.criterionAnalytics(CODE, S.dept, S.ay.id);
    renderSidebarSubcriteria();
    renderInsights();
  };

  // Run Criterion 3 end-to-end (attainment + rubric + gaps) and refresh.
  App.runC3 = async function (btn) {
    if (!S.isHod) { toast("Only HOD/Admin can run Criterion 3", "err"); return null; }
    if (btn) { btn.disabled = true; btn.dataset.label = btn.innerHTML; btn.innerHTML = `${icon("loader", 14, "spin")} Running…`; }
    try {
      const r = await API.c3Run(S.dept, S.ay.id);
      await App.refreshAnalytics();
      toast(`Criterion 3: ${fmtScore(r.total_score)}/${fmtScore(r.max_score)} · ${r.passed}/${r.evaluated} PASS · gaps +${r.gaps_created}${r.gaps_closed ? `, closed ${r.gaps_closed}` : ""}`);
      return r;
    } catch (e) { App.showError(e); return null; }
    finally { if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.label; } }
  };

  App.showError = (e, target) => {
    const html = `<div class="alert err" style="margin:10px 0">${esc(e.message)}${e.problems?.length ? `<ul class="problems">${e.problems.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>` : ""}</div>`;
    if (target) target.innerHTML = html; else toast(e.message, "err");
    return html;
  };

  // ---------------------------------------------------------------- router
  const ROUTES = {
    dashboard: { title: "Criterion 3: Teaching-Learning and Assessment", crumb: ["Home", "Dashboard"] },
    c3: { title: "Criterion 3: Teaching-Learning and Assessment", crumb: ["Home", "Criteria Workspace"] },
    sub: { title: "", crumb: ["Home", "Criteria Workspace", "Criterion 3"] },
    courses: { title: "Courses, CO-PO Mapping & Marks", crumb: ["Home", "Criteria Workspace", "Criterion 3"] },
    attainment: { title: "CO / PO / PSO Attainment", crumb: ["Home", "Criteria Workspace", "Criterion 3"] },
    evidence: { title: "Evidence Repository — Criterion 3", crumb: ["Home", "Criteria Workspace", "Criterion 3"] },
    gaps: { title: "Gaps & Corrective Actions — Criterion 3", crumb: ["Home", "Criteria Workspace", "Criterion 3"] },
    inspection: { title: "Virtual NBA Inspection — Criterion 3", crumb: ["Home", "Virtual Inspection"] },
    approvals: { title: "Faculty Approvals", crumb: ["Home", "Faculty Approvals"] },
    notifications: { title: "Notifications", crumb: ["Home", "Notifications"] },
    profile: { title: "My Profile", crumb: ["Home", "My Profile"] },
    settings: { title: "Settings — Attainment Methodology", crumb: ["Home", "Settings"] },
    scope: { title: "Out of scope", crumb: ["Home", "Criteria Workspace"] },
  };

  let routeToken = 0;
  async function route() {
    const parts = (location.hash.replace(/^#\/?/, "") || "dashboard").split("/");
    let name = parts[0], param = parts[1];
    if (name === "c3" && param) name = "sub";
    if (name === "c3") name = "dashboard";
    if (!App.pages[name]) { location.hash = "#/dashboard"; return; }
    const meta = ROUTES[name] || ROUTES.dashboard;
    const myToken = ++routeToken;
    const activeKey = name === "sub" ? `sub-${param}` : name === "scope" ? `scope-${(param || "").toLowerCase()}` : name;
    $$("[data-route]").forEach((a) => a.classList.toggle("active", a.dataset.route === activeKey || (activeKey === "dashboard" && a.dataset.route === "c3")));
    $("#crumbs").innerHTML = meta.crumb.map(esc).join(` ${icon("chevRight", 12)} `);
    $("#pageTitle").textContent = meta.title;
    const view = $("#view");
    view.innerHTML = `<div class="skeleton" style="height:120px"></div><div class="skeleton" style="height:320px"></div>`;
    window.scrollTo(0, 0);
    try {
      await App.pages[name](view, param, (title) => { if (myToken === routeToken) $("#pageTitle").textContent = title; });
      hydrateIcons(view);
    } catch (e) {
      if (myToken === routeToken) view.innerHTML = `<div class="card card-pad">${App.showError(e, document.createElement("div"))}</div>`;
    }
  }
  App.rerender = route;

  // ---------------------------------------------------------------- chrome
  function renderIdentity() {
    const short = U.deptShort(S.dept), p = S.me.faculty_profile, name = p?.full_name || S.me.email;
    $("#sbDept").textContent = `Dept. of ${short}`;
    $("#sbMeta").textContent = `AY ${U.ayLong(S.ay.name)} • Tier-I UG`;
    $("#ctxChip").innerHTML = `${esc(short)} <span class="dot">•</span> AY ${esc(U.ayLong(S.ay.name))}`;
    $("#userName").textContent = name;
    $("#userAvatar").textContent = U.initial(name);
    $("#insightAvatar").textContent = U.initial(name);
    $("#userRole").textContent = S.me.roles.includes("HOD") ? "HOD" : S.me.roles.includes("ADMIN") ? "ADMIN" : S.me.roles[0] || "";
  }

  function renderSidebarSubcriteria() {
    $("#sbSubcriteria").innerHTML = S.requirements.map((r) => {
      const s = App.summary(r.id), t = splitTitle(r.title);
      return `<a class="sb-leaf" data-route="sub-${r.rubric}" href="#/c3/${r.rubric}" title="${esc(t.name)}"><span class="dot ${esc(s?.status || "")}"></span>${t.num} ${esc(t.name)}</a>`;
    }).join("");
    const active = (location.hash.match(/#\/c3\/(\d\.\d)/) || [])[1];
    if (active) $$(`#sbSubcriteria [data-route="sub-${active}"]`).forEach((a) => a.classList.add("active"));
  }

  function bindChrome() {
    $("#criteriaToggle").onclick = () => {
      const l = $("#criteriaList"); l.classList.toggle("hidden");
      $("#criteriaToggle").setAttribute("aria-expanded", String(!l.classList.contains("hidden")));
    };
    $("#logoutBtn").onclick = () => { API.token.clear(); try { sessionStorage.removeItem("nbaSplashSeen"); } catch { /* */ } location.replace("login.html"); };
    $("#bellBtn").onclick = (e) => { e.stopPropagation(); $("#notifPop").classList.toggle("hidden"); };
    $("#insightBtn").onclick = (e) => { e.stopPropagation(); $("#insightPop").classList.toggle("hidden"); };
    $("#aiFab").onclick = () => App.openAssistant();
    document.addEventListener("click", (e) => {
      if (!e.target.closest("#notifPop, #bellBtn")) $("#notifPop").classList.add("hidden");
      if (!e.target.closest("#insightPop, #insightBtn")) $("#insightPop").classList.add("hidden");
    });
  }

  function renderInsights() {
    const items = [];
    S.requirements.forEach((r) => {
      const s = App.summary(r.id), t = splitTitle(r.title);
      if (!s) return;
      if (["WARNING", "FAIL", "NEEDS_RULE_CLARIFICATION"].includes(s.status))
        items.push({ href: `#/c3/${r.rubric}`, sev: s.status, text: `${t.num} ${t.name}: ${fmtScore(s.score_attained)}/${fmtScore(s.max_score)}` });
      else if (s.status === "UNEVALUATED")
        items.push({ href: `#/c3/${r.rubric}`, sev: "UNEVALUATED", text: `${t.num} ${t.name}: not evaluated yet` });
      if (!s.has_evidence) items.push({ href: "#/evidence", sev: "WARNING", text: `${t.num} ${t.name}: no evidence linked` });
    });
    $("#insightLabel").textContent = `${items.length} Insight${items.length === 1 ? "" : "s"}`;
    $("#insightPop").innerHTML = `<div class="row" style="margin-bottom:8px"><strong>Readiness insights</strong><span class="spacer"></span></div>` +
      (items.length ? items.map((i) => `<a href="${i.href}" class="row" style="padding:8px 0;border-top:1px solid var(--line);align-items:flex-start;text-decoration:none;color:inherit">${badge(i.sev)}<span class="small">${esc(i.text)}</span></a>`).join("")
        : `<div class="small muted">All C3 sub-criteria pass with evidence linked.</div>`);
    $$("#insightPop a").forEach((a) => a.addEventListener("click", () => $("#insightPop").classList.add("hidden")));
  }

  App.loadNotifications = async function () {
    let data;
    try { data = await API.notifications(); } catch { data = { unread_count: 0, notifications: [] }; }
    const n = data.unread_count;
    $("#bellCount").textContent = n; $("#bellCount").classList.toggle("hidden", !n);
    $("#sbNotifCount").textContent = n; $("#sbNotifCount").classList.toggle("hidden", !n);
    $("#notifPop").innerHTML = `<div class="row" style="padding:12px 14px;border-bottom:1px solid var(--line)"><strong>Notifications</strong><span class="spacer"></span><a class="btn sm ghost" href="#/notifications">View all</a></div>
      <div style="max-height:340px;overflow-y:auto">${data.notifications.length ? data.notifications.slice(0, 8).map((x) => `<div style="padding:10px 14px;border-bottom:1px solid var(--line);${x.is_read ? "opacity:.6" : ""}"><div class="small"><strong>${esc(x.title)}</strong></div><div class="small muted">${esc(x.message)}</div></div>`).join("") : `<div class="empty">You're all caught up.</div>`}</div>`;
    return data;
  };

  // ---------------------------------------------------------------- drawer
  App.openDrawer = function (html, onMount) {
    const root = $("#drawerRoot");
    root.innerHTML = `<div class="overlay" data-close></div><aside class="drawer" role="dialog" aria-modal="true">${html}</aside>`;
    hydrateIcons(root);
    $$("[data-close]", root).forEach((el) => el.addEventListener("click", App.closeDrawer));
    document.addEventListener("keydown", escClose);
    onMount && onMount(root.querySelector(".drawer"));
  };
  App.closeDrawer = () => { $("#drawerRoot").innerHTML = ""; document.removeEventListener("keydown", escClose); };
  function escClose(e) { if (e.key === "Escape") App.closeDrawer(); }

  // ---------------------------------------------------------------- AI
  App.aiResultHtml = function (r) {
    const ok = r.status === "SUCCESS";
    return `<div class="card card-pad" style="padding:14px 16px;border-color:${ok ? "#cde2d6" : "#f0d2cb"}">
      <div class="row" style="margin-bottom:8px"><strong>${icon("sparkles", 14)} AI agent analysis</strong><span class="spacer"></span><span class="badge ${ok ? "PASS" : "FAIL"}">${esc(r.status)}</span></div>
      ${(r.findings || []).map((f) => `<div class="msg bot" style="margin-right:0"><span class="badge IDENTIFIED" style="margin-bottom:6px">${esc(f.category)}</span>\n${esc(f.description)}</div>`).join("")}
      ${(r.recommended_actions || []).length ? `<b class="small">Recommended actions</b><ul class="small">${r.recommended_actions.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
      ${(r.limitations || []).length ? `<div class="alert warn small">${r.limitations.map(esc).join("<br>")}</div>` : ""}
      <p class="small muted" style="margin:8px 0 0">Advisory only — AI never changes the deterministic score.</p></div>`;
  };

  App.openAssistant = function (preselect) {
    const opts = S.requirements.map((r) => `<option value="${r.id}" ${preselect === r.id ? "selected" : ""}>${r.rubric} — ${esc(splitTitle(r.title).name)}</option>`).join("");
    App.openDrawer(`
      <div class="drawer-head"><div><div class="eyebrow">Criterion 3</div><h3 style="margin:4px 0 0;font-size:18px">${icon("sparkles", 18)} NBA AI Assistant</h3>
        <p class="small muted" style="margin:4px 0 0">Assessment → Student → Coordinator agents, grounded in backend-verified evaluations and RAG evidence.</p></div>
        <button class="btn ghost sm" data-close aria-label="Close">${icon("x", 16)}</button></div>
      <div class="drawer-body" id="chatLog"><div class="msg bot">Pick a sub-criterion and run the agent analysis, or search uploaded evidence. I explain results — I never change marks.</div></div>
      <div class="drawer-foot" style="flex-direction:column;align-items:stretch">
        <div class="row"><select class="input" id="aiReq">${opts}</select>
          <button class="btn primary" id="aiRun" ${S.isHod ? "" : "disabled title='HOD/Admin only'"}>${icon("play", 13)} Analyse</button></div>
        <form class="row" id="ragForm"><input class="input" id="ragQ" placeholder="Search evidence, e.g. “attainment methodology”" minlength="3" />
          <button class="btn" type="submit">${icon("search", 14)}</button></form>
      </div>`, (d) => {
      const log = $("#chatLog", d);
      const push = (cls, html) => { const el = document.createElement("div"); el.className = "msg " + cls; el.innerHTML = html; log.appendChild(el); log.scrollTop = log.scrollHeight; return el; };
      $("#aiRun", d).onclick = async (e) => {
        const btn = e.currentTarget, id = $("#aiReq", d).value, r = App.reqById(id);
        btn.disabled = true;
        push("user", `Analyse ${esc(r.rubric)} — ${esc(splitTitle(r.title).name)}`);
        const wait = push("bot", `${icon("loader", 14, "spin")} Running agents…`);
        try { const res = await API.aiAnalysis({ requirement_id: id, academic_year_id: S.ay.id, department: S.dept }); wait.outerHTML = `<div style="margin-bottom:10px">${App.aiResultHtml(res)}</div>`; }
        catch (err) { wait.innerHTML = esc(err.message); } finally { btn.disabled = false; }
      };
      $("#ragForm", d).onsubmit = async (e) => {
        e.preventDefault();
        const q = $("#ragQ", d).value.trim(); if (q.length < 3) return;
        push("user", esc(q)); $("#ragQ", d).value = "";
        const wait = push("bot", `${icon("loader", 14, "spin")} Searching evidence…`);
        try {
          const r = await API.retrieve({ query: q, top_k: 5, department: S.dept, academic_year_id: S.ay.id });
          wait.innerHTML = r.results.length ? `<b>${r.total} passage(s)</b>${r.embedding_available ? "" : " <span class='muted small'>(semantic embeddings off — most recent first)</span>"}` +
            r.results.map((m) => `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--line)"><span class="code">${esc(m.document_name)} · p.${m.page_number}</span><div class="small">${esc(m.content.slice(0, 300))}${m.content.length > 300 ? "…" : ""}</div></div>`).join("")
            : "No matching evidence passages. Upload documents first.";
        } catch (err) { wait.innerHTML = esc(err.message); }
      };
    });
  };

  window.App = App;
})();
