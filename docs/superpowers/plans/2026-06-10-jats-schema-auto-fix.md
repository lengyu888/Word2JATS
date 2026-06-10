# JATS Schema Auto Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe whitelist-based JATS Schema auto-fix loop with visible repair records.

**Architecture:** A focused `JatsAutoFixer` mutates only deterministic XML structure issues, revalidates through the existing local Schema validator, and returns a compatible `validation.auto_fix` report. Conversion endpoints share one generation pipeline so upload and manual correction behave identically.

**Tech Stack:** Python, FastAPI, lxml, Pydantic, Vue 3, Element Plus, pytest

---

### Task 1: Auto-fixer contract

**Files:**
- Create: `backend/app/services/jats_auto_fixer.py`
- Modify: `backend/app/models/schema.py`
- Test: `backend/tests/test_jats_auto_fixer.py`

- [ ] Write failing tests for `graphic/@href`, `journal-meta` order, duplicate IDs, and preserved missing metadata.
- [ ] Run `python -m pytest tests/test_jats_auto_fixer.py -q` and confirm failure.
- [ ] Implement the minimal whitelist fixer and typed response model.
- [ ] Run the focused tests and confirm pass.

### Task 2: Conversion pipeline integration

**Files:**
- Modify: `backend/app/routers/convert.py`
- Modify: `backend/app/services/validator.py`
- Test: `backend/tests/test_api.py`

- [ ] Write failing API assertions for `validation.auto_fix`.
- [ ] Introduce a shared generate, auto-fix, validate, score helper.
- [ ] Confirm upload and `/api/generate-xml` return repaired XML and final validation.

### Task 3: Frontend repair visibility

**Files:**
- Modify: `frontend/src/components/ValidationPanel.vue`

- [ ] Render applied repairs and remaining manual Schema problems.
- [ ] Run `npm run build` and confirm pass.

### Task 4: Documentation and verification

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`

- [ ] Document the whitelist boundary and response fields.
- [ ] Run full pytest, frontend build, DTD demo conversion, and Docker Compose verification.

