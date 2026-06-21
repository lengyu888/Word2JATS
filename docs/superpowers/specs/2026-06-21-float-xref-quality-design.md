# Float and Xref Quality Design

## Goal

Improve official-sample semantic similarity from 91.6% to at least 93.0% while preserving a minimum per-sample score of 88 and a JATS Publishing 1.3 DTD valid rate of 100%.

The implementation must generalize to unseen DOCX files. Rules based on official sample filenames, directory paths, or fixed sample text are prohibited.

## Scope

This round focuses on the two largest recoverable gaps in the current report:

- figure and table count, caption, and section placement;
- figure, table, formula, and bibliography xref recovery.

Metadata, reference parsing, and OMML conversion may only be changed when required to prevent a regression caused by this work.

## Architecture

### Float Candidate Matcher

Add a focused matching service that consumes existing document-flow nodes. It must not reparse DOCX. It will build candidates between captions and media/native tables using:

- same-section membership;
- normalized object number and optional sub-number;
- flow distance and direction;
- explicit figure/table caption syntax;
- object kind: image, native table, or table-like image;
- nearby caption and paragraph context.

High-confidence candidates are bound automatically. Ambiguous candidates remain separate and receive `need_review`; cross-section candidates are rejected.

### Float Classification

Native Word tables remain tables. Images are classified conservatively as figures unless strong local evidence identifies a table caption and a one-to-one table-image relationship. Multi-panel figures may retain multiple media paths under one figure when caption syntax and adjacency support grouping.

Caption normalization removes label-only formatting differences, line-break noise, and redundant whitespace while preserving the original caption text in the article data. JATS placement continues to use the real section index.

### Target-Aware Xref Recovery

Extend the existing resolver rather than replacing it. Supported forms will include:

- singular and plural figure/table references;
- numeric ranges and comma/and-separated lists;
- subfigure identifiers such as `Fig. 1a` and `Figure 2(b)`;
- formula references with parenthesized numbers;
- bibliography ranges using hyphen, en dash, or em dash.

Resolution is checked against actual article target IDs before XML generation. Missing targets remain plain text and produce a review warning. Partially valid compound references only emit valid `rid` values and report missing targets.

## Data Flow

1. `DocumentFlowParser` produces ordered nodes.
2. `DocxParser` identifies sections and object candidates.
3. The float matcher scores and binds captions to figures/tables.
4. `StructureEvidence` records confidence, evidence, status, and issues.
5. `XrefResolver` recognizes references and resolves them against article IDs.
6. `JatsGenerator` emits only valid float placement and xref targets.
7. Validator and quality report expose ambiguity and missing targets.
8. Official evaluation reports count, caption, section, and xref sub-metrics.

## Error Handling

- No ambiguous binding may fail conversion.
- No caption may be silently discarded.
- No missing xref target may be emitted as an invalid `rid`.
- Cross-section matching is rejected unless an explicit object number establishes a unique target and tests demonstrate the behavior is safe.
- Existing `need_review`, `warning`, and issue structures remain API-compatible.

## Testing

Use test-driven development for each behavior. Add tests for:

- image/figure and image/table discrimination;
- caption before and after object;
- multi-panel figure grouping;
- unmatched captions and media;
- section-boundary rejection;
- figure/table ranges, lists, and subfigure xrefs;
- partially missing and fully missing targets;
- generated JATS containing only existing IDs.

Acceptance gates:

- all existing backend tests pass;
- frontend production build passes;
- average official semantic similarity is at least 93.0%;
- minimum official sample score is at least 88;
- JATS 1.3 DTD valid rate is 100%;
- no existing dimension or API contract regresses without an explicit documented reason.

## Documentation

Update all three README files and the official comparison report with measured results. Describe evidence-driven matching and current limitations without claiming complete coverage of arbitrary visual tables or every citation style.
