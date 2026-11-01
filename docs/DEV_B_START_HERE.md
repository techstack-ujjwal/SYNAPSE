# Dev B (Frontend) - Your Phases and How to Start

## When to Start

**Wait for Dev A to complete Phase A-P0 and A-P1 first.**

Why?
- You need the DB schema and Auth API contracts to build your UI
- Dev A is setting up the foundation (PostgreSQL, authentication)
- Once those are ready, you can work in parallel

**Expected timeline:**
- Dev A does A-P0 (stabilise backend) → ~1-2 days
- Dev A does A-P1 (Postgres + Auth) → ~3-5 days
- Then you start Phase B-P0 while Dev A starts A-P2

---

## Your Phases (Dev B - Frontend Focus)

You own these directories:
- `frontend/` or `app/` - All frontend code
- `e2e/` - End-to-end tests
- `frontend/messages/*.json` - Locale files

Dev A never touches these. You never touch `backend/`, `clinical/`, `ai/`, `migrations/`.

---

## Phase B-P0: Stabilise Frontend (START HERE - AFTER Dev A finishes A-P1)

**Goal:** Clean up frontend, fix TypeScript errors, set up foundation

### Tasks (do these in order):

1. **Remove `typescript.ignoreBuildErrors`**
   - Edit `next.config.mjs`
   - Remove or set to `false`
   - This will reveal all TypeScript errors

2. **Enable strict TypeScript**
   - Update `tsconfig.json`
   - Enable strict mode
   - Log the resulting type errors as bug-register entries

3. **Enable ESLint**
   - Ensure ESLint is configured
   - Fix linting errors

4. **Add global error boundary**
   - Create error boundary component
   - Wrap app with it
   - Surface errors instead of swallowing them

5. **Create typed API client**
   - Generate from `contracts/openapi.json` (Dev A provides this)
   - Use OpenAPI generator or similar
   - Ensures type safety on API calls
   - Errors surface, never swallowed with `.catch(() => {})`

6. **Write characterisation tests (Playwright smoke)**
   - Test current patient flow
   - Test current doctor flow
   - Document current behavior before refactor

7. **Split the 1,661-line `app/[locale]/page.tsx`**
   - Current: One giant file with everything
   - Target structure:
     ```
     app/
       [locale]/
         page.tsx (main entry)
         components/
           landing/
           register/
           returning/
           intake/
           summary/
           token/
           dashboard/
     ```
   - Split WITHOUT changing behavior (use characterisation tests to verify)

8. **Switch to route groups**
   - Create `(patient)` route group
   - Create `(doctor)` route group
   - Create `(admin)` route group (empty shell for now)
   - Create `(display)` route group (empty shell for now)

9. **Create design-token skeleton**
   - Create `docs/design-tokens.md`
   - Define colors, typography, spacing, radius, elevation
   - Use CSS variables + Tailwind theme
   - Create clearly marked placeholder brand slot (never fake JMCH logo)

10. **Fix B-04 (shared bug with Dev A)**
    - Remove optimistic UI update on queue buttons
    - Show real success/error
    - Adapt to Dev A's body-based endpoint (Dev A will publish contract)

11. **Remove B-16 (face-scan icon)**
    - Unless D-8 says feature is wanted
    - If not wanted, remove the icon entirely

12. **Set up mock server**
    - MSW or Prism
    - Generated from `contracts/openapi.json`
    - Allows you to build UI without waiting for real backend

13. **Set up frontend CI**
    - Type-check
    - Lint
    - Vitest (unit tests)
    - Playwright smoke tests

14. **Create bug register**
    - `docs/BUGS.md`
    - Format: ID, steps, expected/actual, severity, owner, fix, regression test, retest

### Exit Criteria:
- ✅ Frontend code split into feature modules
- ✅ Characterisation tests passing
- ✅ TypeScript strict mode enabled
- ✅ CI green (type-check, lint, tests)
- ✅ Design token skeleton in place
- ✅ Mock server set up

---

## Phase B-P1: Auth & Identity UI

**Goal:** Login screens, admin console shell, base components

**Dependencies:** Phase B-P0 complete, Dev A's Auth contract available

### Tasks:

1. **Create login screens**
   - Doctor login (password + OTP/TOTP step)
   - Admin login (password + OTP/TOTP step)
   - Patient OTP flow (stubbed visibly until D-9)
   - Logout screen
   - Idle-timeout warning
   - Session-expired handling

2. **Remove `localStorage('doctor')` identity**
   - Currently: identity stored in localStorage
   - Change to: use cookie session via `/me` endpoint
   - Remove all localStorage identity code

3. **Create route guards**
   - Per role (patient, doctor, admin)
   - Friendly 403/401 pages
   - Role-escalation attempts redirect safely

4. **Create admin console shell**
   - Layout component
   - Navigation component
   - Doctor management screens:
     - Create doctor
     - Pending doctors list
     - Verify doctor
     - Approve doctor
     - Suspend doctor
     - Reassign department
   - Audit-log viewer

5. **Create consent screens**
   - Versioned notice
   - Separate AI consent
   - Separate audio consent
   - In all locales (23 languages)

6. **Build base component library on design tokens**
   - Button
   - Input
   - Select
   - Table
   - Tabs
   - Dialog/Modal
   - Toast
   - Badge
   - Banner
   - Skeleton
   - Empty state
   - Error state
   - Loading state
   - Success state

7. **Write E2E test**
   - New doctor onboarding → approval → first login → suspension → blocked login

### Exit Criteria:
- ✅ Login screens working (with mocks)
- ✅ Admin console shell ready
- ✅ Base component library complete
- ✅ E2E test passing

---

## Phase B-P2: Live Queue UI

**Goal:** SSE client, admin queue board, patient queue view

**Dependencies:** Phase B-P1 complete, Dev A's Queue + SSE contract available

### Tasks:

1. **Implement SSE client**
   - Reconnect with exponential backoff
   - Event-ID resume
   - Heartbeat handling
   - Polling fallback
   - Offline banner

2. **Create admin queue board**
   - Per-queue live lists
   - Actions:
     - Check-in
     - Call next
     - In-progress
     - Complete
     - Cancel
     - No-show
     - Recall
     - Transfer
   - Walk-in registration
   - "Requires attention" lane
   - Filters
   - Search
   - Keyboard shortcuts

3. **Create doctor dashboard queue view**
   - Own queue
   - "Call next" button
   - In-progress timer
   - Open consultation workspace

4. **Create patient queue view**
   - Token display (e.g., `JMCH-OPD-042`)
   - Position (e.g., "3 people before you")
   - Status
   - Assigned doctor
   - Wait range wording (not exact time)
   - Neutral emergency-reorder message
   - No other patients' data shown

5. **Create TV display mode**
   - Route group: `(display)`
   - Now-serving tokens only
   - Large type
   - Auto-reconnect
   - No personal data

6. **Write E2E tests**
   - Admin + patient in two browsers stay in sync
   - Killing SSE falls back to polling

### Exit Criteria:
- ✅ SSE client working with fallback
- ✅ Admin queue board complete
- ✅ Doctor queue view complete
- ✅ Patient queue view complete
- ✅ TV display mode complete
- ✅ E2E tests passing

---

## Phase B-P3: Clinical Safety & No-Doctor UI

**Goal:** Intake UI, emergency states, escalation inbox

**Dependencies:** Phase B-P2 complete, Dev A's Symptom/Triage contract available

### Tasks:

1. **Create intake progress UI**
   - Driven by symptom contract
   - Button-card answers
   - Body diagram for pain location
   - Confirm-low-confidence prompts

2. **Create emergency state screen**
   - Clear, calm instruction
   - Local emergency number slot
   - Designed for panic situations

3. **Create CANNOT_ASSESS state**
   - Clear message: "AI unavailable – manual intake"
   - Never empty "no red flags"

4. **Create escalation inbox**
   - On admin dashboard
   - On doctor dashboard
   - Age timers
   - Emergency alerts (sound + banner)

5. **Create no-doctor mode UI**
   - Persistent banner: "No doctor is available right now; this is general information"
   - Callback action
   - Queue placement action
   - Message to clinician action
   - "NOT REVIEWED" report badge
   - Disabled prescription UI

6. **Add priority/triage badges**
   - Visible to doctors
   - With reason codes

7. **Fix remaining UI-side bugs**
   - From bug register

### Exit Criteria:
- ✅ Intake UI complete
- ✅ Emergency state screen complete
- ✅ Escalation inbox complete
- ✅ No-doctor mode UI complete
- ✅ All UI bugs fixed

---

## Phase B-P4: Reports, History, Patient Dashboard

**Goal:** Report viewer, history timeline, patient dashboard

**Dependencies:** Phase B-P3 complete, Dev A's Report/Facts contract available

### Tasks:

1. **Create report viewer**
   - 10 fixed sections
   - Provenance chips
   - "Not recorded" for empty sections
   - Revision history with diff
   - Sign-off UI
   - Print stylesheet (A4)
   - PDF download button

2. **Create doctor "Before consultation" panel**
   - Visit timeline
   - Previous-vs-today view
   - Vitals/lab trend charts with ranges
   - Allergy banner (distinguish "No known allergies recorded" vs "Not recorded / unknown")
   - Reconciliation UI
   - "Information used" list

3. **Implement three-way labelling**
   - Colour + icon + text:
     - 🟦 Clinician-recorded
     - 🟨 Patient-reported
     - 🟪 AI-generated
   - Never colour alone

4. **Rebuild patient dashboard**
   - On authenticated APIs
   - Plain-language visit summaries
   - Follow-ups
   - Reports with existing parameter cards
   - Timeline

5. **Create consultation workspace**
   - Two-pane layout
   - Evolved from existing doctor review page

6. **Create returning-patient flow**
   - "Shall I continue from last time?"
   - Private-device handling

### Exit Criteria:
- ✅ Report viewer complete
- ✅ Doctor "Before consultation" panel complete
- ✅ Patient dashboard rebuilt
- ✅ Three-way labelling implemented

---

## Phase B-P5: Voice UI

**Goal:** AudioWorklet, VAD, WebSocket client, mic status

**Dependencies:** Phase B-P4 complete, Dev A's WebSocket contract available

### Tasks:

1. **Implement AudioWorklet + VAD**
   - Voice activity detection in browser
   - Detect speech start/end

2. **Implement getUserMedia**
   - With echo cancellation
   - Handle permission requests

3. **Create WebSocket client**
   - Connect to `/ws/voice`
   - Handle streaming audio
   - Handle connection loss

4. **Create mic status UI**
   - Large animated indicator
   - States: listening / thinking / speaking / muted / error
   - Repeat button
   - Pause button
   - "Use buttons instead" fallback
   - No transcript by default
   - "Show what I heard" toggle (for staff/accessibility)

5. **Implement barge-in**
   - Stop TTS playback immediately on patient speech
   - Cancel in-flight reply

6. **Implement chunked TTS playback**
   - Play chunks as they arrive
   - Smooth playback

7. **Add silence handling**
   - Silence cue
   - One gentle re-prompt

8. **Create failure UI**
   - No mic permission
   - No device
   - Noisy room
   - Network drop
   - TTS failure
   - Response: spoken/visual message + automatic tap-based fallback + resume

9. **Test across browsers**
   - Chromium
   - Safari iOS
   - Chrome Android
   - One low-end Android device

### Exit Criteria:
- ✅ Voice UI complete
- ✅ Barge-in working
- ✅ Failure modes handled
- ✅ Tested across browsers

---

## Phase B-P6: Prescription Review UI

**Goal:** Side-by-side review, warnings, approval

**Dependencies:** Phase B-P5 complete, Dev A's Prescription contract available

### Tasks:

1. **Create side-by-side layout**
   - Left: patient context
   - Right: AI suggestions

2. **Implement per-item actions**
   - Accept
   - Modify
   - Reject (+ reason)
   - No default "accept all"

3. **Render warnings**
   - **Block** (needs override reason)
   - **Warn**
   - **Info**
   - "Interaction check not available" (never green)

4. **Add banner**
   - "AI-generated draft — not a prescription until approved by Dr. X"

5. **Create searchable catalogue**
   - Searchable drug list
   - Template picker

6. **Implement "Approve and sign"**
   - Re-auth dialog
   - Prescription PDF preview
   - Patient copy in their language (labelled as translation)

7. **Hide when disabled**
   - Hide when `no_doctor_mode` flag is off
   - Hide when `ai_rx` flag is off

### Exit Criteria:
- ✅ Prescription review UI complete
- ✅ Warnings rendering correctly
- ✅ Approval flow working
- ✅ Hidden when disabled

---

## Phase B-P7: JMCH Theme

**Goal:** Apply official branding, accessibility, visual regression

**Dependencies:** Phase B-P6 complete, JMCH assets available (D-2)

### Tasks:

1. **Apply official assets**
   - Logo files (when D-2 arrives)
   - Brand colours
   - Brand fonts
   - Until then: use clearly marked placeholder

2. **Font setup**
   - Brand font if licensed for web
   - Or close open font
   - **Noto Sans Devanagari** for Hindi/Marwari
   - Check all 23 locale scripts for clipping

3. **Create role layouts**
   - Patient: mobile-first
   - Doctor: two-pane workspace
   - Admin: dense tables + dashboard
   - Registration desk
   - Queue display

4. **Implement consistent state patterns**
   - Loading
   - Empty
   - Error
   - Success
   - Offline
   - Session-expiring

5. **Create letterhead component**
   - Shared with Dev A's PDF templates
   - Supply tokens file to Dev A

6. **Accessibility**
   - WCAG 2.2 AA contrast
   - Keyboard navigation
   - Visible focus
   - Labels
   - Reduced motion support
   - 44px touch targets

7. **Visual-regression baselines**
   - 360-430px (mobile)
   - 768-1024px (tablet)
   - ≥1280px (desktop)
   - Save screenshots for comparison

8. **Feature freeze on UI components**
   - No new UI components after this phase
   - Dev A stops adding fields that need new UI

### Exit Criteria:
- ✅ JMCH theme applied
- ✅ All scripts rendering correctly
- ✅ Accessibility scan clean
- ✅ Visual-regression baselines saved
- ✅ UI component feature freeze

---

## Phase B-P8: QA, Hardening, Demo

**Goal:** Full test suite, failure modes, demo preparation

**Dependencies:** Phase B-P7 complete

### Tasks:

1. **Run Playwright across browsers**
   - Chromium
   - Firefox
   - WebKit
   - Mobile emulation

2. **Run accessibility scans**
   - axe in Playwright
   - Zero critical issues

3. **Automate complete workflows**
   - New patient → voice intake → red-flag check → token → live position → doctor consults → report → prescription → PDF → patient sees summary
   - Returning patient → history-aware questions → doctor sees "previous vs today"
   - Admin: register walk-in → call next → no-show → cancel → reports
   - Doctor onboarding → approval → first login → suspension → blocked login

4. **Create failure-mode tests**
   - Session expiry mid-form
   - Refresh on every route
   - Back/forward navigation
   - Double submit
   - Flaky network
   - Mic permission denied/revoked
   - Unsupported browser
   - Interrupted TTS
   - Long inputs
   - Unicode/Devanagari input
   - Empty dashboards
   - Role-escalation attempts
   - Forged tokens
   - Bad uploads

5. **Generate pass/fail report**
   - Zero open Sev-1/Sev-2
   - Published for review

6. **Freeze demo build**
   - One week before demo date
   - Tagged version
   - Only Sev-1 fixes after freeze

7. **Create demo script**
   - 12-15 minute scripted story
   - Every step is an E2E test

8. **Prepare demo backup**
   - Pre-recorded voice fallback clip
   - Offline-capable demo mode
   - Pre-loaded synthetic data

### Exit Criteria:
- ✅ All E2E tests passing
- ✅ Accessibility scan clean
- ✅ Failure-mode tests passing
- ✅ Zero Sev-1/Sev-2 bugs
- ✅ Demo build frozen
- ✅ Demo script ready

---

## What to Do Right Now

**WAIT for Dev A to complete:**
- Phase A-P0 (stabilise backend)
- Phase A-P1 (Postgres + Auth)

**Then:**
1. Start Phase B-P0 (stabilise frontend)
2. Build against Dev A's API contracts using mock servers
3. Work in parallel with Dev A from Phase A-P2 onwards

---

## Summary

**Your Path (starts after Dev A finishes A-P1):**
1. Phase B-P0 → Stabilise frontend
2. Phase B-P1 → Auth UI (parallel with Dev A's A-P2)
3. Phase B-P2 → Queue UI (parallel with Dev A's A-P3)
4. Phase B-P3 → Clinical UI (parallel with Dev A's A-P4)
5. Phase B-P4 → Reports/History (parallel with Dev A's A-P5)
6. Phase B-P5 → Voice UI (parallel with Dev A's A-P6)
7. Phase B-P6 → Prescription UI (parallel with Dev A's A-P7)
8. Phase B-P7 → Theme (parallel with Dev A's A-P8)
9. Phase B-P8 → QA & Demo (both together)

**Collision Risk:** Minimal (you work on frontend only, Dev A works on backend only)
**Coordination:** Only 8 sync points total
**Start:** Wait for Dev A to finish A-P0 and A-P1
