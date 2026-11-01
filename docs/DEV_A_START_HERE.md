# Dev A (Backend/AI) - Your Phases and How to Start

## Quick Answer: How to Work Together

**You have TWO options:**

### Option 1: Sequential (Recommended for Now)
- You complete **Phases A-P0 and A-P1** first (Database + Auth)
- Once those are done, Dev B starts working in parallel with you
- This is safer because Dev B needs your DB schema and Auth contracts to build their UI

### Option 2: Parallel from Day 1
- You work on your phases, Dev B works on their phases simultaneously
- Dev B uses **mock servers** based on your API contracts
- Requires more coordination but faster overall

**My recommendation:** Start with Option 1 (Sequential). It's simpler and less error-prone.

---

## Your Phases (Dev A - Backend/AI Focus)

You own these directories:
- `backend/` - All backend code
- `clinical/` - Clinical rules and protocols
- `ai/` - AI provider adapters
- `migrations/` - Database migrations
- `backend/tests/` - Backend tests

Dev B never touches these. You never touch `frontend/` or `e2e/`.

---

## Phase A-P0: Stabilise Backend (START HERE)

**Goal:** Clean up the codebase, fix critical bugs, set up foundation

### Tasks (do these in order):

1. **Rotate the exposed OpenAI key** (CRITICAL - Security)
   - The `.env` file has a real-looking OpenAI key exposed
   - Generate a new key from OpenAI dashboard
   - Update `.env` with the new key
   - Never commit `.env` to git

2. **Clean repository**
   - Remove `node_modules/` from git (already in .gitignore)
   - Remove `.next/` from git (already in .gitignore)
   - Ensure `.env` is in `.gitignore`

3. **Write characterisation tests for `backend/main.py`**
   - These tests document current behavior
   - Purpose: Ensure refactoring doesn't break existing functionality
   - Test all existing endpoints (`/patients`, `/doctors`, `/queue`, etc.)

4. **Split `backend/main.py` into modules**
   - Current: One 2,034-line file
   - Target structure:
     ```
     backend/
       app/
         api/        # Route handlers
         core/       # Config, security
         models/     # SQLAlchemy models
         schemas/    # Pydantic schemas
         services/   # Business logic
         clinical/   # Clinical rules
         ai/         # AI adapters
         tests/      # Tests
     ```
   - **Important:** Split WITHOUT changing behavior (use characterisation tests to verify)

5. **Set up backend CI**
   - Add `ruff` for linting
   - Add `mypy` for type checking
   - Add `pytest` for testing
   - Create `.github/workflows/backend-ci.yml`

6. **Fix critical bugs (backend-side):**
   - **B-05:** Fix specialty matching (substring matching is wrong)
   - **B-08:** Remove hardcoded "None reported" in summary fallback
   - **B-09:** Remove Male/30 default in report analysis
   - **B-11:** Rename seed doctors (currently has "Dr. Anus Kumar")
   - **B-12:** Return proper HTTP errors (not 200 with `{ok:false}`)
   - **B-18:** Hide doctor phone numbers from public endpoint

7. **Fix B-04 (shared bug with Dev B)**
   - Change queue status endpoint to accept JSON body (UI already sends this)
   - Publish API contract for this change

8. **Publish first API contract**
   - Generate `contracts/openapi.json` from FastAPI
   - Add example JSON responses in `contracts/examples/`
   - This is what Dev B will use to build their UI

### Exit Criteria (when to move to next phase):
- ✅ Backend code split into modules
- ✅ Characterisation tests passing
- ✅ All critical bugs (B-04, B-05, B-08, B-09, B-11, B-12, B-18) fixed
- ✅ CI green (lint, type-check, tests)
- ✅ API contract published

---

## Phase A-P1: Foundation - Postgres + Auth

**Goal:** Move from in-memory SQLite to PostgreSQL, add real authentication

**Dependencies:** Phase A-P0 complete

### Tasks:

1. **Design PostgreSQL schema** (all tables from original plan):
   - `users` - Authenticated accounts
   - `patients` - Demographics with UHID
   - `consents` - Versioned consent records
   - `doctors` - Clinician profiles
   - `departments` - OPD departments
   - `visits` - Encounters
   - `queue_tokens` - Tokens
   - `token_counters` - Race-safe sequences
   - `intake_sessions` / `intake_turns` - Voice/chat turns
   - `symptom_records` - Structured symptoms
   - `clinical_facts` - Longitudinal fact store
   - `documents` - Uploaded reports
   - `lab_results` - Normalised parameters
   - `reports` / `report_revisions` - Structured reports
   - `prescription_drafts` / `prescription_items` / `prescriptions`
   - `medication_catalog`, `rx_templates` - Formulary
   - `escalations` - Emergency events
   - `audit_log` - Append-only audit

2. **Set up SQLAlchemy 2.x models**
   - Create models for all tables
   - Use UUID primary keys
   - Add foreign keys everywhere
   - Add indexes on foreign keys and common query paths
   - Add `created_at/updated_at` timestamps

3. **Create Alembic migrations**
   - Initial migration to create all tables
   - Ensure migrations are reproducible from empty DB
   - Test migration rollback

4. **Set up Neon PostgreSQL**
   - Create Neon dev project (Singapore region for demo)
   - Configure pooled connection string for app
   - Configure direct connection for migrations
   - Set up least-privilege roles (`app_rw`, `migrator`, `readonly_reports`)
   - Add TLS (`sslmode=require`)

5. **Implement authentication**
   - Add Argon2id password hashing
   - Create `/auth/login` endpoint
   - Create `/auth/refresh` endpoint
   - Create `/auth/logout` endpoint
   - Implement httpOnly/Secure/SameSite cookies
   - Add refresh token rotation
   - Add CSRF protection
   - Add rate limiting on login
   - Add account lockout after failed attempts

6. **Implement RBAC (Role-Based Access Control)**
   - Roles: `patient`, `doctor`, `admin`, `super_admin`
   - Middleware to check role on every endpoint
   - Object-level checks (doctor can only see their patients)
   - Actor identity from session, never from request body

7. **Implement doctor identity system**
   - `doctor.id` - UUID (immutable, internal)
   - `doctor_code` - Human-readable (e.g., `JMCH-DR-0001`)
   - `employee_code` - HR identifier
   - `registration_no` - Medical council registration
   - Onboarding → approve → suspend flow
   - Endpoints: `/admin/doctors/*`

8. **Add patient UHID**
   - Hospital patient ID (unique)
   - Stored in `patients` table
   - Separate from internal UUID

9. **Add consent records**
   - Versioned consent notices
   - Separate consent for AI processing
   - Separate consent for audio recording
   - Withdrawal tracking

10. **Implement audit log**
    - Append-only table
    - Every write operation logs: actor, role, action, entity, before/after hash, IP, time
    - Audit middleware automatically adds entries

11. **Remove `allow_origins=['*']`**
    - Allow only known frontend origins
    - Add security headers (CSP, HSTS, frame-ancestors)

12. **Create synthetic seed script**
    - ≥5 patients with varied histories
    - Clearly labelled as synthetic data
    - JMCH-approved doctor names (no more "Dr. Anus Kumar")

13. **Publish Auth API contract**
    - Document all auth endpoints
    - Document cookie behavior
    - Document error shapes
    - Document role claims
    - This is what Dev B needs to build login UI

### Exit Criteria:
- ✅ Fresh database built from migrations only
- ✅ Auth endpoints working and tested
- ✅ Forged `doctor_id` in request body has no effect
- ✅ Suspended doctor cannot log in
- ✅ Every write produces audit log entry
- ✅ Auth contract published

---

## Phase A-P2: Live Queue Backend

**Goal:** Race-safe token system, SSE live updates

**Dependencies:** Phase A-P1 complete

### Tasks:

1. **Design queue tables**
   - `queues` - Queue definitions
   - `queue_tokens` - Token records
   - `token_counters` - Race-safe sequences

2. **Implement race-safe token generation**
   - Token label: `JMCH-<QUEUE>-<NNN>` (e.g., `JMCH-OPD-042`)
   - Sequence per queue per day
   - Use DB transaction with `UPDATE ... RETURNING` or `SELECT ... FOR UPDATE`
   - Unique constraint on `(queue_id, service_date, seq)`
   - One active token per patient per queue (unique partial index)
   - Idempotency keys to prevent double-submit

3. **Implement queue state machine**
   - States: `issued → checked_in → called → in_consultation → completed`
   - Additional states: `cancelled`, `no_show`, `skipped/recalled`, `transferred`
   - Server-side validation on every transition
   - Role checks (only admin can cancel, only doctor can complete)
   - Timestamped transitions
   - Audit logged

4. **Implement priority-aware ordering**
   - Default: FIFO within priority class
   - Emergency override (logged, visible)
   - Configurable ordering rule

5. **Create SSE endpoint**
   - `GET /events/queue`
   - Event types: `queue.updated`, `token.called`, `escalation.created`
   - Heartbeat events
   - Event IDs for resume
   - Per-stream authorisation (patients only get their own events)
   - Polling fallback endpoint

6. **Implement wait-estimate service**
   - EWMA (Exponentially Weighted Moving Average)
   - Only shown after minimum sample (don't show on first few tokens)
   - Returns range, not exact time

7. **Write concurrency tests**
   - 200 parallel token requests
   - Verify zero duplicates
   - Verify gapless sequence (or explained gaps)

8. **Publish Queue + SSE contract**
   - Document queue endpoints
   - Document SSE event schema
   - This is what Dev B needs for queue UI

### Exit Criteria:
- ✅ 200 concurrent token requests → zero duplicates
- ✅ Patient cannot read another token by ID guessing
- ✅ Queue + SSE contract published

---

## Phase A-P3: Clinical Safety Core

**Goal:** Structured symptom model, red-flag screening, triage engine

**Dependencies:** Phase A-P1 complete, Clinical lead input needed

### Tasks:

1. **Design symptom model**
   - `symptom_records` table
   - Fields: chief complaint, onset, duration, severity, location, character, progression, aggravating/relieving factors, associated symptoms, pertinent negatives, relevant history
   - Each field: `value | unknown | not_asked | declined`
   - `source` field (patient_reported, clinician_recorded, etc.)
   - `confidence` field
   - `visit_id` foreign key

2. **Design clinical facts store**
   - `clinical_facts` table
   - Categories: allergy, condition, medication, vital, lab, etc.
   - Status: `confirmed | reported | unknown | refuted`
   - Source type and source reference
   - Recorded by and recorded at

3. **Implement red-flag screening layer**
   - Deterministic rules (code, not prompts)
   - Keyword/phrase lists per language (Hindi, Hinglish, Marwari, English)
   - Example: "chest pain + sweating + breathlessness" → EMERGENCY
   - Rules reviewed by clinical lead

4. **Add LLM classifier as second safety net**
   - LLM reads same utterance
   - Logical OR with rules (either firing triggers escalation)
   - LLM can only raise urgency, never lower rules result
   - Pin model version

5. **Run screening on every utterance**
   - Not just first utterance
   - Also run on submitted vitals
   - Log why urgency was assigned

6. **Implement triage engine**
   - Output: `EMERGENCY | URGENT | ROUTINE | CANNOT_ASSESS`
   - Include reason codes (e.g., "chest pain + age>50 + sweating")
   - Store with visit

7. **Implement adaptive questioning engine**
   - Per-complaint question sets (headache, fever, cough, etc.)
   - Data files (versioned), not hardcoded in prompts
   - Authored/reviewed by clinicians
   - Next question = highest-value unfilled slot
   - Red-flag follow-ups exceed question cap

8. **Handle uncertainty and contradictions**
   - Detect: "no fever" vs temperature 39°C
   - Detect: Implausible values
   - Detect: Low ASR confidence
   - Response: Re-ask once → record as `unknown` → flag to doctor
   - If safety-relevant slots stay unknown, raise urgency

9. **Replace old priority system**
   - Remove `ai_determine_priority` (B-10)
   - Use new triage engine

10. **Implement AI-unavailable mode**
    - Rules-only red-flag screening
    - Neutral wording ("This section was not assessed")
    - Never empty "no red flags"

11. **Create vignette bank**
    - 150-300 cases written/labelled by clinical lead
    - Span common OPD complaints, emergencies, tricky look-alikes
    - Cases in Hindi, Hinglish, English (Marwari subset)
    - Gold label: clinician-agreed urgency + expected red flags

12. **Implement evaluation harness in CI**
    - Metrics: under-triage rate (primary), sensitivity, specificity, PPV, over-triage rate
    - Regression: runs on every change to rules/prompts
    - Model/prompt change that worsens under-triage is blocked

13. **Publish Symptom/Triage/Escalation contract**
    - Document symptom schema
    - Document triage output format
    - Document escalation structure
    - This is what Dev B needs for clinical UI

### Exit Criteria:
- ✅ Red-flag recall on agreed emergency set meets clinical lead target
- ✅ Every false negative reviewed
- ✅ Vignette bank passing in CI
- ✅ Symptom/triage/escalation contract published

---

## Phase A-P4: Records, History, Personalisation

**Goal:** Fixed report schema, fact store, history retrieval

**Dependencies:** Phase A-P1 complete, Phase A-P3 complete

### Tasks:

1. **Design ClinicalReport schema v1**
   - 10 fixed sections (from requirements)
   - Typed fields for each section
   - `schema_version` field
   - JSON body

2. **Implement report generation flow**
   - AI proposes field values via structured outputs
   - Backend validates against schema
   - Reject/repair loop
   - Template renders to HTML/PDF
   - AI never decides layout

3. **Add provenance chips**
    - Inline labels: clinician_recorded, patient_reported, lab_document, vitals, ai_inferred
    - Stored with each fact

4. **Implement report revisions**
    - Report body immutable per revision
    - Doctor edits create new revision with diff
    - Sign-off locks revision
    - Audit log entry for each

5. **Implement server-side PDF generation**
    - WeasyPrint or similar
    - JMCH letterhead (placeholder until official assets)
    - A4 format
    - Page numbers
    - Patient ID and visit ID on every page
    - Embed Noto fonts for Hindi/Marwari
    - Print CSS

6. **Migrate legacy visit blobs**
    - Existing `visits` summary blobs
    - Migrate to `clinical_facts` with `source_type = legacy_import`
    - Add `needs_review` flag

7. **Implement lab normalisation**
    - Normalise names/units (e.g., Hb g/dL)
    - Store in `lab_results` table
    - Reference ranges from versioned table
    - Adjust by age/sex

8. **Implement retrieval service**
    - SQL filters + recency + category
    - ≤300-token source-linked history brief
    - Each bullet has `fact_id`
    - Never send whole history to model

9. **Implement question planner**
    - Compare brief vs current complaint
    - Generate verification questions
    - "Last time you mentioned headaches. Are they still happening?"
    - Never state old condition as current fact

10. **Add AI context logging**
    - Log which fact IDs were included in each prompt
    - For audit and debugging

11. **Implement prompt hygiene**
    - Strip name/phone
    - Use age band and sex only when clinically needed
    - Treat retrieved text as data, not instructions (prompt-injection defence)

12. **Create endpoints**
    - Timeline endpoint
    - Previous-vs-current diff endpoint
    - Reconciliation endpoint
    - `/reports/{id}/revisions`
    - `/reports/{id}/pdf`

13. **Publish Report/Facts/Timeline contract**
    - Document report schema
    - Document fact structure
    - Document timeline format
    - This is what Dev B needs for report/history UI

### Exit Criteria:
- ✅ Every fact links to its source
- ✅ No cross-patient leakage in tests
- ✅ Report/facts/timeline contract published

---

## Phase A-P5: Voice Backend

**Goal:** Speech-to-speech intake, WebSocket gateway

**Dependencies:** Phase A-P3 complete (symptom model needed for turn-taking)

### Tasks:

1. **Voice bake-off**
   - Option A: Pipeline (browser VAD → streaming ASR → orchestrator + LLM → streaming TTS)
   - Option B: Native realtime speech-to-speech model API
   - Record metrics: p50/p95 latency, WER per language, red-flag recall
   - Choose based on measured results

2. **Implement conversation orchestrator**
   - Deterministic state machine
    - Decides what slot to fill next
    - Driven by symptom model
    - LLM only phrases questions, extracts values

3. **Create WebSocket endpoint**
   - `/ws/voice`
   - Streaming audio in both directions
   - State management on server
   - Resume-after-failure capability

4. **Implement streaming ASR adapter**
   - Whisper adapter (default)
   - Language hints for Hindi/Hinglish
   - Marwari glossary
   - Swapable interface

5. **Implement streaming TTS adapter**
   - Default: OpenAI tts-1
   - Swapable interface
   - Chunked playback

6. **Add red-flag gate before every reply**
   - Run red-flag screening on every utterance
   - If emergency: stop and escalate
   - Never send reply without checking

7. **Implement low-confidence confirmation**
   - If ASR confidence low: "Did you say three days?"
   - Extract structured value only after confirmation

8. **Add Marwari support**
   - Glossary of common terms
   - Hindi fallback
   - Measure and report accuracy
   - Define support honestly (D-10)

9. **Implement resume-after-failure**
    - Server holds session state
    - If connection drops, resume where left off
    - No raw audio stored (transcripts only)

10. **Publish WebSocket message contract**
    - Document WS message types
    - Document audio format
    - Document state transitions
    - This is what Dev B needs for voice UI

### Exit Criteria:
- ✅ Voice gateway handles streaming audio
- ✅ Red-flag gate before every reply
- ✅ Marwari glossary in place
- ✅ WebSocket contract published

---

## Phase A-P6: AI-Assisted Prescribing Backend

**Goal:** Prescription suggestion engine with safety checks

**Dependencies:** Phase A-P4 complete (report schema), Phase A-P3 complete (clinical facts)

### Tasks:

1. **Design medication tables**
   - `medication_catalog` - Hospital formulary
   - `rx_templates` - Prescription templates per speciality

2. **Implement medication catalogue**
   - Generic/brand names
   - Strength, forms, routes
   - Usual frequencies
   - Formulary status
   - ATC code if available
   - Admin CRUD with audit

3. **Implement prescription templates**
   - Per speciality/condition
   - Maintained by clinicians
   - Versioned

4. **Implement suggestion engine**
   - Inputs: history, symptoms, allergies, medications, labs, age/weight/pregnancy
   - Missing data passed as `unknown`
    - Output: structured JSON
    - Per item: medicine_id, strength, dose, route, frequency, duration, instructions, rationale, supporting facts, warnings, missing data
    - Restricted to catalogue items (LLM cannot invent drugs)

5. **Implement deterministic safety checks**
   - Allergy and cross-reactivity vs recorded allergies
   - Drug-drug interactions vs current medications
   - Duplicate therapy detection
   - Dose-range checks (age/weight/pregnancy/renal)
    - Source: licensed database or pharmacist-curated rules
    - If no reliable source: show "check unavailable", never green
    - Severity levels: block, warn, info

6. **Create endpoints**
   - `/rx/drafts` - Create draft
   - `/rx/{id}/approve` - Approve (requires re-auth)
   - Final prescription immutable
   - Automated test: AI cannot create final prescription without doctor approval

7. **Publish Prescription contract**
    - Document draft schema
    - Document approval flow
    - Document safety check format
    - This is what Dev B needs for prescription UI

### Exit Criteria:
- ✅ Suggestion engine restricted to catalogue
- ✅ Safety checks (allergy, interaction, dose) in place
- ✅ AI cannot create final prescription (automated test)
- ✅ Prescription contract published

---

## Phase A-P7: Support Dev B's Theme

**Goal:** Use design tokens for PDF/templates

**Dependencies:** Dev B provides design tokens

### Tasks:

1. **Read design tokens from Dev B**
   - `docs/design-tokens.md` (owned by Dev B)
   - Extract colors, fonts, spacing

2. **Apply tokens to PDF templates**
   - Letterhead
   - Prescription
   - Token print
   - Report PDF

3. **Fix contract gaps**
   - If Dev B finds issues during theming
   - Fix in backend
   - No new fields after S7 (feature freeze)

### Exit Criteria:
- ✅ PDF templates use design tokens
- ✅ No contract gaps

---

## Phase A-P8: Hardening

**Goal:** Security, performance, demo preparation

**Dependencies:** All previous phases complete

### Tasks:

1. **Load/concurrency tests**
   - k6 or Locust
   - Test queue token generation
   - Test login endpoints
   - Measure p50/p95 latency

2. **Security hardening**
   - Security headers (CSP, HSTS, frame-ancestors)
   - Upload hardening (magic-byte check, size cap, re-encode)
   - ASVS L1 checklist
   - Pen-test prep

3. **Failure drills**
   - DB down → clean 503
   - AI down → graceful degradation
   - Network flaky → retry logic

4. **Demo health endpoint**
   - `/health` endpoint
   - Check DB connection
   - Check AI vendor status
   - Check SSE
   - Used for pre-demo checks

5. **Backup and restore**
   - `pg_dump` scheduled job
   - Separate storage owned by JMCH
   - Perform and document restore drill

6. **Runbooks**
   - Restore procedure
   - Key rotation procedure
   - Incident response

7. **Demo data reset script**
   - Reset synthetic patients
   - Reset queue
   - For demo rehearsals

### Exit Criteria:
- ✅ Load tests passing
- ✅ Security checklist complete
- ✅ Restore drill documented and tested
- ✅ Runbooks written

---

## Collision Analysis

### Will there be collisions?

**Phase A-P0:** NO COLLISION
- You work on backend only
- Dev B works on frontend only
- No shared files

**Phase A-P1:** MINIMAL COLLISION
- You publish API contract (auth endpoints)
- Dev B can start building login UI against mock
- Only coordination: contract review

**Phase A-P2:** MINIMAL COLLISION
- You publish Queue + SSE contract
- Dev B builds queue UI against mock
- Only coordination: contract review

**Phase A-P3:** MINIMAL COLLISION
- You publish Symptom/Triage contract
- Dev B builds clinical UI against mock
- Only coordination: contract review

**Phase A-P4 onwards:** MINIMAL COLLISION
- Same pattern: you publish contract, Dev B builds against mock

### Sequential vs Parallel

**Sequential (Recommended):**
- You do A-P0 and A-P1 first
- Then Dev B starts while you do A-P2
- Pros: Simpler, less coordination, safer
- Cons: Slower overall

**Parallel:**
- You start A-P0, Dev B starts B-P0
- Dev B uses mock servers based on your contracts
- Pros: Faster overall
- Cons: More coordination, contract changes affect both

---

## My Recommendation

**Start Sequential:**
1. You complete **Phase A-P0** (stabilise backend)
2. You complete **Phase A-P1** (Postgres + Auth)
3. Publish Auth contract
4. Then Dev B starts Phase B-P1 (Auth UI) while you start Phase A-P2 (Queue)
5. Continue in parallel from there

**Why this approach:**
- Dev B really needs the DB schema and Auth to build their UI
- A-P0 and A-P1 are foundational (everything depends on them)
- Once foundation is ready, parallel work is safe
- Less coordination overhead at the start

---

## What to Do Right Now

**Start Phase A-P0:**

1. Rotate the OpenAI key in `.env`
2. Clean up `.gitignore` (ensure `.env`, `node_modules`, `.next` are ignored)
3. Write characterisation tests for `backend/main.py`
4. Start splitting `main.py` into modules
5. Fix the critical bugs (B-04, B-05, B-08, B-09, B-11, B-12, B-18)

**Once A-P0 is complete:**
- Let me know
- I'll help you move to Phase A-P1
- Then we can discuss when to bring in Dev B

---

## Summary

**Your Path:**
1. Phase A-P0 → Stabilise backend (you alone)
2. Phase A-P1 → Postgres + Auth (you alone)
3. Phase A-P2 → Queue (parallel with Dev B's B-P1)
4. Phase A-P3 → Clinical safety (parallel with Dev B's B-P2)
5. Phase A-P4 → Reports/History (parallel with Dev B's B-P3)
6. Phase A-P5 → Voice (parallel with Dev B's B-P4)
7. Phase A-P6 → Prescriptions (parallel with Dev B's B-P5)
8. Phase A-P7 → Theme support (parallel with Dev B's B-P6)
9. Phase A-P8 → Hardening (both together)

**Collision Risk:** Minimal after foundation is ready
**Coordination:** Only 8 sync points total
**Start:** Phase A-P0 right now
