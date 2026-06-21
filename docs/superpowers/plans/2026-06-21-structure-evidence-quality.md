# Structure Evidence Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve figure/table binding, formula classification, and xref integrity through conservative, explainable evidence scoring while preserving JATS 1.3 DTD validity.

**Architecture:** Add a focused `StructureEvidence` service that scores existing parser candidates without re-parsing DOCX. Integrate its annotations into `DocxParser`, `JatsGenerator`, `QualityScorer`, and the existing official-sample evaluator, with conservative degradation for ambiguous objects.

**Tech Stack:** Python 3.12, FastAPI, lxml, python-docx, pytest, Vue 3, Element Plus, Vite

---

## File Map

- Create `backend/app/services/structure_evidence.py`: shared score thresholds and evidence calculations.
- Create `backend/tests/test_structure_evidence.py`: unit tests for evidence scoring and status thresholds.
- Modify `backend/app/services/docx_parser.py`: annotate figures, tables, and formulas after flow parsing.
- Modify `backend/app/services/jats_generator.py`: preserve conservative objects and valid xrefs without inventing targets.
- Modify `backend/app/services/quality_scorer.py`: report evidence, ambiguous bindings, and formula/xref summaries.
- Modify `backend/app/services/xref_resolver.py`: expose partially resolved targets and normalized reference evidence.
- Modify `backend/app/services/official_xml_comparator.py`: report figure/table/formula/xref sub-metrics without changing dimension weights.
- Modify `backend/app/services/official_sample_evaluator.py`: aggregate before/after structure metrics.
- Modify `frontend/src/components/QualityReport.vue`: show evidence and conservative-review summaries.
- Modify `README.md`, `backend/README.md`, `frontend/README.md`, `docs/官方样例对比报告.md`: document measured behavior and limits.

### Task 1: Structure Evidence Service

**Files:**
- Create: `backend/app/services/structure_evidence.py`
- Create: `backend/tests/test_structure_evidence.py`

- [ ] **Step 1: Write failing threshold and binding tests**

```python
from app.services.structure_evidence import StructureEvidence


def test_status_thresholds_are_conservative():
    scorer = StructureEvidence()
    assert scorer.status_for(0.80) == "ok"
    assert scorer.status_for(0.79) == "need_review"
    assert scorer.status_for(0.49) == "warning"


def test_cross_section_candidate_is_rejected():
    result = StructureEvidence().score_binding(
        object_type="figure",
        same_section=False,
        distance=1,
        number_match=True,
        explicit_caption=True,
    )
    assert result["status"] == "error"
    assert result["confidence"] == 0.0
    assert "跨章节" in result["issues"][0]["message"]


def test_number_and_section_evidence_produce_high_confidence():
    result = StructureEvidence().score_binding(
        object_type="table",
        same_section=True,
        distance=1,
        number_match=True,
        explicit_caption=True,
    )
    assert result["confidence"] >= 0.80
    assert result["status"] == "ok"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/test_structure_evidence.py -q`

Expected: FAIL because `structure_evidence.py` does not exist.

- [ ] **Step 3: Implement the minimal evidence service**

```python
class StructureEvidence:
    OK_THRESHOLD = 0.80
    REVIEW_THRESHOLD = 0.50

    @classmethod
    def status_for(cls, confidence: float) -> str:
        if confidence >= cls.OK_THRESHOLD:
            return "ok"
        if confidence >= cls.REVIEW_THRESHOLD:
            return "need_review"
        return "warning"

    def score_binding(self, *, object_type, same_section, distance,
                      number_match, explicit_caption):
        if not same_section:
            return {
                "confidence": 0.0,
                "status": "error",
                "evidence": [],
                "issues": [{
                    "level": "error",
                    "message": "候选对象与题注跨章节，已拒绝自动绑定。",
                    "suggestion": "在人工校正页面确认对象归属。",
                }],
            }
        score = 0.30
        evidence = ["位于同一章节"]
        if explicit_caption:
            score += 0.20
            evidence.append("识别到显式题注")
        if number_match:
            score += 0.35
            evidence.append("编号一致")
        if distance <= 1:
            score += 0.15
            evidence.append("文档流距离为 1")
        return {
            "confidence": round(min(score, 1.0), 2),
            "status": self.status_for(score),
            "evidence": evidence,
            "issues": [],
        }
```

- [ ] **Step 4: Run the new tests**

Run: `python -m pytest tests/test_structure_evidence.py -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/structure_evidence.py backend/tests/test_structure_evidence.py
git commit -m "feat: add conservative structure evidence scoring"
```

### Task 2: Evidence-Aware Figure and Table Binding

**Files:**
- Modify: `backend/app/services/docx_parser.py`
- Modify: `backend/tests/test_official_parser_improvements.py`
- Test: `backend/tests/test_document_flow_parser.py`

- [ ] **Step 1: Add failing tests for annotations and ambiguity**

Add tests that build DOCX files with an explicit same-section figure caption and with an uncaptioned image:

```python
def test_explicit_figure_binding_contains_evidence(tmp_path):
    article = parse_doc_with_image_and_caption(tmp_path, "Figure 1. Architecture")
    figure = article["figures"][0]
    assert figure["status"] == "ok"
    assert figure["confidence"] >= 0.80
    assert "位于同一章节" in figure["evidence"]


def test_unbound_image_requires_review(tmp_path):
    article = parse_doc_with_image_without_caption(tmp_path)
    figure = article["figures"][0]
    assert figure["status"] == "need_review"
    assert figure["issues"][0]["level"] == "warning"
```

- [ ] **Step 2: Run the focused tests**

Run: `python -m pytest tests/test_official_parser_improvements.py -q`

Expected: new assertions FAIL because evidence fields are absent.

- [ ] **Step 3: Annotate parsed floats after binding**

Instantiate `StructureEvidence` in `DocxParser`, retain caption/media flow indexes, and call:

```python
result = self.structure_evidence.score_binding(
    object_type="figure",
    same_section=caption_section == media_section,
    distance=abs(caption_flow_index - media_flow_index),
    number_match=caption_number == object_number,
    explicit_caption=bool(caption),
)
figure.update(result)
```

For unbound or caption-only objects call `review_result()` with a specific message. Apply the same behavior to native and image-based tables. Do not change current IDs or section indexes.

- [ ] **Step 4: Run parser and flow tests**

Run: `python -m pytest tests/test_official_parser_improvements.py tests/test_document_flow_parser.py -q`

Expected: PASS, including existing cross-section binding tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/docx_parser.py backend/tests/test_official_parser_improvements.py
git commit -m "feat: annotate figure and table binding evidence"
```

### Task 3: Conservative Formula Classification

**Files:**
- Modify: `backend/app/services/structure_evidence.py`
- Modify: `backend/app/services/document_flow_parser.py`
- Modify: `backend/app/services/docx_parser.py`
- Modify: `backend/tests/test_structure_evidence.py`
- Modify: `backend/tests/test_official_parser_improvements.py`

- [ ] **Step 1: Add failing formula-evidence tests**

```python
def test_display_omml_scores_high_but_inline_omml_is_not_display():
    scorer = StructureEvidence()
    display = scorer.score_formula(
        has_omath_para=True, pure_math=True, aligned=False, numbered=False
    )
    inline = scorer.score_formula(
        has_omath_para=False, pure_math=False, aligned=False, numbered=False
    )
    assert display["status"] == "ok"
    assert inline["is_display"] is False


def test_greek_abbreviation_remains_paragraph(tmp_path):
    nodes = parse_flow_paragraphs(tmp_path, "α-KG: α-ketoglutarate")
    assert nodes[0]["type"] == "paragraph"
```

- [ ] **Step 2: Run focused formula tests**

Run: `python -m pytest tests/test_structure_evidence.py tests/test_official_parser_improvements.py -q`

Expected: formula evidence test FAIL.

- [ ] **Step 3: Implement formula evidence and attach annotations**

Add `score_formula()` using OMML paragraph, pure-math, alignment, numbering, operator density, and prose length. Return `is_display`, `confidence`, `status`, `evidence`, and `issues`. `DocumentFlowParser` continues deciding node shape but includes raw signals; `DocxParser` applies the shared result to formula objects.

- [ ] **Step 4: Run formula and OMML regression tests**

Run: `python -m pytest tests/test_structure_evidence.py tests/test_official_parser_improvements.py tests/test_omml_converter.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/structure_evidence.py backend/app/services/document_flow_parser.py backend/app/services/docx_parser.py backend/tests/test_structure_evidence.py backend/tests/test_official_parser_improvements.py
git commit -m "feat: score display formula evidence conservatively"
```

### Task 4: Target-Aware Xref Resolution

**Files:**
- Modify: `backend/app/services/xref_resolver.py`
- Modify: `backend/app/services/jats_generator.py`
- Modify: `backend/app/services/jats_auto_fixer.py`
- Modify: `backend/tests/test_xref_resolver.py`
- Modify: `backend/tests/test_jats_auto_fixer.py`

- [ ] **Step 1: Add failing partial-resolution tests**

```python
def test_resolve_against_targets_reports_partial_range():
    result = XrefResolver().resolve_against_targets(
        "See [1-4].", {"ref1", "ref2", "ref3"}
    )[0]
    assert result["rid"] == "ref1 ref2 ref3"
    assert result["status"] == "need_review"
    assert result["missing_targets"] == ["ref4"]


def test_all_missing_target_remains_plain_text_in_delivery_xml():
    article = build_article("See Figure 9.")
    xml = JatsGenerator().generate(article)
    assert 'rid="fig9"' not in xml
    assert "Figure 9" in xml
```

- [ ] **Step 2: Run xref tests**

Run: `python -m pytest tests/test_xref_resolver.py tests/test_jats_auto_fixer.py -q`

Expected: FAIL because `resolve_against_targets` is absent and generator emits unresolved targets.

- [ ] **Step 3: Implement target-aware resolution**

Add:

```python
def resolve_against_targets(self, text: str, target_ids: set[str]):
    results = []
    for match in self.resolve(text):
        requested = match["rid"].split()
        valid = [rid for rid in requested if rid in target_ids]
        missing = [rid for rid in requested if rid not in target_ids]
        results.append({
            **match,
            "rid": " ".join(valid),
            "status": "ok" if not missing else "need_review",
            "missing_targets": missing,
        })
    return results
```

Update mixed-content generation to create `<xref>` only when `rid` is non-empty. Keep the existing auto-fixer as a final safety layer.

- [ ] **Step 4: Run xref, validator, and API tests**

Run: `python -m pytest tests/test_xref_resolver.py tests/test_jats_auto_fixer.py tests/test_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/xref_resolver.py backend/app/services/jats_generator.py backend/app/services/jats_auto_fixer.py backend/tests/test_xref_resolver.py backend/tests/test_jats_auto_fixer.py
git commit -m "feat: resolve xrefs against actual JATS targets"
```

### Task 5: Quality Report Evidence and Formula/Xref Summaries

**Files:**
- Modify: `backend/app/services/quality_scorer.py`
- Modify: `backend/tests/test_quality_scorer.py`
- Modify: `frontend/src/components/QualityReport.vue`

- [ ] **Step 1: Add failing quality-report assertions**

```python
def test_quality_report_summarizes_structure_evidence():
    article = complete_article()
    article["figures"][0].update(status="need_review", confidence=0.65,
                                 evidence=["位于同一章节"], issues=[])
    article["formulas"][0].update(conversion_status="partial",
                                  unsupported_features=["complex_accent"])
    report = QualityScorer().score(article, validation_result(), "<article/>")
    assert report["structure_evidence"]["need_review"] == 1
    assert report["formula_summary"]["partial"] == 1
    assert "complex_accent" in report["formula_summary"]["unsupported_features"]
```

- [ ] **Step 2: Run quality scorer tests**

Run: `python -m pytest tests/test_quality_scorer.py -q`

Expected: FAIL because summary fields are absent.

- [ ] **Step 3: Add backend summaries**

Aggregate evidence statuses across figures, tables, and formulas. Preserve all current score keys and append `structure_evidence`, `formula_summary`, and `xref_summary` so API compatibility is maintained.

- [ ] **Step 4: Render summaries in the existing quality component**

Add three compact cards to `QualityReport.vue`. Use green/yellow/red tags for `ok/need_review/error`; render evidence strings and unsupported formula features without adding a new route or editor.

- [ ] **Step 5: Verify backend and frontend**

Run: `python -m pytest tests/test_quality_scorer.py tests/test_api.py -q`

Run: `npm.cmd run build`

Expected: tests PASS and Vite build succeeds.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/quality_scorer.py backend/tests/test_quality_scorer.py frontend/src/components/QualityReport.vue
git commit -m "feat: expose structure evidence in quality reports"
```

### Task 6: Official Evaluation Detail and Acceptance Gates

**Files:**
- Modify: `backend/app/services/official_xml_comparator.py`
- Modify: `backend/app/services/official_sample_evaluator.py`
- Modify: `backend/tests/test_official_xml_comparator.py`
- Modify: `backend/tests/test_official_samples.py`
- Modify: `backend/evaluate_official_samples.py`

- [ ] **Step 1: Add failing sub-metric and gate tests**

```python
def test_float_dimension_reports_count_caption_and_section_metrics(tmp_path):
    result = compare_generated_and_official_float_xml(tmp_path)
    metrics = result["dimensions"]["figures_tables"]["metrics"]
    assert {"figure_count", "figure_caption", "figure_section"} <= metrics.keys()


def test_official_gate_requires_no_regression():
    summary = aggregate_results([
        {"similarity_score": 92, "schema_valid": True},
        {"similarity_score": 90, "schema_valid": True},
    ])
    assert acceptance_passed(summary, average_floor=91.4,
                             minimum_floor=88, schema_floor=1.0)
```

- [ ] **Step 2: Run official comparator tests**

Run: `python -m pytest tests/test_official_xml_comparator.py tests/test_official_samples.py -q`

Expected: FAIL because detailed metrics and gate function are absent.

- [ ] **Step 3: Add detailed metrics without changing weights**

Split existing object scores into count, caption/content, and section-placement metrics. Keep dimension names and weights unchanged. Add `acceptance_passed()` and CLI exit code `1` when a configured floor regresses.

- [ ] **Step 4: Run official five-sample evaluation**

Run: `python evaluate_official_samples.py`

Expected:
- sample count: 5
- average similarity: at least 91.4
- minimum similarity: at least 88
- schema valid rate: 1.0000
- at least two of figure/table, formula, and xref detailed metrics improve over the recorded baseline.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/official_xml_comparator.py backend/app/services/official_sample_evaluator.py backend/evaluate_official_samples.py backend/tests/test_official_xml_comparator.py backend/tests/test_official_samples.py docs/官方样例对比报告.md
git commit -m "feat: add structure quality acceptance metrics"
```

### Task 7: Documentation and Full Delivery Verification

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Modify: `docs/错误案例分析.md`

- [ ] **Step 1: Update capability and limitation text**

Document evidence-driven conservative binding, status thresholds, xref target validation, metric commands, and measured official-sample results. Keep complex visual table reconstruction, image formula OCR, and full Office Math coverage under current limitations.

- [ ] **Step 2: Run complete backend tests with an explicit temp directory**

Run:

```powershell
$base = 'C:\tmp\word2jats-final-' + [guid]::NewGuid().ToString('N')
python -m pytest -q --basetemp $base
```

Expected: all tests PASS.

- [ ] **Step 3: Run frontend production build**

Run: `npm.cmd run build`

Expected: Vite build succeeds; chunk-size warning is acceptable.

- [ ] **Step 4: Re-run official acceptance**

Run: `python evaluate_official_samples.py`

Expected: all configured floors pass and the Markdown report is regenerated.

- [ ] **Step 5: Build Docker images**

Run: `docker compose build`

Expected: backend and frontend images build successfully and include five official samples.

- [ ] **Step 6: Commit final documentation**

```bash
git add README.md backend/README.md frontend/README.md docs/错误案例分析.md docs/官方样例对比报告.md
git commit -m "docs: document evidence-driven structure quality"
```
