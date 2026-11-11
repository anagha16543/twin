# Frontend — Criterion 3 portal (HTML · CSS · JavaScript)

No framework, no build step. The backend serves this folder at **http://localhost:8000/app/**,
so start everything with `python run.py` from the project root (see `../START_HERE.md`).

## Flow

`index.html` (splash) → `login.html` (sign in / faculty registration) → `app.html` (portal)

## Portal pages (`app.html#/…`)

| Sidebar item | Route | Backend |
|---|---|---|
| Dashboard | `#/dashboard` | `/digital-twin/criteria/CRITERION_3`, `/criterion3/attainment`, `/criterion3/courses` |
| C3 → Courses & Marks | `#/courses` | `/criterion3/courses`, `…/co-po`, `…/marks`, `…/indirect` |
| C3 → CO / PO Attainment | `#/attainment` | `/criterion3/attainment`, `/criterion3/po-indirect` |
| C3 → 3.1 … 3.8 | `#/c3/3.x` | `/criterion3/rubric-scores`, `/nba/requirements/{id}/evaluations`, `/analysis/ai-analysis` |
| C3 → Evidence Repository | `#/evidence` | `/documents/*` |
| C3 → Gaps & Actions | `#/gaps` | `/gaps/*` |
| Virtual Inspection | `#/inspection` | `/criterion3/run` |
| Faculty Approvals | `#/approvals` | `/users/pending`, `/users/{id}/approve` |
| Notifications / My Profile | `#/notifications`, `#/profile` | `/notifications`, `/auth/me` |
| Settings | `#/settings` | `/criterion3/config` (attainment methodology) |
| C4 / C5 / C6 | `#/scope/C4` … | out of scope for this build |

**Run Criterion 3** (`POST /criterion3/run`) recomputes attainment from the uploaded marks, scores 3.1–3.8 with the
NBA Annexure VII rubric, saves the evaluations and opens or closes gaps. The frontend never calculates a score itself.

## Files

```
index.html  login.html  app.html  criterion3.html (redirect)
css/styles.css   design tokens + components     css/app.css   portal pages
css/slideshow.css
js/config.js     API base (same-origin /api/v1 when served by the backend)
js/api.js        every endpoint used
js/utils.js      icons, formatting, toast
js/chart.js      SVG bar chart
js/app.js        shell, router, sidebar, insights, AI assistant
js/pages-c3.js   dashboard, 3.x workspaces, courses & marks, attainment
js/pages-other.js evidence, gaps, inspection, approvals, notifications, profile, settings
```
