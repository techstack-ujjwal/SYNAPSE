# DEV A — Backend, Database, AI & Clinical Logic

**Owner:** Person 1 (backend + AI) · Companion file: `PLAN_DEV_B_FRONTEND.md` · Source: `plan.md` (v2)
**Rule of the split:** Dev A never edits anything under `frontend/`. Dev B never edits anything under `backend/`, `clinical/`, `migrations/`.

---

## 0. Collision-proofing rules (identical in both files)

### 0.1 Directory ownership

| Path | Owner | Others may |
|---|---|---|
| `backend/**`, `clinical/**`, `ai/**`, `migrations/**`, `backend/tests/**` | **Dev A** | read only |
| `frontend/**`, `e2e/**`, `frontend/messages/*.json` (locales) | **Dev B** | read only |
| `contracts/openapi.json`, `contracts/examples/*.json` | **Dev A writes, Dev B reviews** | Dev B opens a comment/PR, never edits directly |
| `docs/**`, `README.md`, `plan.md` | shared, small PRs, both review | |
| `.github/workflows/**` | Dev A (backend jobs) / Dev B (frontend jobs) in **separate workflow files** | |
| `.env.example` | Dev A | Dev B requests additions |

### 0.2 Contract-first workflow (this is what prevents "I changed X while you built on old X")
1. Before a phase starts, **Dev A publishes the API contract** for that phase: updated `contracts/openapi.json` + example JSON responses, merged to `main` — **before** writing the implementation.
2. Dev B builds against a **mock server** (MSW or Prism, generated from the contract). Dev B is never blocked waiting for real endpoints.
3. When Dev A's implementation merges, Dev B flips the mock off for that feature (one-line switch) and runs the contract tests.
4. **A contract change after freeze** = a PR titled `contract: ...` that both approve. Breaking changes get a new field/version, never an in-place rename.

### 0.3 Git rules
- Branch names: `a/<phase>-<topic>` (Dev A), `b/<phase>-<topic>` (Dev B).
- Short-lived branches (≤ 2 days), merge to `main` via PR, the other dev reviews anything touching `contracts/` or `docs/`.
- Rebase on `main` daily. Never push to the other dev's branch.
- CI must be green to merge. Backend CI and frontend CI are separate, so one person's failing tests don't block the other's merge.
- Feature flags (`voice`, `ai_rx`, `no_doctor_mode`, `live_queue`) are defined in the contract; both sides respect them.

### 0.4 Sync points (the only moments you must meet)

| ID | When | What happens | Who waits for whom |
|---|---|---|---|
| **S0** | Day 1 | Agree branch rules, contract folder, mock tooling, pick the demo date (D-1) | none |
| **S1** | End of P0 | Backend is split into modules **and** `page.tsx` is split into feature components; both merged, CI green. Old files frozen. | both finish P0 independently, then merge in the order: A then B |
| **S2** | Start of P1 | Dev A publishes auth contract (`/auth/*`, session cookie behaviour, error shapes, role claims) | B waits only for the *contract*, not the code |
| **S3** | End of P1 | Auth live on dev env; B swaps mocks for real login | B waits for A |
| **S4** | Start of P2 | Queue contract + SSE event schema frozen | B waits for contract only |
| **S5** | End of P3 | Symptom/triage/escalation contract frozen; vignette bank passes | B builds UI from contract earlier |
| **S6** | Start of P4/P6 | Report schema v1 + prescription draft contract frozen | B waits for contract only |
| **S7** | End of P7 | Theme merged; **feature freeze on UI components** | A stops adding fields that need new UI |
| **S8** | P8 | Joint regression, demo rehearsals | both |

---

## 1. Dev A phase plan

Legend: 🔴 blocks Dev B (real integration), 🟡 Dev B can proceed on mocks, 🟢 independent.

### A-P0 — Stabilise backend (Week 0–1) 🟢
- Rotate the exposed OpenAI key (B-19) **today**; remove `.env` from the archive; add `.env.example`; add secret scanning to CI.
- Write **characterisation tests** around the current endpoints (they define "behaviour must not change" for the split).
- Split `backend/main.py` into `app/{api,core,models,schemas,services,clinical,ai}` with **no behaviour change**.
- Backend CI: ruff, mypy, pytest.
- Quick fixes (backend-side): **B-05** (token/phrase matching with negation), **B-08** (remove hardcoded "None reported"; return "not assessed"), **B-09** (remove Male/30 default), **B-11** (rename seed doctors), **B-12** (return proper HTTP errors), **B-18** (hide doctor phone numbers).
- **B-04 (shared bug):** change the status endpoint to accept a JSON body (as the UI already sends). Publish it in the contract; Dev B removes the optimistic update.
- Publish the first real `contracts/openapi.json` generated from FastAPI.
- **Exit:** G0 (backend half). → **S1**

### A-P1 — Foundation: Postgres + Auth (Week 1–3) 🔴 (S2 contract first, S3 code)
Requirements **#10, #6**.
1. Contract first: `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/otp/*`, `/me`, role names, error shapes, cookie rules → **S2**.
2. SQLAlchemy 2.x models + Alembic for the Section 5.3 schema (UUID PKs, FKs, indexes, soft delete).
3. Neon dev/staging (Singapore, synthetic data only), pooled vs direct connection strings, least-privilege roles.
4. Auth: Argon2id, httpOnly/Secure/SameSite cookies, refresh rotation, CSRF, rate limiting, lockout, TOTP/OTP for doctor/admin.
5. RBAC + object-level checks on every endpoint; actor identity from session, never request body.
6. Doctor identity: `id`, `doctor_code` (sequence, immutable), `employee_code`, `registration_no`; onboarding → approve → suspend flow endpoints (`/admin/doctors/*`).
7. Patient UHID, consent records, append-only `audit_log`.
8. Remove `allow_origins=['*']`.
9. Synthetic seed script (≥5 patients with varied histories, labelled synthetic).
- **Exit:** G1. Fresh DB from migrations only; forged `doctor_id` has no effect; suspended doctor cannot log in. → **S3**

### A-P2 — Live queue backend (Week 3–4) 🔴 (S4)
Requirement **#12** (server side).
- Contract + **SSE event schema** frozen first (`queue.updated`, `token.called`, `escalation.created`, heartbeat, event IDs).
- `queues`, `queue_tokens`, `token_counters`; race-safe tokens `JMCH-OPD-042`; unique `(queue_id, service_date, seq)`; one active token per patient per queue; idempotency keys.
- State machine with server-side role-checked transitions; priority-aware ordering with logged overrides.
- `GET /events/queue` (SSE), per-stream authorisation, polling fallback endpoint.
- Wait-estimate service (EWMA, only after minimum sample).
- **Exit:** 200 parallel token requests → zero duplicates; patient cannot read another token by ID.

### A-P3 — Clinical safety core (Week 3–6) 🟡
Requirements **#4, #11** (all server logic).
- Structured symptom model + `symptom_records`.
- Red-flag layer (rules + per-language phrase lists + LLM second net, logical OR; LLM can only raise urgency); runs on every utterance and vitals.
- Triage engine with reason codes; `EMERGENCY/URGENT/ROUTINE/CANNOT_ASSESS`.
- Adaptive question engine driven by clinician-authored data files.
- Contradiction/uncertainty handling; AI-unavailable mode (rules-only, neutral wording).
- Replace `ai_determine_priority` (B-10).
- **No-doctor mode:** doctor availability/schedule model, escalations table + endpoints, approved-knowledge retrieval, safe wording library, "must not" guardrails, disabled Rx engine in this mode.
- **Vignette bank + evaluation harness in CI** (needs clinical lead, D-4). Targets set *before* testing.
- Contract for symptom/triage/escalation responses frozen at start of phase so Dev B can build the UI.
- **Exit:** G2 clinical v1.

### A-P4 — Records, history, personalisation (Week 5–7) 🟡
Requirements **#5, #8, #9** (backend).
- `ClinicalReport` schema v1 (10 sections), revisions, sign-off, server-side PDF (WeasyPrint, Noto fonts, letterhead slot).
- `clinical_facts` store with provenance; migrate legacy visit blobs as `legacy_import / needs_review`.
- Lab normalisation + versioned reference-range table.
- Retrieval service (SQL + recency + category), ≤300-token source-linked history brief, question planner, AI context log, prompt hygiene (strip PII, injection defence).
- Endpoints: timeline, previous-vs-current diff, reconciliation, `/reports/{id}/revisions`, `/reports/{id}/pdf`.
- **Exit:** every fact links to its source; no cross-patient leakage tests.

### A-P5 — Voice backend (Week 4–8, parallel) 🟡
Requirement **#1** (server side).
- Voice bake-off: Option A pipeline vs Option B realtime; record p50/p95 latency, WER per language, red-flag recall.
- `/ws/voice` WebSocket gateway, deterministic dialogue orchestrator, streaming ASR/LLM/TTS adapters, red-flag gate before every reply, low-confidence confirmation turns, resume-after-failure state on server, no raw audio stored.
- Marwari glossary + Hindi fallback; define support with JMCH (D-10).
- Contract for WS message types frozen at phase start.

### A-P6 — AI-assisted prescribing backend (Week 7–9) 🟡
Requirement **#7**.
- Medication catalogue + templates (D-6), admin CRUD with audit.
- Suggestion engine restricted to catalogue; structured output with rationale, sources, warnings, missing data.
- Deterministic checks: allergy, interaction, duplicate therapy, dose/age/pregnancy/renal (licensed or pharmacist-curated source; "check unavailable" otherwise).
- `/rx/drafts`, `/rx/{id}/approve` requiring re-auth; final Rx immutable; automated test proving AI cannot create a final Rx.

### A-P7 — Support Dev B's theme (Week 6–10) 🟢
- PDF/letterhead/token/prescription templates use the theme tokens from `docs/design-tokens.md` (owned by Dev B).
- Fix contract gaps found during theming; no new fields after S7.

### A-P8 — Hardening (Week 10–12)
- Load/concurrency tests (k6/Locust), restore drill, security headers, upload hardening, ASVS L1 checklist, pen-test prep.
- Backend regression, failure drills (DB down → clean 503), demo health endpoint, `pg_dump` backup job, runbooks (restore, key rotation, incident).
- Demo data reset script.

---

## 2. What Dev A needs from Dev B (and when)

| Needs | From B | By |
|---|---|---|
| Typed API client generated from contract, reports contract issues | B-P0 | S1 |
| Design tokens file for PDF/templates | B-P0/P7 | P7 |
| Bug reports using the shared bug register format | continuous | weekly |
| Confirmation that SSE/WS events render as designed | B-P2/P5 | per phase |

## 3. Weekly rhythm
Monday: 20-min sync, review next contract(s). Wednesday: merge-to-`main` checkpoint. Friday: integration run on dev env, update bug register and `plan.md` Section 2.2.
