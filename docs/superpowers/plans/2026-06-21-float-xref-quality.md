# Float and Xref Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise five-sample official semantic similarity from 91.6% to at least 93.0% by improving general-purpose figure/table matching and xref recovery while keeping the minimum sample score at 88 and JATS 1.3 DTD validity at 100%.

**Architecture:** Add a `FloatCandidateMatcher` that scores existing document-flow objects without reparsing DOCX, then integrate its decisions into `DocxParser`. Extend `XrefResolver` with normalized target tokens, subfigure support, and conservative partial resolution. Keep `StructureEvidence`, validation, and the official comparator as the explanation and acceptance layers.

**Tech Stack:** Python 3.12, FastAPI, python-docx, lxml, pytest, Vue 3, Vite

---

## File Map

- Create `backend/app/services/float_candidate_matcher.py`: rank caption/object candidates and return conservative binding decisions.
- Create `backend/tests/test_float_candidate_matcher.py`: unit coverage for adjacency, numbering, object kind, ambiguity, and section boundaries.
- Modify `backend/app/services/docx_parser.py`: collect float candidates, invoke the matcher, preserve unmatched objects, and expose evidence.
- Modify `backend/app/services/document_flow_parser.py`: retain minimal caption/object signals required by the matcher.
- Modify `backend/app/services/xref_resolver.py`: parse plural, range, subfigure, formula, and bibliography reference tokens.
- Modify `backend/app/services/jats_generator.py`: emit only target-valid xrefs and preserve unresolved text.
- Modify `backend/app/services/validator.py`: report partial and unresolved source references.
- Modify `backend/app/services/official_xml_comparator.py`: expose xref type/count and float placement diagnostics without changing dimension weights.
- Modify `backend/app/services/official_sample_evaluator.py` and `backend/evaluate_official_samples.py`: enforce 93/88/100 acceptance gates.
- Modify `frontend/src/components/QualityReport.vue`: show ambiguous float and unresolved xref summaries already returned by the backend.
- Modify `README.md`, `backend/README.md`, `frontend/README.md`, and `docs/官方样例对比报告.md`: publish measured behavior and limits.

### Task 1: Float Candidate Matcher

**Files:**
- Create: `backend/app/services/float_candidate_matcher.py`
- Create: `backend/tests/test_float_candidate_matcher.py`

- [ ] **Step 1: Write failing matcher tests**

```python
from app.services.float_candidate_matcher import FloatCandidateMatcher


def test_same_number_adjacent_caption_is_selected():
    matcher = FloatCandidateMatcher()
    result = matcher.match(
        captions=[{"flow_index": 11, "section_index": 0, "kind": "figure", "number": "1"}],
        objects=[{"flow_index": 10, "section_index": 0, "kind": "image", "id": "fig1"}],
    )
    assert result[0]["object_id"] == "fig1"
    assert result[0]["status"] == "ok"
    assert result[0]["confidence"] >= 0.80


def test_table_caption_prefers_native_table_over_image():
    matcher = FloatCandidateMatcher()
    result = matcher.match(
        captions=[{"flow_index": 20, "section_index": 1, "kind": "table", "number": "2"}],
        objects=[
            {"flow_index": 19, "section_index": 1, "kind": "image", "id": "fig2"},
            {"flow_index": 18, "section_index": 1, "kind": "table", "id": "tab2"},
        ],
    )
    assert result[0]["object_id"] == "tab2"


def test_cross_section_and_tied_candidates_are_not_forced():
    matcher = FloatCandidateMatcher()
    cross_section = matcher.match(
        captions=[{"flow_index": 8, "section_index": 1, "kind": "figure", "number": "1"}],
        objects=[{"flow_index": 7, "section_index": 0, "kind": "image", "id": "fig1"}],
    )
    assert cross_section[0]["object_id"] is None
    assert cross_section[0]["status"] == "need_review"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/test_float_candidate_matcher.py -q`

Expected: collection fails because `float_candidate_matcher.py` does not exist.

- [ ] **Step 3: Implement the minimal matcher**

Implement `FloatCandidateMatcher.match(captions, objects)` with these deterministic scores:

```python
score = 0.0
if caption["section_index"] == obj["section_index"]: score += 0.35
else: reject = True
if caption["number"] and caption["number"] == object_number(obj["id"]): score += 0.35
if abs(caption["flow_index"] - obj["flow_index"]) <= 1: score += 0.20
elif abs(caption["flow_index"] - obj["flow_index"]) <= 3: score += 0.10
if caption["kind"] == "table" and obj["kind"] == "table": score += 0.10
if caption["kind"] == "figure" and obj["kind"] == "image": score += 0.10
```

Select a candidate only when the best score is at least `0.80` and exceeds the second-best score by at least `0.15`. Otherwise return `object_id=None`, `status=need_review`, evidence, and an issue.

- [ ] **Step 4: Run matcher tests**

Run: `python -m pytest tests/test_float_candidate_matcher.py -q`

Expected: all matcher tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/float_candidate_matcher.py backend/tests/test_float_candidate_matcher.py
git commit -m "feat: add conservative float candidate matcher"
```

### Task 2: Integrate Float Matching Into DOCX Parsing

**Files:**
- Modify: `backend/app/services/document_flow_parser.py`
- Modify: `backend/app/services/docx_parser.py`
- Modify: `backend/tests/test_document_flow_parser.py`
- Modify: `backend/tests/test_official_parser_improvements.py`

- [ ] **Step 1: Add failing flow integration tests**

Add tests constructing DOCX files for:

```python
def test_table_caption_binds_native_table_when_nearby_image_exists(tmp_path):
    article = parse_doc_with_image_native_table_and_caption(tmp_path, "Table 1 Results")
    assert len(article["tables"]) == 1
    assert article["tables"][0]["caption"] == "Table 1 Results"
    assert article["tables"][0]["status"] == "ok"
    assert article["figures"][0]["caption"] == ""


def test_caption_before_object_binds_with_same_number(tmp_path):
    article = parse_doc_with_caption_before_image(tmp_path, "Figure 1 Architecture")
    assert article["figures"][0]["caption"] == "Figure 1 Architecture"


def test_unmatched_float_is_preserved_for_review(tmp_path):
    article = parse_doc_with_ambiguous_images(tmp_path)
    assert any(item["status"] == "need_review" for item in article["figures"])
```

- [ ] **Step 2: Run focused parser tests and verify failure**

Run: `python -m pytest tests/test_document_flow_parser.py tests/test_official_parser_improvements.py -q`

Expected: new native-table preference and caption-before-object assertions fail.

- [ ] **Step 3: Collect and match candidates**

Retain each float object's `flow_index`, `section_index`, and `kind`, and each caption's normalized kind and number. Invoke `FloatCandidateMatcher` after the existing flow pass. Apply accepted matches, keep unmatched captions as caption-only objects, and keep unmatched media with empty captions. Feed match confidence/evidence/issues into `StructureEvidence` fields without changing public IDs.

- [ ] **Step 4: Normalize caption comparison text**

Add a helper that collapses whitespace and separates the label from caption content for matching while preserving the original caption in article JSON:

```python
def _caption_key(text: str) -> tuple[str, str]:
    match = re.match(r"^\s*(fig(?:ure)?\.?|table|图|表)\s*(\d+(?:[-.]\d+)?[a-z]?)", text, re.I)
    return (match.group(1).casefold(), match.group(2).casefold()) if match else ("", "")
```

- [ ] **Step 5: Run parser and JATS regressions**

Run: `python -m pytest tests/test_document_flow_parser.py tests/test_official_parser_improvements.py tests/test_services.py -q`

Expected: all tests pass and existing section-boundary behavior remains intact.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_flow_parser.py backend/app/services/docx_parser.py backend/tests/test_document_flow_parser.py backend/tests/test_official_parser_improvements.py
git commit -m "feat: bind floats with document-flow evidence"
```

### Task 3: Extend Xref Syntax and Token Normalization

**Files:**
- Modify: `backend/app/services/xref_resolver.py`
- Modify: `backend/tests/test_xref_resolver.py`

- [ ] **Step 1: Add failing syntax tests**

```python
def test_resolves_subfigures_and_plural_lists():
    matches = XrefResolver().resolve(
        "See Fig. 1a, Figure 2(b), and Tables 1 and 2."
    )
    assert [(item["ref_type"], item["rid"]) for item in matches] == [
        ("fig", "fig1a"), ("fig", "fig2b"), ("table", "tab1 tab2")
    ]


def test_resolves_mixed_bibliography_separators():
    match = XrefResolver().resolve("Prior work [1, 3–5, 7].")[0]
    assert match["rid"] == "ref1 ref3 ref4 ref5 ref7"
```

- [ ] **Step 2: Run xref tests and verify failure**

Run: `python -m pytest tests/test_xref_resolver.py -q`

Expected: subfigure targets and mixed bibliography separators fail.

- [ ] **Step 3: Implement normalized target tokens**

Represent parsed targets as ordered tokens such as `1`, `1a`, and `2b`. Expand numeric ranges only when both endpoints are integers. Normalize parenthesized subfigure suffixes to the same token form and preserve stable order without duplicates.

- [ ] **Step 4: Run xref unit tests**

Run: `python -m pytest tests/test_xref_resolver.py -q`

Expected: all xref syntax and previous range tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/xref_resolver.py backend/tests/test_xref_resolver.py
git commit -m "feat: recover compound and subfigure xrefs"
```

### Task 4: Validate Xrefs Against Real Targets

**Files:**
- Modify: `backend/app/services/jats_generator.py`
- Modify: `backend/app/services/validator.py`
- Modify: `backend/tests/test_xref_resolver.py`
- Modify: `backend/tests/test_jats_auto_fixer.py`

- [ ] **Step 1: Add failing target-integrity tests**

```python
def test_subfigure_reference_falls_back_to_parent_when_only_parent_exists():
    result = XrefResolver().resolve_against_targets("Fig. 1a", {"fig1"})[0]
    assert result["rid"] == "fig1"
    assert result["status"] == "need_review"
    assert result["normalized_from"] == "fig1a"


def test_generator_never_emits_unknown_subfigure_id():
    xml = JatsGenerator().generate(build_article("See Fig. 9a."))
    assert 'rid="fig9a"' not in xml
```

- [ ] **Step 2: Run target-integrity tests and verify failure**

Run: `python -m pytest tests/test_xref_resolver.py tests/test_jats_auto_fixer.py -q`

Expected: parent fallback metadata is absent.

- [ ] **Step 3: Implement conservative parent fallback**

When a subfigure target is absent but its numeric parent exists, emit the parent `rid`, retain the original visible text, mark the match `need_review`, and record `normalized_from`. When neither target exists, emit no xref and report the missing target through source validation.

- [ ] **Step 4: Run xref, validator, generator, and API tests**

Run: `python -m pytest tests/test_xref_resolver.py tests/test_jats_auto_fixer.py tests/test_api.py -q`

Expected: all tests pass and generated XML contains no unknown IDs.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/xref_resolver.py backend/app/services/jats_generator.py backend/app/services/validator.py backend/tests/test_xref_resolver.py backend/tests/test_jats_auto_fixer.py
git commit -m "feat: normalize xrefs to real article targets"
```

### Task 5: Quality and Official Evaluation Diagnostics

**Files:**
- Modify: `backend/app/services/quality_scorer.py`
- Modify: `backend/app/services/official_xml_comparator.py`
- Modify: `backend/app/services/official_sample_evaluator.py`
- Modify: `backend/evaluate_official_samples.py`
- Modify: `backend/tests/test_quality_scorer.py`
- Modify: `backend/tests/test_official_xml_comparator.py`
- Modify: `backend/tests/test_official_samples.py`
- Modify: `frontend/src/components/QualityReport.vue`

- [ ] **Step 1: Add failing diagnostic tests**

Assert that the comparator returns `figure_count`, `figure_caption`, `figure_section`, `table_count`, `table_caption`, `table_section`, `xref_count`, and `xref_targets`, and that the quality report counts ambiguous floats and parent-normalized xrefs.

- [ ] **Step 2: Run diagnostics tests and verify failure**

Run: `python -m pytest tests/test_quality_scorer.py tests/test_official_xml_comparator.py tests/test_official_samples.py -q`

Expected: xref diagnostics and parent-normalization summaries are absent.

- [ ] **Step 3: Implement additive diagnostics**

Keep all existing score keys and weights. Add xref count and target F1 sub-metrics, `float_evidence_summary`, and `xref_normalization_summary`. Render these as compact tags in `QualityReport.vue`; do not add a new route or change API endpoints.

- [ ] **Step 4: Verify backend and frontend**

Run: `python -m pytest tests/test_quality_scorer.py tests/test_official_xml_comparator.py tests/test_api.py -q`

Run: `npm.cmd run build`

Expected: tests and production build pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/quality_scorer.py backend/app/services/official_xml_comparator.py backend/app/services/official_sample_evaluator.py backend/evaluate_official_samples.py backend/tests/test_quality_scorer.py backend/tests/test_official_xml_comparator.py backend/tests/test_official_samples.py frontend/src/components/QualityReport.vue
git commit -m "feat: report float and xref quality diagnostics"
```

### Task 6: Acceptance Tuning Without Sample-Specific Rules

**Files:**
- Modify only files already listed in Tasks 1-5 when a failing generic test demonstrates the required behavior.
- Update: `docs/官方样例对比报告.md`

- [ ] **Step 1: Run the official evaluator**

Run: `python evaluate_official_samples.py --average-floor 93 --minimum-floor 88 --schema-floor 1`

Expected: the command reports each failing dimension and exits `1` until the 93/88/100 gates are met.

- [ ] **Step 2: Convert each recoverable gap into a generic failing test**

For every proposed parser change, create a synthetic DOCX/XML test reproducing the layout pattern without copying official filenames or fixed article text. Run that test to confirm it fails before modifying production code.

- [ ] **Step 3: Implement only test-backed generic changes**

Allowed signals are styles, numbering, flow order, section boundaries, relationships, object kinds, and caption/reference syntax. Reject changes conditioned on sample paths, filenames, hashes, or exact article phrases.

- [ ] **Step 4: Re-run focused and official gates after each change**

Run: `python -m pytest tests/test_float_candidate_matcher.py tests/test_document_flow_parser.py tests/test_xref_resolver.py -q`

Run: `python evaluate_official_samples.py --average-floor 93 --minimum-floor 88 --schema-floor 1`

Expected final result: average at least 93.0, minimum at least 88, schema valid rate 1.0000.

- [ ] **Step 5: Commit measured improvements**

```bash
git add backend/app backend/tests docs/官方样例对比报告.md
git commit -m "perf: improve official float and xref similarity"
```

### Task 7: Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Modify: `docs/错误案例分析.md`

- [ ] **Step 1: Update measured capability text**

Document the final measured score, matcher evidence, parent xref fallback, limitations, and the exact evaluator command. Keep visual table reconstruction and nonstandard citation syntax under current limitations.

- [ ] **Step 2: Run the complete backend suite**

Run: `$base = 'C:\tmp\word2jats-float-xref-' + [guid]::NewGuid().ToString('N'); python -m pytest -q --basetemp $base`

Expected: all tests pass with zero failures.

- [ ] **Step 3: Run frontend production build**

Run: `npm.cmd run build`

Expected: Vite build succeeds; the existing chunk-size warning is acceptable.

- [ ] **Step 4: Run final official acceptance**

Run: `python evaluate_official_samples.py --average-floor 93 --minimum-floor 88 --schema-floor 1`

Expected: `acceptance_passed=true`.

- [ ] **Step 5: Build Docker images**

Run: `docker compose build`

Expected: backend and frontend images build successfully.

- [ ] **Step 6: Commit final documentation**

```bash
git add README.md backend/README.md frontend/README.md docs/错误案例分析.md docs/官方样例对比报告.md
git commit -m "docs: publish float and xref quality results"
```
