// Thin client for the FastAPI backend (backend/app/api/v1).
// Every score and status shown in the UI comes from these endpoints —
// the frontend never computes compliance itself.
(function () {
  const BASE = window.NBA_CONFIG.API_BASE.replace(/\/$/, "");
  const TOKEN_KEY = "nba_twin_token";

  const token = {
    get() { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
    set(t) { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* storage blocked */ } },
    clear() { try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage blocked */ } },
  };

  class ApiError extends Error {
    constructor(status, message, problems) { super(message); this.status = status; this.problems = problems || []; }
  }

  function detailToMessage(d) {
    if (!d) return "Request failed";
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => (x && x.msg ? `${(x.loc || []).slice(-1)[0] || ""} ${x.msg}`.trim() : String(x))).join("; ");
    if (d.message) return d.message;
    return JSON.stringify(d);
  }

  async function request(path, opts = {}, raw = false) {
    const headers = new Headers(opts.headers || {});
    const t = token.get();
    if (t) headers.set("Authorization", "Bearer " + t);
    if (opts.body && !(opts.body instanceof FormData)) headers.set("Content-Type", "application/json");

    let res;
    try {
      res = await fetch(BASE + path, { ...opts, headers });
    } catch {
      throw new ApiError(0, "Cannot reach the backend at " + BASE + ". Is the FastAPI server running?");
    }
    if (res.status === 401 && !path.startsWith("/auth/login")) {
      token.clear();
      window.location.href = "login.html?expired=1";
      throw new ApiError(401, "Session expired");
    }
    if (!res.ok) {
      let msg = res.statusText, problems = [];
      try {
        const b = await res.json();
        msg = detailToMessage(b.detail || b.error);
        if (b.detail && Array.isArray(b.detail.problems)) problems = b.detail.problems;
      } catch { /* ignore */ }
      throw new ApiError(res.status, msg, problems);
    }
    if (raw) return res;
    if (res.status === 204) return null;
    return res.json();
  }

  const qs = (p) => {
    const u = new URLSearchParams();
    Object.entries(p).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") u.set(k, v); });
    const s = u.toString();
    return s ? "?" + s : "";
  };
  const post = (path, body, method = "POST") => request(path, { method, body: JSON.stringify(body) });

  window.API = {
    token, ApiError,

    // Auth
    login: (email, password) => post("/auth/login", { email, password }),
    register: (body) => post("/auth/register", body),
    me: () => request("/auth/me"),
    academicYears: () => request("/academic-years"),

    // NBA criteria / requirements / deterministic evaluation
    criteria: () => request("/nba/criteria"),
    requirements: (criterionId) => request(`/nba/criteria/${criterionId}/requirements`),
    c3Context: (department, ay) =>
      request(`/nba/criteria/code/CRITERION_3/context${qs({ department, academic_year_id: ay })}`),
    evaluate: (reqId, body) => post(`/nba/requirements/${reqId}/evaluate`, body),
    evaluations: (reqId, department, ay, limit = 10) =>
      request(`/nba/requirements/${reqId}/evaluations${qs({ department, academic_year_id: ay, limit })}`),

    // Digital twin readiness analytics
    criterionAnalytics: (code, department, ay) =>
      request(`/digital-twin/criteria/${code}${qs({ department, academic_year_id: ay })}`),

    // Documents & evidence
    documents: (department, ay) => request(`/documents/${qs({ department, academic_year_id: ay, limit: 100 })}`),
    upload: (file, department, ay) => {
      const fd = new FormData();
      fd.append("file", file);
      return request(`/documents/upload${qs({ department, academic_year_id: ay })}`, { method: "POST", body: fd });
    },
    linkEvidence: (reqId, documentId, note) =>
      post(`/documents/requirements/${reqId}/evidence`, { document_id: documentId, is_primary: true, relevance_note: note || null }),
    requirementEvidence: (reqId) => request(`/documents/requirements/${reqId}/evidence`),
    setValidation: (docId, status) => post(`/documents/${docId}/validation`, { validation_status: status }, "PATCH"),
    download: async (doc) => {
      const res = await request(`/documents/${doc.id}/download`, {}, true);
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url; a.download = doc.original_filename; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    },

    // AI agents & RAG
    aiAnalysis: (body) => post("/analysis/ai-analysis", body),
    retrieve: (body) => post("/analysis/retrieve", body),

    // Gaps & corrective actions
    gaps: (department, ay, criterionId) =>
      request(`/gaps${qs({ department, academic_year_id: ay, criterion_id: criterionId })}`),
    generateGaps: (department, ay, criterionId) =>
      post("/gaps/generate", { department, academic_year_id: ay, criterion_id: criterionId }),
    updateGap: (gapId, body) => post(`/gaps/${gapId}`, body, "PATCH"),
    createAction: (gapId, body) => post(`/gaps/${gapId}/actions`, body),
    updateAction: (actionId, body) => post(`/gaps/actions/${actionId}`, body, "PATCH"),

    // Criterion 3 workflow (marks -> attainment -> rubric -> run)
    c3Rubric: () => request("/criterion3/rubric"),
    c3RubricScores: (department, ay) => request(`/criterion3/rubric-scores${qs({ department, academic_year_id: ay })}`),
    c3SaveRubric: (code, department, ay, scores) =>
      post(`/criterion3/rubric-scores/${code}`, { department, academic_year_id: ay, scores }, "PUT"),
    c3Config: (department, ay) => request(`/criterion3/config${qs({ department, academic_year_id: ay })}`),
    c3SaveConfig: (body) => post("/criterion3/config", body, "PUT"),
    c3Courses: (department, ay) => request(`/criterion3/courses${qs({ department, academic_year_id: ay })}`),
    c3CreateCourse: (body) => post("/criterion3/courses", body),
    c3DeleteCourse: (id) => request(`/criterion3/courses/${id}`, { method: "DELETE" }),
    c3UploadCoPo: (id, file) => { const fd = new FormData(); fd.append("file", file); return request(`/criterion3/courses/${id}/co-po`, { method: "POST", body: fd }); },
    c3UploadMarks: (id, file) => { const fd = new FormData(); fd.append("file", file); return request(`/criterion3/courses/${id}/marks`, { method: "POST", body: fd }); },
    c3Marks: (id) => request(`/criterion3/courses/${id}/marks`),
    c3Template: async (id, code) => {
      const res = await request(`/criterion3/courses/${id}/marks-template`, {}, true);
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a"); a.href = url; a.download = `${code}_marks_template.csv`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    },
    c3SaveIndirect: (id, values) => post(`/criterion3/courses/${id}/indirect`, { values }, "PUT"),
    c3PoIndirect: (department, ay) => request(`/criterion3/po-indirect${qs({ department, academic_year_id: ay })}`),
    c3SavePoIndirect: (department, ay, surveys) => post("/criterion3/po-indirect", { department, academic_year_id: ay, surveys }, "PUT"),
    c3Attainment: (department, ay) => request(`/criterion3/attainment${qs({ department, academic_year_id: ay })}`),
    c3Run: (department, ay) => post("/criterion3/run", { department, academic_year_id: ay }),

    // Users (Faculty approvals)
    pendingUsers: () => request("/users/pending"),
    approveUser: (id) => post(`/users/${id}/approve`, {}),
    rejectUser: (id) => post(`/users/${id}/reject`, {}),

    // Notifications
    notifications: () => request("/notifications?limit=20"),
    markAllRead: () => post("/notifications/read-all", {}),
  };
})();
