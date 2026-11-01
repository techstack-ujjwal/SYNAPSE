# SYNAPSE AI × JMCH — Implementation Plan

**Status:** Active · **Date:** 1 Nov 2026 · **Developers:** 2 (Backend/AI + Frontend)

---

## Quick Start

**Dev A (Backend/AI):** Read <ref_file file="C:\SYNAPSE\docs\DEV_A_START_HERE.md" />
**Dev B (Frontend):** Read <ref_file file="C:\SYNAPSE\docs\DEV_B_START_HERE.md" />

---

## Overview

Two developers working in parallel with minimal collision.

**Dev A (Backend/AI Focus):**
- Owns: `backend/`, `clinical/`, `ai/`, `migrations/`
- Requirements: #6, #10, #1, #4, #7, #11
- Phases: A-P0 through A-P8

**Dev B (Frontend Focus):**
- Owns: `app/`, `e2e/`, `messages/*.json`
- Requirements: #2, #3, #5, #8, #9, #12
- Phases: B-P0 through B-P8

**Collision Prevention:**
- Clear directory ownership (no shared files)
- Contract-first workflow (API contracts before implementation)
- Only 8 sync points where coordination is required

---

## How It Works

### Sequential Start (Recommended)

1. **Dev A completes A-P0 and A-P1 first**
   - A-P0: Stabilise backend (split main.py, fix bugs, set up CI)
   - A-P1: Postgres + Auth (database schema, authentication system)
   - This creates the foundation that Dev B needs

2. **Then work in parallel**
   - Dev A starts A-P2 (Queue)
   - Dev B starts B-P0 (Stabilise frontend)
   - Continue in parallel through remaining phases

### Why Sequential Start?

- Dev B needs DB schema and Auth contracts to build UI
- Foundation (A-P0, A-P1) is foundational - everything depends on it
- Once foundation is ready, parallel work is safe
- Less coordination overhead at the start

---

## Phase Overview

| Phase | Dev A (Backend) | Dev B (Frontend) | Parallel? |
|-------|-----------------|------------------|------------|
| P0 | Stabilise backend | (Wait) | No |
| P1 | Postgres + Auth | (Wait) | No |
| P2 | Queue backend | Stabilise frontend | Yes |
| P3 | Clinical safety | Auth UI | Yes |
| P4 | Reports/History | Queue UI | Yes |
| P5 | Voice backend | Clinical UI | Yes |
| P6 | Prescriptions | Reports/History UI | Yes |
| P7 | Theme support | Voice UI | Yes |
| P8 | Hardening | Prescription UI | Yes |
| - | - | Theme | Yes |
| - | - | QA & Demo | Joint |

---

## Server Commands

**Backend:**
```bash
cd backend
py -m venv venv
venv/Scripts/pip install -r requirements.txt
venv/Scripts/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
npm install
npm run dev
```

---

## For Detailed Plans

**Dev A:** <ref_file file="C:\SYNAPSE\docs\DEV_A_START_HERE.md" />
**Dev B:** <ref_file file="C:\SYNAPSE\docs\DEV_B_START_HERE.md" />

These contain:
- Complete task breakdown per phase
- Exit criteria for each phase
- Collision analysis
- Recommendations for getting started
- Sequential vs parallel workflow explanation

---

## Quick Reference: Requirement-to-Developer Mapping

| # | Requirement | Owner | Phase |
|---|-------------|-------|-------|
| 1 | Speech-to-speech AI | Dev A | A-P5 |
| 2 | JMCH theme | Dev B | B-P7 |
| 3 | UI bug fixing | Dev B | B-P8 |
| 4 | Symptom assessment | Dev A | A-P3 |
| 5 | Report structure | Dev A | A-P4 |
| 6 | Doctor identity | Dev A | A-P1 |
| 7 | AI prescriptions | Dev A | A-P6 |
| 8 | History intelligence | Dev A | A-P4 |
| 9 | Personalised questions | Dev A | A-P4 |
| 10 | Neon PostgreSQL | Dev A | A-P1 |
| 11 | No-doctor fallback | Dev A | A-P3 |
| 12 | Live queue | Dev A | A-P2 |

---

## Sync Points

Only 8 moments where coordination is required:

| ID | When | What Happens |
|---|------|--------------|
| S0 | Day 1 | Agree on rules, contracts, mock tooling |
| S1 | End A-P0 | Backend split complete, publish first contract |
| S2 | Start A-P1 | Publish Auth contract |
| S3 | End A-P1 | Auth live, Dev B can start B-P0 |
| S4 | Start A-P2 | Publish Queue + SSE contract |
| S5 | End A-P3 | Publish Symptom/Triage contract |
| S6 | Start A-P4 | Publish Report/Facts contract |
| S7 | End A-P7 | UI component feature freeze |
| S8 | A-P8/B-P8 | Joint regression and demo rehearsals |

---

## What to Do Right Now

**Dev A:**
1. Read <ref_file file="C:\SYNAPSE\docs\DEV_A_START_HERE.md" />
2. Start Phase A-P0 (Stabilise backend)
3. Complete A-P0 and A-P1 before bringing in Dev B

**Dev B:**
1. Read <ref_file file="C:\SYNAPSE\docs\DEV_B_START_HERE.md" />
2. Wait for Dev A to complete A-P0 and A-P1
3. Then start Phase B-P0

---

## Summary

**Sequential start is recommended:**
- Dev A builds foundation first (A-P0, A-P1)
- Then both work in parallel
- Minimal collision due to clear directory ownership
- Only 8 sync points for coordination

**For detailed phase breakdowns, see the developer-specific guides linked above.**
