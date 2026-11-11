# How to verify Criterion 3 works (step by step)

Do these in order on a **fresh database**. Each step lists the exact result you should see; the numbers come from the files in `sample_data/`. If a number matches, the backend calculated it from your upload. Nothing on the dashboard is hard-coded.

---

## 0. Start clean

```bash
python run.py --reset
```

Open http://localhost:8000/app/. You should see the splash screen transitioning directly to the login page. Log in as `hod@viit.ac.in` / `Hod@12345`.

**Expected:** the dashboard shows Readiness **"Not evaluated"**, Evaluated Marks **0 / 120**, Requirements Evaluated **0 of 8**, and the 8 pipeline steps are grey. So the dashboard starts empty and nothing is pre-filled.

---

## 1. Create a course

Go to **Sidebar → Criteria Workspace → C3 → Courses & Marks**, then **Add a course**:
`22UAI608C` · `Machine Learning Algorithms` · Sem `6` → **Add course**.

**Expected:** the course card appears with grey chips: 0 COs, 0 CO-PO links, 0 students.

## 2. Upload the CO-PO matrix

On the course card, click **Upload CO-PO matrix** → `sample_data/22UAI608C_co_po_matrix.csv`

**Expected:** "CO-PO matrix saved: **4 COs, 22 mappings**". The CO table shows CO1–CO4 with their statements and PO/PSO links (CO1 → PO1:3 PO2:3 PO3:2 PO5:2 PSO1:3).

## 3. Upload the marks

Click **Upload marks** → `sample_data/22UAI608C_marks.csv`

**Expected:** "Marks saved: **60 students (60 new), 16 questions (12 CIE, 4 SEE), 960 marks**".
Click **View marks** to see the full sheet. Absent students show as **AB**.

> The marks file format is `USN, Name, CIE-I Q1|CO1|10, …, SEE Q1|CO1|20|SEE`.
> Each column header carries the question name, the CO it tests, and its maximum marks. That is the question-to-CO mapping.

## 4. Course exit survey (indirect CO attainment)

In the CO table type exit-survey %: **CO1 82, CO2 61, CO3 78, CO4 74** → **Save exit survey**.

## 5. Run before approving the methodology

Go to **Dashboard → Run Criterion 3 evaluation**.

**Expected:** 3.7 and 3.8 show **NEEDS CLARIFICATION**. This is NBA 3.7.2: the program must set its attainment levels first.

## 6. Approve the attainment methodology

Go to **Sidebar → Settings** → keep the defaults → **Save & approve methodology**.
The defaults are: student attains a CO at ≥ 60 % of its marks; Level 3 ≥ 70 % of students, Level 2 ≥ 60 %, Level 1 ≥ 50 %; direct = 40 % CIE + 60 % SEE; final = 80 % direct + 20 % indirect; target level 2.

Then go to **Dashboard → Run Criterion 3 evaluation**.

**Expected:**

| | Result |
|---|---|
| Total | **28.4 / 120** (no reviewer scores or evidence yet) |
| 3.1 | 3 / 10 (only the computed part C = 3/3) |
| 3.7 | 15 / 25 (3.7.2 = 20 × 3/4 COs met) |
| 3.8 | 10.4 / 25 (B = 15 × 2.08 / 3) |
| Weak CO | **22UAI608C CO2 (0.40)** |
| Gaps | a HIGH "Weak CO" gap, plus WARNING and missing-evidence gaps |

## 7. Check the attainment maths by hand

Go to **Sidebar → CO / PO Attainment**.

**Expected CO table:**

| CO | CIE % students | CIE lvl | SEE % | SEE lvl | Direct | Exit % | Indirect | **Final** |
|---|---|---|---|---|---|---|---|---|
| CO1 | 91.67 | 3 | 90.00 | 3 | 3.00 | 82 | 3 | **3.00** |
| CO2 | 18.33 | 0 | 27.12 | 0 | 0.00 | 61 | 2 | **0.40** WEAK |
| CO3 | 73.33 | 3 | 76.27 | 3 | 3.00 | 78 | 3 | **3.00** |
| CO4 | 65.00 | 2 | 75.00 | 3 | 2.60 | 74 | 3 | **2.68** |

Check one CO yourself. For **CO4**: 65 % of students got ≥ 60 %, so the CIE level is 2. SEE 75 % gives level 3. Direct = 0.4×2 + 0.6×3 = **2.6**. The exit survey is 74 %, so indirect is level 3. Final = 0.8×2.6 + 0.2×3 = **2.68** ✓

Check one PO in **Table 3.8.1**. **PO3** is mapped from CO1 (correlation 2) and CO2 (correlation 3):
(2×3.00 + 3×0.40) / (2+3) = **1.44** ✓, and it shows in red because it is below target 2.

The page also warns: *"Not addressed by any course: PO6, PO7, PO8, PO9, PO10"*.

## 8. Score the evidence-based rubric items

Go to **Sidebar → Sub-criteria → 3.1**. You'll see 4 rows, as in the manual: A(2) B(3) **C(3, blue = computed)** D(2).
Enter **A 2, B 2.5, D 1.5** → **Save & re-evaluate**. **Expected: 3.1 = 9 / 10 PASS.**
The blue C row has no input box. Computed parts cannot be typed in.

Go to **3.7** → **A 2, B 2.5** → save. **Expected: 19.5 / 25 PASS** (2 + 2.5 + 15).
Go to **3.8** → **A 8.5** → save. **Expected: 18.9 / 25 PASS** (8.5 + 10.4).

## 9. Evidence

Go to **Sidebar → Evidence Repository** → choose any PDF, link it to *3.7*, then **Upload & link** → **Verify**.

**Expected:** the dashboard KPI **Verified Evidence** goes up by 1, and the "3.7 evidence missing" gap closes on the next run.

## 10. Continuous improvement loop (the core of Criterion 3)

1. **Sidebar → Gaps & Actions.** The **HIGH · Weak CO: 22UAI608C CO2 below target** gap is open. Add a corrective action, for example *"Remedial class + extra practice on backpropagation"*.
2. **Courses & Marks → Upload marks** → `sample_data/22UAI608C_marks_after_remedial.csv`. This is the re-assessment, where only the CO2 questions change.
3. **Gaps & Actions → Run Criterion 3.**

**Expected:**
- CO2 final goes from 0.40 to **2.80 (MET)**.
- The weak-CO gap moves to **Closed** automatically.
- 3.7.2 rises to **20 / 20**, so 3.7 = **24.5 / 25**.
- 3.8 = **22.6 / 25**.
- The total rises to **56.1 / 120**.

## 11. Virtual NBA Inspection

Go to **Sidebar → Virtual Inspection → Run Virtual NBA Inspection**.

**Expected:** the console lists 3.1 … 3.8 with PASS/WARNING/FAIL, the weak COs and gaps opened/closed, followed by a summary (PASS / WARNING / FAIL counts, readiness %, missing evidence, pending actions) and the findings list.

## 12. Prove the numbers are calculated, not hard-coded

Go to **Settings** → change *Student attains a CO at* from **60** to **70** → save → **Run Criterion 3**.

**Expected:** CO3 and CO4 also drop below target. Only **2 of 4** COs are met, the total falls to **41.05**, and new weak-CO gaps open. Set it back to 60 afterwards.

## 13. Negative tests (the system must refuse bad data)

| Try | Expected |
|---|---|
| Edit one mark in the CSV to `15` in a `/10` column and upload it | Rejected: *"Row N (USN) 'CIE-I Q1': 15.0 is outside 0-10"*, and **nothing is saved** |
| Put `abc` in a mark cell | Rejected with the row number |
| Swagger `PUT /api/v1/criterion3/rubric-scores/3.7` with `{"C": {"score": 20}}` | **422**: computed from data, cannot be entered manually |
| Log in as a faculty account and click Run | Run button hidden; the API returns **403** |

To create a faculty account: on the login page, click **Register here**. Then, as HOD, go to **Sidebar → Faculty Approvals → Approve**.

## 14. Full demo in one command

```bash
python run.py --reset --demo
```

This loads 3 courses, 180 marks rows, surveys, rubric scores and evidence.

**Expected dashboard:**
- Readiness **100 %**
- **105.33 / 120**
- **8 of 8** evaluated
- **6 of 7** documents verified
- **1 Insight** (3.4 has no evidence)
- one weak CO (ML CO2)

## 15. Automated tests

```bash
.venv/Scripts/python -m pytest backend/tests -q      # Windows
.venv/bin/python -m pytest backend/tests -q          # macOS / Linux
```

**Expected:** **256 passed**. This includes `test_criterion3_pipeline.py`, which runs steps 1 to 10 automatically.

---

### What is computed vs. scored by a person (be ready to explain this in your viva)

| Sub-criterion | Computed from your data | Scored by the reviewer from evidence |
|---|---|---|
| 3.1 (10) | C: CO coverage in CIE (3) | A process (2), B question quality (3), D feedback (2) |
| 3.2 – 3.6 | — | all parts (rubrics, SDG portfolio, etc. are qualitative in the manual) |
| 3.7 (25) | 3.7.2 attainment vs. set levels (20) | 3.7.1 A tools (2), B quality (3) |
| 3.8 (25) | B overall PO/PSO attainment level (15) | A document verification (10) |

The status thresholds (PASS ≥ 70 %, WARNING ≥ 40 %) are an **internal readiness indicator, not an official NBA grade**.
