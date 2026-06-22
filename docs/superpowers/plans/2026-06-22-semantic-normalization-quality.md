# Semantic Normalization Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve real DOCX-to-JATS semantics through conservative contributor, caption, and formula normalization until official evaluation reaches 94/90/100 without sample-specific rules.

**Architecture:** Add three small normalizers with deterministic, independently tested interfaces. `DocxParser` applies contributor and formula normalization to Article JSON, while `JatsGenerator` applies caption normalization at serialization so editable source captions stay intact. `QualityScorer` reports normalization evidence, and existing DTD/business/xref validators remain the delivery gate.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, python-docx, lxml, pytest, Vue 3, Vite, Docker Compose

---

## File Map

- Create `backend/app/services/contributor_normalizer.py`: remove only trailing author affiliation/footnote markers.
- Create `backend/app/services/caption_normalizer.py`: split supported figure/table labels from caption prose.
- Create `backend/app/services/formula_semantic_normalizer.py`: extract equation labels and remove duplicate plain/LaTeX representations.
- Create `backend/tests/test_semantic_normalizers.py`: focused unit tests for all three normalizers.
- Modify `backend/app/models/schema.py`: preserve additive normalization evidence in API models.
- Modify `backend/app/services/docx_parser.py`: normalize parsed authors and formulas before returning Article JSON.
- Modify `backend/app/services/jats_generator.py`: emit normalized float and formula labels in DTD-valid order.
- Modify `backend/app/services/quality_scorer.py`: expose normalization counts and formula conflicts.
- Modify `backend/tests/test_services.py`: verify parser integration and DTD-valid JATS output.
- Modify `backend/tests/test_quality_scorer.py`: verify additive quality summaries.
- Modify `README.md`, `backend/README.md`, `frontend/README.md`, and `docs/官方样例对比报告.md`: publish measured behavior and limits.

### Task 1: Contributor Marker Normalization

**Files:**
- Create: `backend/app/services/contributor_normalizer.py`
- Create: `backend/tests/test_semantic_normalizers.py`
- Modify: `backend/app/models/schema.py`
- Modify: `backend/app/services/docx_parser.py`

- [ ] **Step 1: Write failing contributor tests**

```python
from app.services.contributor_normalizer import ContributorNormalizer


def test_removes_trailing_affiliation_markers_from_person_name():
    result = ContributorNormalizer().normalize({"name": "Ivo Deblier²", "orcid": ""})
    assert result["name"] == "Ivo Deblier"
    assert result["original_name"] == "Ivo Deblier²"
    assert result["markers"] == ["²"]
    assert result["normalization_status"] == "normalized"


def test_preserves_digits_inside_a_person_name():
    result = ContributorNormalizer().normalize({"name": "Researcher X2", "orcid": ""})
    assert result["name"] == "Researcher X2"
    assert result["markers"] == []
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/test_semantic_normalizers.py -q`

Expected: collection fails because `contributor_normalizer.py` does not exist.

- [ ] **Step 3: Implement the minimal contributor normalizer**

```python
import re
from typing import Any


class ContributorNormalizer:
    MARKER_RE = re.compile(r"(?P<markers>[⁰¹²³⁴⁵⁶⁷⁸⁹*†‡]+)$")

    def normalize(self, author: dict[str, Any]) -> dict[str, Any]:
        result = dict(author)
        original = str(result.get("name", "")).strip()
        match = self.MARKER_RE.search(original)
        if not match:
            result.setdefault("original_name", "")
            result.setdefault("markers", [])
            result.setdefault("normalization_status", "unchanged")
            return result
        marker_text = match.group("markers")
        result["name"] = original[:match.start()].rstrip()
        result["original_name"] = original
        result["markers"] = list(marker_text)
        result["normalization_status"] = "normalized"
        return result
```

Add compatible optional fields to `Author`:

```python
original_name: str = ""
markers: list[str] = Field(default_factory=list)
normalization_status: str = "unchanged"
```

Instantiate one `ContributorNormalizer` in `DocxParser.__init__`, then normalize
the author dictionaries immediately after author detection and before returning
the article.

- [ ] **Step 4: Verify GREEN and parser regressions**

Run: `python -m pytest tests/test_semantic_normalizers.py tests/test_official_parser_improvements.py tests/test_api.py -q`

Expected: all selected tests pass and author API payloads retain ORCID and affiliation IDs.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/contributor_normalizer.py backend/app/models/schema.py backend/app/services/docx_parser.py backend/tests/test_semantic_normalizers.py
git commit -m "feat: normalize contributor footnote markers"
```

### Task 2: Figure and Table Label Separation

**Files:**
- Create: `backend/app/services/caption_normalizer.py`
- Modify: `backend/tests/test_semantic_normalizers.py`
- Modify: `backend/app/services/jats_generator.py`
- Modify: `backend/tests/test_services.py`

- [ ] **Step 1: Write failing caption tests**

```python
from app.services.caption_normalizer import CaptionNormalizer


def test_splits_english_figure_and_table_labels():
    normalizer = CaptionNormalizer()
    assert normalizer.split("Fig. 1: Calibration plot", "figure") == {
        "label": "Fig. 1", "caption": "Calibration plot", "status": "normalized"
    }
    assert normalizer.split("Table 2. Results", "table") == {
        "label": "Table 2", "caption": "Results", "status": "normalized"
    }


def test_splits_chinese_compound_label_and_preserves_unlabeled_text():
    normalizer = CaptionNormalizer()
    assert normalizer.split("图 1-1 系统架构", "figure")["label"] == "图 1-1"
    assert normalizer.split("Calibration plot", "figure")["caption"] == "Calibration plot"
```

- [ ] **Step 2: Run the caption tests and verify RED**

Run: `python -m pytest tests/test_semantic_normalizers.py -q`

Expected: import fails because `caption_normalizer.py` does not exist.

- [ ] **Step 3: Implement `CaptionNormalizer`**

Use one anchored expression per float type. Accept optional whitespace and
punctuation after the label, preserve the original prose when no supported label
matches, and return `status="need_review"` when a label consumes the whole string.

```python
class CaptionNormalizer:
    FIGURE_RE = re.compile(r"^\s*((?:fig(?:ure)?\.?)\s*\d+(?:[-.]\d+)?|图\s*\d+(?:[-－.]\d+)?)\s*[:：.．-]?\s*", re.I)
    TABLE_RE = re.compile(r"^\s*(table\s*\d+(?:[-.]\d+)?|表\s*\d+(?:[-－.]\d+)?)\s*[:：.．-]?\s*", re.I)

    def split(self, text: str, object_type: str) -> dict[str, str]:
        original = str(text or "").strip()
        pattern = self.FIGURE_RE if object_type == "figure" else self.TABLE_RE
        match = pattern.match(original)
        if not match:
            return {"label": "", "caption": original, "status": "unchanged"}
        body = original[match.end():].strip()
        return {
            "label": match.group(1).strip().rstrip(".:：．-"),
            "caption": body,
            "status": "normalized" if body else "need_review",
        }
```

- [ ] **Step 4: Integrate labels into JATS generation**

Instantiate the normalizer in `JatsGenerator`. For each figure and table, emit
`<label>` before `<caption>` and place only normalized caption prose in the
caption paragraph. Use `Fig. {index}` or `Table {index}` only when no source label
exists. Keep `article["figures"][n]["caption"]` and
`article["tables"][n]["caption"]` unchanged.

- [ ] **Step 5: Add and run DTD-valid integration tests**

```python
def test_generator_separates_float_labels_from_caption_text():
    xml = JatsGenerator().generate(article_with_labeled_figure_and_table())
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.xpath("string(//fig/label)") == "Fig. 1"
    assert root.xpath("string(//fig/caption/p)") == "Architecture"
    assert root.xpath("string(//table-wrap/label)") == "Table 1"
    assert root.xpath("string(//table-wrap/caption/p)") == "Results"
```

Run: `python -m pytest tests/test_semantic_normalizers.py tests/test_services.py tests/test_jats_auto_fixer.py -q`

Expected: all tests pass and generated label order remains DTD valid.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/caption_normalizer.py backend/app/services/jats_generator.py backend/tests/test_semantic_normalizers.py backend/tests/test_services.py
git commit -m "feat: separate float labels from captions"
```

### Task 3: Formula Semantic Normalization

**Files:**
- Create: `backend/app/services/formula_semantic_normalizer.py`
- Modify: `backend/tests/test_semantic_normalizers.py`
- Modify: `backend/app/models/schema.py`
- Modify: `backend/app/services/docx_parser.py`
- Modify: `backend/app/services/jats_generator.py`
- Modify: `backend/tests/test_services.py`

- [ ] **Step 1: Write failing formula tests**

```python
from app.services.formula_semantic_normalizer import FormulaSemanticNormalizer


def test_extracts_equation_label_and_deduplicates_latex_suffix():
    result = FormulaSemanticNormalizer().normalize({
        "content": "AF = sum P(f_i) x f_i / sum P AF=\\frac{\\sum_i P(f_i)f_i}{\\sum P}",
        "latex": "AF=\\frac{\\sum_i P(f_i)f_i}{\\sum P}",
        "label": "(1)",
        "type": "omml",
    })
    assert result["label"] == "(1)"
    assert result["content"] == "AF = sum P(f_i) x f_i / sum P"
    assert result["normalization_status"] == "normalized"


def test_conflicting_formula_representations_degrade_to_partial():
    result = FormulaSemanticNormalizer().normalize({
        "content": "x + y", "latex": "z^2", "type": "omml",
        "conversion_status": "success",
    })
    assert result["conversion_status"] == "partial"
    assert result["issues"]
```

- [ ] **Step 2: Run formula tests and verify RED**

Run: `python -m pytest tests/test_semantic_normalizers.py -q`

Expected: import fails because `formula_semantic_normalizer.py` does not exist.

- [ ] **Step 3: Implement deterministic formula normalization**

The normalizer must:

1. copy the formula dictionary;
2. extract a leading/trailing parenthesized integer from `content` when `label`
   is empty;
3. normalize whitespace for comparison only;
4. remove an exact or whitespace-normalized LaTeX suffix from `content`;
5. preserve MathML, OMML, and LaTeX fields verbatim;
6. append a warning issue and set `partial` only when both non-empty
   representations remain materially different after token normalization.

Expose additive model fields:

```python
label: str = ""
original_content: str = ""
normalization_status: str = "unchanged"
```

Apply the normalizer once to every formula after document-flow parsing and before
structure evidence is finalized.

- [ ] **Step 4: Emit formula labels in DTD order**

In `JatsGenerator`, create `<label>` immediately inside `<disp-formula>` and
before `<alternatives>` only when `formula["label"]` is non-empty.

- [ ] **Step 5: Verify formula and DTD regressions**

Run: `python -m pytest tests/test_semantic_normalizers.py tests/test_omml_converter.py tests/test_services.py tests/test_jats_auto_fixer.py -q`

Expected: formula normalization tests pass, complex OMML still degrades safely,
and all generated XML remains DTD valid.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/formula_semantic_normalizer.py backend/app/models/schema.py backend/app/services/docx_parser.py backend/app/services/jats_generator.py backend/tests/test_semantic_normalizers.py backend/tests/test_services.py
git commit -m "feat: normalize formula labels and fallback text"
```

### Task 4: Quality Report Normalization Evidence

**Files:**
- Modify: `backend/app/services/quality_scorer.py`
- Modify: `backend/tests/test_quality_scorer.py`
- Modify: `frontend/src/components/QualityReport.vue`

- [ ] **Step 1: Write failing quality summary tests**

```python
def test_quality_report_counts_semantic_normalizations():
    report = QualityScorer().score(article, validation)
    assert report["normalization_summary"] == {
        "contributors": 1,
        "captions": 2,
        "labeled_formulas": 1,
        "formula_conflicts": 1,
    }
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_quality_scorer.py -q`

Expected: `normalization_summary` is absent.

- [ ] **Step 3: Add the summary without changing score weights**

Count normalized author records, captions recognized by `CaptionNormalizer`,
formula labels, and formulas with `conversion_status="partial"` plus a semantic
conflict issue. Return the summary as an additive top-level quality-report field;
do not alter `WEIGHTS` or existing score calculations.

- [ ] **Step 4: Render compact frontend tags**

Add four tags to the existing quality evidence area. Use green for normalized
contributors/captions/labeled formulas and yellow for formula conflicts. Guard
all access with defaults so historical API responses remain renderable.

- [ ] **Step 5: Verify backend and frontend**

Run: `python -m pytest tests/test_quality_scorer.py tests/test_api.py -q`

Run: `npm.cmd run build`

Expected: backend tests pass and Vite production build succeeds.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/quality_scorer.py backend/tests/test_quality_scorer.py frontend/src/components/QualityReport.vue
git commit -m "feat: report semantic normalization evidence"
```

### Task 5: Official Acceptance Tuning With Generic Evidence

**Files:**
- Modify only normalizers, parser/generator integration, and their tests when a
  generic failing test demonstrates the missing behavior.
- Update: `docs/官方样例对比报告.md`

- [ ] **Step 1: Run the hard gate**

Run: `python evaluate_official_samples.py --average-floor 94 --minimum-floor 90 --schema-floor 1`

Expected: the command identifies whether 94/90/100 is met and reports every
remaining weak dimension.

- [ ] **Step 2: Convert each recoverable gap into a synthetic failing test**

Allowed evidence is Unicode character category, Word run properties, caption
syntax, OMML/MathML/LaTeX structure, section boundaries, flow distance, numbering,
and object type. Tests must use invented names, captions, formulas, and layouts.
Rules conditioned on official filenames, paths, hashes, or exact article phrases
are forbidden.

- [ ] **Step 3: Implement only test-backed generic behavior**

Keep the existing matcher acceptance threshold and uniqueness margin. Preserve
source text and return `need_review` whenever evidence is ambiguous. Do not alter
official-comparator weights or acceptance arithmetic.

- [ ] **Step 4: Re-run focused and hard gates after each change**

Run: `python -m pytest tests/test_semantic_normalizers.py tests/test_official_parser_improvements.py tests/test_services.py -q`

Run: `python evaluate_official_samples.py --average-floor 94 --minimum-floor 90 --schema-floor 1`

Expected final result: average at least 94, minimum at least 90, DTD rate 1.0000.

- [ ] **Step 5: Commit measured improvements**

```bash
git add backend/app backend/tests docs/官方样例对比报告.md
git commit -m "perf: improve semantic JATS normalization"
```

### Task 6: Documentation and Full Delivery Verification

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Modify: `docs/错误案例分析.md`
- Modify: `docs/官方样例对比报告.md`

- [ ] **Step 1: Update measured documentation**

Document the final measured average/minimum/DTD rate, contributor marker cleanup,
caption label separation, formula labels, evidence summaries, and remaining
limits. Keep OCR, visual table reconstruction, publisher-only caption expansion,
and full Office Math coverage under current limitations.

- [ ] **Step 2: Run the complete backend suite**

Run: `$base = 'C:\tmp\word2jats-semantic-' + [guid]::NewGuid().ToString('N'); python -m pytest -q --basetemp $base`

Expected: all tests pass with zero failures.

- [ ] **Step 3: Run the frontend production build**

Run: `npm.cmd run build`

Expected: Vite succeeds; the existing chunk-size warning is acceptable.

- [ ] **Step 4: Run final official acceptance**

Run: `python evaluate_official_samples.py --average-floor 94 --minimum-floor 90 --schema-floor 1`

Expected: `acceptance_passed=true`.

- [ ] **Step 5: Build Docker images**

Run: `docker compose build`

Expected: `word2jats-backend:latest` and `word2jats-frontend:latest` build successfully.

- [ ] **Step 6: Commit final documentation**

```bash
git add README.md backend/README.md frontend/README.md docs/错误案例分析.md docs/官方样例对比报告.md
git commit -m "docs: publish semantic normalization results"
```
