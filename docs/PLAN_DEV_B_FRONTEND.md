# DEV B — Frontend, UI Features, Theme & QA

**Owner:** Person 2 (UI + feature work + bug fixing) · Companion file: `PLAN_DEV_A_BACKEND_AI.md` · Source: `plan.md` (v2)
**Rule of the split:** Dev B never edits anything under `backend/`, `clinical/`, `ai/`, `migrations/`. Dev A never edits `frontend/` or `e2e/`.

---

## 0. Collision-proofing rules (identical in both files)

### 0.1 Directory ownership

| Path | Owner | Others may |
|---|---|---|
| `backend/**`, `clinical/**`, `ai/**`, `migrations/**`, `backend/tests/**` | **Dev A** | read only |
| `frontend/**`, `e2e/**`, `frontend/messages/*.json` (locales) | **Dev B** | read only |
| `contracts/openapi.json`, `contracts/examples/*.json` | **Dev A writes, Dev B reviews** | Dev B comments/PRs, never edits directly |
| `docs/**`, `README.md`, `plan.md` | shared, small PRs, both review | |
| `.github/workflows/**` | A (backend jobs) / B (frontend jobs), **separate workflow files** | |
| `docs/design-tokens.md` | **Dev B** | A reads for PDF/templates |

### 0.2 Contract-first workflow (prevents building on stale code)
1. **Dev A publishes the API contract** for each phase (OpenAPI + example JSON) and merges it to `main` **before** implementing.
2. **You build against a mock server** (MSW or Prism generated from `contracts/openapi.json`). You are never blocked by backend code, only by the *contract* (a day or two of notice at most).
3. When Dev A's implementation merges, you flip the mock off for that feature (single env flag per feature) and run contract tests.
4. Contract change after freeze = `contract: ...` PR that both approve. Breaking changes use new fields, not renames.

### 0.3 Git rules
- Branches: `b/<phase>-<topic>`; ≤ 2 days; PR to `main`; rebase daily; other dev reviews anything in `contracts/` or `docs/`.
- Frontend CI is separate from backend CI.
- Feature flags (`voice`, `ai_rx`, `no_doctor_mode`, `live_queue`) come from the contract; respect them in UI.

### 0.4 Sync points

| ID | When | What happens |
|---|---|---|
| **S0** | Day 1 | Agree rules, mock tooling, demo date |
| **S1** | End P0 | Backend split + `page.tsx` split both merged, CI green. Merge order: A then B. Old monolith files frozen |
| **S2** | Start P1 | A publishes auth contract; you start login UI on mocks |
| **S3** | End P1 | Real auth live; you swap mocks for real |
| **S4** | Start P2 | Queue + SSE contract frozen |
| **S5** | End P3 | Symptom/triage/escalation contract frozen |
| **S6** | Start P4/P6 | Report schema v1 + Rx draft contract frozen |
| **S7** | End P7 | Theme merged; UI component feature freeze |
| **S8** | P8 | Joint regression + rehearsals |

---

## 1. Dev B phase plan

Legend: ⏳ waits for A's *contract* only · 🔴 real integration waits for A's code · 🟢 independent.

### B-P0 — Stabilise frontend (Week 0–1) 🟢
- Remove `typescript.ignoreBuildErrors`; enable strict TS + ESLint; log the resulting type errors as the first bug-register entries.
- Add global error boundary and a **typed API client generated from `contracts/openapi.json`** (errors surface, never swallowed with `.catch(() => {})`).
- **Characterisation tests** (Playwright smoke) of the current patient, doctor flows before refactor.
- Split the 1,661-line `app/[locale]/page.tsx` into feature modules (landing / register / returning / intake / summary / token / dashboard) with **no behaviour change**.
- Switch to route groups `(patient)`, `(doctor)`, `(admin)`, `(display)` (admin/display empty shells for now).
- Design-token skeleton (`docs/design-tokens.md`, CSS variables + Tailwind theme) and a **clearly marked placeholder brand slot** (never a fake JMCH logo).
- **B-04 (shared bug):** remove optimistic UI update on queue buttons; show real success/error; adapt to Dev A's body-based endpoint.
- **B-16:** remove the face-scan icon unless D-8 says the feature is wanted.
- Set up mock server (MSW/Prism) + frontend CI (type-check, lint, vitest, Playwright smoke).
- Set up bug register file `docs/BUGS.md` (ID, steps, expected/actual, severity, owner, fix, regression test, retest).
- **Exit:** G0 (frontend half) → **S1**

### B-P1 — Auth & identity UI (Week 1–3) ⏳ S2 → 🔴 S3
Requirements **#6, #2 (start)**.
- Login screens for doctor/admin/registration (password + OTP/TOTP step), patient OTP flow (stubbed visibly until D-9), logout, idle-timeout warning, session-expired handling.
- Remove `localStorage('doctor')` identity entirely; use cookie session via `/me`.
- Route guards per role + friendly 403/401 pages; role-escalation attempts redirect safely.
- **Admin console shell:** layout, nav, doctor management screens (create → pending → verify → approve → suspend → reassign), audit-log viewer.
- Consent screens (versioned notice, separate AI + audio consent) in all locales.
- Base component library on tokens: buttons, inputs, selects, tables, tabs, dialogs, toasts, badges, banners, skeletons, empty/error/loading patterns.
- E2E: new doctor onboarding → approval → first login → suspension → blocked login.

### B-P2 — Live queue UI (Week 3–4) ⏳ S4 → 🔴
Requirement **#12** (UI side).
- SSE client with reconnect/backoff, event-ID resume, heartbeat, **polling fallback**, offline banner.
- **Admin queue board:** per-queue live lists, check-in / call next / in-progress / complete / cancel / no-show / recall / transfer, walk-in registration, "requires attention" lane, filters, search, keyboard shortcuts.
- **Doctor dashboard:** own queue, Call next, in-progress timer, open consultation workspace.
- **Patient queue view:** token (`JMCH-OPD-042`), position, status, assigned doctor, wait *range* wording, neutral emergency-reorder message, no other patients' data.
- **TV display mode** `(display)`: now-serving tokens only, large type, auto-reconnect.
- E2E: admin + patient in two browsers stay in sync; killing SSE falls back to polling.

### B-P3 — Clinical safety & no-doctor UI (Week 3–6) ⏳ S5 → 🟡
Requirements **#4, #11** (UI).
- Intake progress UI driven by the symptom contract (button-card answers, body diagram for pain location, confirm-low-confidence prompts).
- Emergency state screen (clear, calm instruction + local emergency number slot), `CANNOT_ASSESS` and "AI unavailable – manual intake" states (never an empty "no red flags").
- Admin/doctor **escalation inbox** with age timers and emergency alerts (sound + banner).
- **No-doctor mode UI:** persistent "No doctor is available right now; this is general information" banner, callback/queue/message actions, "NOT REVIEWED" report badge, disabled prescription UI.
- Priority/triage badges with reason codes visible to doctors.
- Fix remaining UI-side bugs from the register.

### B-P4 — Reports, history, patient dashboard (Week 5–7) ⏳ S6 → 🟡
Requirements **#5, #8, #9** (UI).
- **Report viewer** (10 fixed sections, provenance chips, "Not recorded" for empty sections, revision history with diff, sign-off), print stylesheet (A4), PDF download button.
- **Doctor "Before consultation" panel:** visit timeline, previous-vs-today view, vitals/lab trend charts with ranges, allergy banner distinguishing *"No known allergies recorded"* vs *"Not recorded / unknown"*, reconciliation UI, "information used" list.
- Three-way labelling with colour + icon + text: 🟦 clinician-recorded · 🟨 patient-reported · 🟪 AI-generated.
- Patient dashboard rebuilt on authenticated APIs: plain-language visit summaries, follow-ups, reports with the existing parameter cards, timeline.
- Consultation workspace two-pane layout (evolved from the existing doctor review page).
- Returning-patient flow: "Shall I continue from last time?" with private-device handling.

### B-P5 — Voice UI (Week 4–8, parallel) ⏳ → 🟡
Requirement **#1** (browser side).
- `AudioWorklet` + VAD, `getUserMedia` with echo cancellation, WS client for `/ws/voice`.
- Large **mic status** (listening / thinking / speaking / muted / error), Repeat, Pause, **"Use buttons instead"** fallback; no transcript by default, a "show what I heard" toggle for staff/accessibility.
- **Barge-in:** stop TTS playback immediately on patient speech; cancel in-flight reply.
- Chunked TTS playback, silence cue and one gentle re-prompt.
- Failure UI: no mic permission, no device, noisy room, network drop, TTS failure → spoken/visual message + automatic tap-based fallback + resume.
- Test in Chromium/Safari iOS/Chrome Android; one low-end Android.

### B-P6 — Prescription review UI (Week 7–9) ⏳ S6 → 🟡
Requirement **#7** (UI).
- Side-by-side: patient context left, AI suggestions right; per-item **Accept / Modify / Reject** (+ reason); no default "accept all".
- Warning rendering: **block** (needs override reason), **warn**, **info**, and *"Interaction check not available"* (never green).
- Banner: *"AI-generated draft — not a prescription until approved by Dr. X."*
- Searchable catalogue + template picker; "Approve and sign" with re-auth dialog; prescription PDF preview; patient copy in their language labelled as translation.
- Hidden when `no_doctor_mode` or `ai_rx` flag is off.

### B-P7 — JMCH theme (Week 6–10) 🟢
Requirement **#2** (the visual pass).
- Apply official assets/colours/fonts when D-2 arrives (placeholder until then). Brand change = token change.
- Fonts: brand font if licensed + **Noto Sans Devanagari**; check all 23 locale scripts for clipping.
- Role layouts: patient (mobile-first), doctor (two-pane), admin (dense tables/dashboard), registration desk, queue display.
- Consistent loading / empty / error / success / offline / session-expiring states.
- Letterhead component shared with Dev A's PDF templates (supply tokens file).
- Accessibility: WCAG 2.2 AA, keyboard nav, visible focus, labels, reduced motion, 44px targets.
- Visual-regression baselines at 360–430 / 768–1024 / ≥1280.
- **S7: feature freeze on UI components.**

### B-P8 — QA, hardening, demo (Week 10–12) 🟢
Requirement **#3** (continuous throughout, concentrated here).
- Playwright across Chromium/Firefox/WebKit + mobile emulation; axe accessibility scans; automate the four complete workflows from plan §7.3.
- Failure-mode matrix as named tests: session expiry mid-form, refresh on every route, back/forward, double submit, flaky network, mic denied/revoked, unsupported browser, interrupted TTS, long/Unicode input, empty dashboards, role-escalation attempts, forged tokens, bad uploads.
- Published pass/fail report; zero open Sev-1/Sev-2.
- Demo build frozen and tagged one week before the date; demo script; pre-recorded voice fallback clip; offline-capable demo mode.

---

## 2. What Dev B needs from Dev A (and when)

| Needs | From A | By |
|---|---|---|
| Real `contracts/openapi.json` + examples | A-P0 | S1 |
| Auth contract, then auth code | A-P1 | S2, S3 |
| Queue + SSE schema, then code | A-P2 | S4 |
| Symptom/triage/escalation contract | A-P3 | start of phase |
| Report schema v1, facts/timeline contract | A-P4 | S6 |
| WS message contract for voice | A-P5 | start of phase |
| Rx draft/approve contract | A-P6 | S6 |
| Seed data + dev environment URL | A-P1 | S3 |

If a contract is late by more than 2 days, build against your own mock shape and file a `contract:` PR, so the work is not lost.

## 3. Weekly rhythm
Monday: 20-min sync, review next contract(s). Wednesday: merge-to-`main` checkpoint. Friday: integration run on dev env, update `docs/BUGS.md` and `plan.md` Section 2.2.
