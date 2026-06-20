# Official JATS Quality Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve actual DOCX-to-JATS output against the five official competition references until every generated XML passes JATS Publishing 1.3 DTD validation, average semantic similarity is at least 90, and every sample scores at least 80 before human correction.

**Architecture:** Keep the existing FastAPI/Vue pipeline and public API fields. Replace global tag-count comparison with semantic-path diagnostics, then use those diagnostics to drive general parser and generator fixes for metadata, hierarchy, floating objects, citations, and xrefs. Official XML remains a structural reference; fields absent from DOCX are reported as publisher-enriched rather than invented.

**Tech Stack:** Python 3, FastAPI, lxml, python-docx, pytest, Vue 3, Element Plus, Vite, Docker Compose.

---

## File Structure

- Create `backend/app/services/official_sample_evaluator.py`: run and aggregate official sample comparisons without HTTP coupling.
- Create `backend/evaluate_official_samples.py`: command-line report entry point.
- Modify `backend/app/services/official_xml_comparator.py`: semantic extraction, scoring, and actionable differences.
- Modify `backend/app/services/docx_parser.py`: metadata, section, object, and reference classification.
- Modify `backend/app/services/document_flow_parser.py`: conservative paragraph and media classification.
- Modify `backend/app/services/jats_generator.py`: nested sections and source-order-aware JATS output.
- Modify `backend/app/services/xref_resolver.py`: compound and range references.
- Modify `backend/app/services/reference_parser.py`: wrapped citations and structured field confidence.
- Modify `backend/app/routers/convert.py`: expose V2 comparison without changing existing fields.
- Modify `frontend/src/components/OfficialComparison.vue`: render dimension scores and difference classes.
- Modify `frontend/src/components/BatchResults.vue`: aggregate official sample scores.
- Create `backend/tests/test_official_xml_comparator.py`: focused semantic comparison tests.
- Create `backend/tests/test_official_samples.py`: five-sample regression and acceptance tests.
- Modify existing service/API tests for each parser and generator behavior.
- Create `docs/官方样例对比报告.md`: reproducible before/after evidence.
- Update the three README files with commands, metric definition, and current limitations.

### Task 1: Establish Semantic Official Comparison

**Files:**
- Create: `backend/tests/test_official_xml_comparator.py`
- Modify: `backend/app/services/official_xml_comparator.py`
- Modify: `backend/app/models/schema.py`

- [ ] **Step 1: Write failing tests for semantic paths**

Add tests proving that the primary title is read only from `front/article-meta/title-group/article-title`, reference article titles do not inflate it, section order is retained, and publisher-only metadata is classified separately.

```python
def test_reference_article_titles_do_not_count_as_primary_titles(tmp_path):
    generated = "<article><front><article-meta><title-group><article-title>A</article-title></title-group></article-meta></front><body/><back/></article>"
    official = tmp_path / "official.xml"
    official.write_text("<article><front><article-meta><title-group><article-title>A</article-title></title-group></article-meta></front><body/><back><ref-list><ref><element-citation><article-title>Reference title</article-title></element-citation></ref></ref-list></back></article>", encoding="utf-8")
    result = OfficialXmlComparator().compare(generated, official)
    assert result["dimensions"]["metadata"]["score"] == 100
    assert result["facts"]["official"]["title"] == "A"
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/test_official_xml_comparator.py -q`

Expected: FAIL because `dimensions` and semantic facts do not exist.

- [ ] **Step 3: Implement semantic extraction and scoring**

Introduce normalized extraction helpers and return both compatibility counts and V2 fields:

```python
result.update({
    "metric_version": "2.0",
    "dimensions": dimensions,
    "facts": {"generated": generated_facts, "official": official_facts},
    "recoverable_differences": recoverable,
    "publisher_enriched_differences": enriched,
})
result["similarity_score"] = self._weighted_score(dimensions)
```

Use precision/recall F1 for unordered collections, sequence similarity for ordered headings and references, and exact JATS semantic XPaths for metadata.

- [ ] **Step 4: Run focused and API tests**

Run: `python -m pytest tests/test_official_xml_comparator.py tests/test_api.py::test_official_demo_conversion_returns_comparison_report -q`

Expected: PASS.

### Task 2: Capture the Five-Sample Baseline

**Files:**
- Create: `backend/app/services/official_sample_evaluator.py`
- Create: `backend/evaluate_official_samples.py`
- Create: `backend/tests/test_official_samples.py`

- [ ] **Step 1: Write a failing evaluator aggregation test**

```python
def test_aggregate_official_results_reports_average_minimum_and_schema_rate():
    summary = aggregate_results([
        {"similarity_score": 90, "schema_valid": True},
        {"similarity_score": 80, "schema_valid": False},
    ])
    assert summary == {
        "sample_count": 2,
        "average_similarity": 85.0,
        "minimum_similarity": 80,
        "schema_valid_rate": 0.5,
    }
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_official_samples.py::test_aggregate_official_results_reports_average_minimum_and_schema_rate -q`

Expected: FAIL because the evaluator module is absent.

- [ ] **Step 3: Implement evaluator and CLI**

The evaluator loads the router's allowlisted official pairs, runs `DocxParser`, `JatsGenerator`, validation, and semantic comparison, then writes a Markdown report. It must not call the network or depend on a running server.

- [ ] **Step 4: Record baseline**

Run: `python evaluate_official_samples.py --output ../docs/官方样例对比报告.md`

Expected: five per-sample rows plus average, minimum, DTD pass rate, and top recoverable differences.

### Task 3: Fix Front Matter and Section Hierarchy

**Files:**
- Modify: `backend/tests/test_services.py`
- Modify: `backend/app/services/docx_parser.py`
- Modify: `backend/app/services/jats_generator.py`

- [ ] **Step 1: Write failing tests for adjacent keywords and nested sections**

```python
def test_keyword_marker_can_be_followed_by_value_paragraph(tmp_path):
    # Build DOCX with "Keywords:" followed by "JATS; XML; publishing".
    article = parse_fixture(tmp_path)
    assert article["keywords"] == ["JATS", "XML", "publishing"]

def test_generator_nests_sections_by_level():
    article = complete_article(sections=[
        {"title": "Methods", "level": 1, "paragraphs": []},
        {"title": "Dataset", "level": 2, "paragraphs": ["Text"]},
        {"title": "Results", "level": 1, "paragraphs": []},
    ])
    root = etree.fromstring(JatsGenerator().generate(article).encode())
    assert root.xpath("count(body/sec)") == 2
    assert root.xpath("string(body/sec[1]/sec/title)") == "Dataset"
```

- [ ] **Step 2: Verify RED**

Run the two focused tests and confirm missing adjacent keywords and flat sections.

- [ ] **Step 3: Implement general fixes**

Track `awaiting_keywords`, reject reserved front/back markers as section titles, normalize section-level jumps, and build section XML with a stack:

```python
while stack and stack[-1][0] >= level:
    stack.pop()
parent = stack[-1][1] if stack else body
sec = etree.SubElement(parent, "sec", id=section_id)
stack.append((level, sec))
```

- [ ] **Step 4: Verify focused tests, DTD, and full service tests**

Run: `python -m pytest tests/test_services.py -q`

Expected: PASS.

### Task 4: Reduce Figure and Formula False Positives

**Files:**
- Modify: `backend/tests/test_document_flow_parser.py`
- Modify: `backend/tests/test_services.py`
- Modify: `backend/app/services/document_flow_parser.py`
- Modify: `backend/app/services/docx_parser.py`

- [ ] **Step 1: Write failing classification tests**

Cover decorative/header images, images inside table cells, ordinary short prose containing `=`, and genuine OMML equations. Assert that weak text evidence stays a paragraph while OMML remains a formula.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_document_flow_parser.py tests/test_services.py -k "formula or image" -q`

- [ ] **Step 3: Implement conservative evidence rules**

Require OMML, equation style, or a compact expression shape with both operands for text formulas. Attach flow context to images and classify unsupported embedded objects as review items instead of figures.

- [ ] **Step 4: Re-evaluate official samples**

Run: `python evaluate_official_samples.py --output ../docs/官方样例对比报告.md`

Expected: figure/formula precision improves without reducing DTD pass rate.

### Task 5: Improve References and Compound Cross-References

**Files:**
- Modify: `backend/tests/test_reference_parser.py`
- Modify: `backend/tests/test_xref_resolver.py`
- Modify: `backend/app/services/reference_parser.py`
- Modify: `backend/app/services/docx_parser.py`
- Modify: `backend/app/services/xref_resolver.py`
- Modify: `backend/app/services/jats_generator.py`

- [ ] **Step 1: Write failing tests**

Cover wrapped reference continuation lines, `[1-3]`, `Figs. 1-3`, `Tables 2 and 3`, and `Eqs. (1)-(2)`. Assert generated xrefs point to existing IDs and original visible text is preserved.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_reference_parser.py tests/test_xref_resolver.py -q`

- [ ] **Step 3: Implement reference buffering and xref expansion**

Use numbered-entry starts to flush a reference buffer; continuation paragraphs append to the current raw citation. Expand ranges only within a bounded size and emit one xref per target while preserving punctuation in text/tails.

- [ ] **Step 4: Verify tests and official reference counts**

Run focused tests, then the evaluator. Expected: sample reference precision/recall and xref target coverage improve.

### Task 6: Improve Official Comparison UI

**Files:**
- Modify: `frontend/src/components/OfficialComparison.vue`
- Modify: `frontend/src/components/BatchResults.vue`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Add frontend component tests if an existing test runner is available; otherwise define build-time fixtures**

The component must handle both legacy count-only responses and V2 dimension responses without throwing.

- [ ] **Step 2: Implement V2 presentation**

Show overall score, DTD status, dimension cards, recoverable differences, publisher-enriched differences, and suggestions. Batch view computes average and minimum only from available official comparisons.

- [ ] **Step 3: Build frontend**

Run: `npm run build`

Expected: successful Vite production build.

### Task 7: Final Acceptance and Documentation

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Update: `docs/官方样例对比报告.md`
- Modify: `backend/tests/test_official_samples.py`

- [ ] **Step 1: Add automated acceptance assertions**

```python
def test_official_samples_meet_automatic_quality_thresholds(official_results):
    assert all(item["schema_valid"] for item in official_results)
    assert min(item["similarity_score"] for item in official_results) >= 80
    assert mean(item["similarity_score"] for item in official_results) >= 90
```

- [ ] **Step 2: Run full backend verification**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Run official evaluator**

Run: `python evaluate_official_samples.py --output ../docs/官方样例对比报告.md`

Expected: five samples, average at least 90, minimum at least 80, DTD pass rate 100%.

- [ ] **Step 4: Run frontend and Docker verification**

Run: `npm run build` from `frontend`, then `docker compose up --build -d` and submit all five official samples through `http://localhost:8080/api/batch-convert`.

Expected: frontend build succeeds, services become healthy, all five conversions succeed, and returned XML passes DTD validation.

- [ ] **Step 5: Synchronize documentation**

Document the semantic metric definition, automatic pre-correction threshold, official sample command, publisher-enrichment boundary, and remaining real limitations consistently in all three README files.

- [ ] **Step 6: Final repository audit**

Run: `git diff --check`, scan the three READMEs for obsolete JATS 1.4/default two-demo claims, inspect `git status`, and review the final diff before commit and push.
