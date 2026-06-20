# Official JATS Quality Optimization Design

## 1. Objective

Use the five competition-provided DOCX/XML pairs as structural references to improve the actual Word-to-JATS conversion pipeline. The generated XML must become closer to the official JATS Publishing 1.3 output through better parsing, semantic classification, hierarchy recovery, reference resolution, and XML generation.

Similarity is a diagnostic and acceptance metric. It must not be increased by hiding differences, weakening validation, or assigning favorable weights without improving generated XML.

## 2. Acceptance Criteria

- All five official sample DOCX files convert successfully.
- Every generated XML document is well formed and passes the bundled JATS Publishing 1.3 MathML3 DTD validation.
- Official comparison score averages at least 90, with every sample scoring at least 80.
- The score is based on recoverable semantic structure and content, not global counts of identically named tags.
- Raw structural differences remain visible even when a field is classified as unavailable from the source DOCX.
- Existing API response fields and frontend workflows remain compatible.
- The complete backend test suite, frontend production build, and Docker five-sample workflow pass.

## 3. Ground-Truth Boundary

The official XML is treated as the reference for JATS structure, node ordering, attributes, nesting, identifiers, and representation choices. It may also contain publisher-enriched data that does not exist in the source Word document.

Comparison therefore distinguishes:

1. **Recoverable content**: title, abstract, keywords, section hierarchy, body paragraphs, figures, tables, formulas, references, and explicit cross-references present in the DOCX.
2. **Publisher-enriched content**: identifiers, editorial history, funding metadata, normalized author identities, issue metadata, or other values absent from the DOCX.
3. **Representation differences**: semantically equivalent JATS structures that use different optional containers or citation detail levels.

Missing recoverable content reduces the score. Missing publisher-enriched content is reported separately and is not silently treated as a parser failure. All differences remain available in the diagnostic report.

## 4. Architecture

The public pipeline remains:

```text
DOCX
  -> DocumentFlowParser
  -> DocxParser semantic article JSON
  -> JatsGenerator
  -> JATS 1.3 DTD validation and bounded auto-repair
  -> official XML diagnostics
  -> quality report and frontend presentation
```

The optimization introduces no sample-number-specific parser rules. Official samples drive tests and reveal general rules that apply to other academic manuscripts.

## 5. Official XML Diagnostics

`OfficialXmlComparator` will compare semantic locations rather than global tag counts.

### 5.1 Compared dimensions

- Front metadata: primary article title, abstract text, keyword set, contributors, and affiliations.
- Body structure: normalized section-title sequence, section levels, nesting, and paragraph coverage.
- Figures: count, labels, captions, graphic presence, chapter placement, and identifiers.
- Tables: count, labels, captions, dimensions, chapter placement, and identifiers.
- Formulas: count, OMML-derived MathML/TeX availability, labels, and chapter placement.
- References: count, labels, normalized citation text, DOI, year, and article title when available.
- Cross-references: type, target class, target existence, and source-text coverage.
- Compliance: well-formed XML and JATS Publishing 1.3 DTD validity.

### 5.2 Score integrity

- XPath expressions target semantic locations, such as `/article/front/article-meta/title-group/article-title`; reference article titles are not counted as document titles.
- Text comparison normalizes whitespace and punctuation without deleting meaningful content.
- Sequence metrics preserve order for sections and references.
- Precision and recall are both used where extra false-positive objects matter.
- A DTD-invalid document cannot meet the acceptance threshold.
- The report exposes dimension scores, raw generated/official facts, and individual differences.

## 6. Parser Improvements

### 6.1 Metadata

- Support keyword labels and values in one paragraph or adjacent paragraphs.
- Normalize Chinese and English separators and marker punctuation.
- Prevent abstract, keyword, caption, and reference paragraphs from becoming section headings.
- Preserve contributor and affiliation information available in the source.

### 6.2 Section hierarchy

- Retain heading level from style and numbering evidence.
- Normalize unreasonable level jumps conservatively.
- Generate a hierarchical section tree while retaining the existing flat article JSON compatibility fields.
- Assign paragraphs and floating objects to the nearest active section in document order.

### 6.3 Figures, tables, and formulas

- Classify media by document-flow context instead of treating every embedded image as a figure.
- Avoid converting short mathematical-looking prose into formulas without adequate evidence.
- Prefer native OMML evidence for display formulas.
- Bind captions to nearby objects in document order, preserving unbound objects as review items.
- Keep table dimensions and cell text stable while handling merged-cell limitations conservatively.

### 6.4 References

- Detect reference-section boundaries independently from heading parsing.
- Join wrapped continuation paragraphs and split numbered entries reliably.
- Preserve raw citation text while extracting structured fields when confidence is sufficient.
- Avoid inventing citation fields that are not present.

### 6.5 Cross-references

- Support singular, plural, range, and coordinated English and Chinese forms.
- Resolve figure, table, formula, and bibliography targets against generated IDs.
- Preserve original visible text while producing valid JATS `xref` nodes.
- Report unresolved or ambiguous references for review.

## 7. JATS Generation Improvements

- Follow JATS Publishing 1.3 element ordering and content models in `journal-meta`, `article-meta`, `body`, and `back`.
- Emit nested `sec` elements from recovered heading hierarchy.
- Place figures, tables, formulas, and lists in their source sections and document order where the article model provides ordering evidence.
- Generate `element-citation` only for confidently parsed references and retain `mixed-citation` as a faithful fallback.
- Use `xlink:href` and namespace declarations required by JATS 1.3.
- Keep bounded schema auto-repair as a safety layer, not as the primary structure generator.

## 8. Testing Strategy

Implementation follows test-driven development:

1. Capture the current official-sample baseline.
2. Add a failing focused test for one general parsing or generation defect.
3. Implement the minimum general fix.
4. Run the focused test and relevant official sample.
5. Run the full backend suite after each subsystem.

Tests cover semantic comparator paths, keywords, nested sections, media classification, formula false positives, reference boundaries, compound xrefs, DTD validity, and API compatibility.

The official five-sample evaluation produces `docs/官方样例对比报告.md` with per-sample dimension scores, average/minimum score, DTD pass rate, recoverable differences, publisher-enriched differences, and remaining review items.

## 9. Frontend and Reporting

The existing official comparison view will show:

- Overall score and acceptance status.
- Per-dimension scores.
- Recoverable conversion errors.
- Publisher-enriched fields absent from the DOCX.
- Raw structural differences and suggestions.
- DTD validation status.

Batch results show each score plus average and minimum values. Existing conversion, correction, validation, preview, and export functions remain unchanged.

## 10. Error Handling and Stability

- Unsupported DOCX constructs degrade to preserved text or `need_review` items.
- A comparison failure never causes conversion failure.
- Missing official XML produces an unavailable comparison result rather than an exception.
- Official XML parsing uses local, no-network parsers and does not execute external entities.
- No commercial API, external model, or online service is introduced.

## 11. Non-Goals

- Exact byte-for-byte reproduction of publisher XML.
- Hard-coded transformations for a specific official sample filename or sample number.
- Automatic invention of metadata absent from the DOCX.
- Complete support for every Word layout, Office Math, merged-cell, or citation-style variant.
