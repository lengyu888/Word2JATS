# Semantic Normalization Quality Design

## Objective

Raise the five official sample conversions from an average semantic similarity of
93% to at least 94%, with every sample scoring at least 90 and all generated XML
passing the bundled JATS Publishing 1.3 MathML3 DTD. Improvements must change the
real Article JSON or JATS XML output and must not depend on sample filenames,
paths, hashes, or exact article phrases.

## Scope

This round focuses on three recoverable source patterns:

1. contributor names carrying Word footnote or affiliation markers;
2. OMML formulas whose extracted visible text duplicates their LaTeX fallback or
   omits a recoverable equation label;
3. figure and table captions whose label remains embedded in caption prose.

The existing document-flow parser, float matcher, xref resolver, official
comparator, API contracts, and correction workflow remain in place. OCR, visual
table reconstruction, publisher-only metadata inference, and sample-specific
rules are out of scope.

## Architecture

The parser continues to collect source evidence. Small normalization helpers
operate at ownership boundaries before JATS serialization:

```text
DOCX flow nodes
  -> DocxParser
  -> Article JSON
     -> ContributorNormalizer
     -> FormulaSemanticNormalizer
     -> CaptionNormalizer
  -> JatsGenerator
  -> DTD validation and quality report
  -> official semantic evaluation
```

Each helper returns normalized values plus additive evidence. A helper must
preserve the original value when confidence is insufficient and mark the item as
`need_review`; normalization failure must never abort conversion.

## Contributor Normalization

`ContributorNormalizer` accepts an author dictionary or name string and returns:

```python
{
    "name": "Ivo Deblier",
    "original_name": "Ivo Deblier²",
    "markers": ["²"],
    "normalization_status": "normalized",
}
```

It removes only trailing Unicode superscript digits, ASCII affiliation markers
attached after a name, and trailing `*` or dagger symbols. Digits that are part
of an ordinary alphanumeric name are preserved. Existing ORCID and affiliation
links are untouched. The JATS contributor name uses the normalized value while
the quality report records removed markers.

## Formula Semantic Normalization

`FormulaSemanticNormalizer` accepts the existing formula object and produces a
canonical display representation without changing the OMML or MathML source.
It performs these deterministic operations:

- extract a leading or trailing equation number such as `(1)` into `label`;
- collapse repeated whitespace in extracted visible text;
- detect when the visible text contains a plain rendering followed by a LaTeX
  rendering of the same expression and retain the plain rendering as `content`;
- keep `latex` as the TeX fallback and `mathml` as the preferred structured form;
- set `conversion_status=partial` with an issue when the two representations
  conflict materially instead of guessing.

`JatsGenerator` emits the formula label as `<label>(1)</label>` before
`<alternatives>`. A partial formula remains deliverable and receives a quality
warning. Existing OMML conversion and stable degradation behavior remain intact.

## Caption Normalization

`CaptionNormalizer` recognizes the already supported caption prefixes and
returns a separate label and caption body:

```python
{"label": "Fig. 1", "caption": "Calibration plots of models"}
```

Supported labels include `Fig. 1`, `Figure 1`, `Table 1`, Chinese figure/table
labels, compound numbers, and optional punctuation. The Article JSON retains the
original caption for correction and preview compatibility. JATS output places
the normalized label in `<label>` and only the caption body in
`<caption><p>`. Empty caption bodies remain warnings.

The normalization is structural, not editorial: it does not expand abbreviations,
invent explanatory prose, or copy publisher-enriched captions absent from DOCX.

## Float Matching Refinement

The existing `FloatCandidateMatcher` remains the only binding decision point.
This round may refine ordered-run evidence only when a synthetic regression test
demonstrates a generic layout pattern. Accepted evidence remains limited to:

- same section;
- flow distance and direction;
- caption number;
- native table versus image object kind;
- uniqueness margin among unused candidates.

No binding may be selected below the existing confidence threshold or when the
best candidate lacks the required uniqueness margin.

## Quality and Validation

The quality report adds compact counts for normalized contributors, normalized
captions, labeled formulas, and partial formula conflicts. Each issue keeps the
existing shape: `level`, `module`, `location`, `message`, and `suggestion`.

DTD validation remains the delivery gate. New XML structures must pass the local
JATS Publishing 1.3 MathML3 DTD before affecting acceptance scores. Business
rules and xref target checks remain unchanged.

## Testing Strategy

All behavior changes use red-green-refactor tests:

- unit tests for safe contributor marker removal and preservation cases;
- formula tests for equation labels, duplicate representations, and conflict
  degradation;
- caption tests for English, Chinese, compound labels, punctuation, and empty
  bodies;
- JATS tests for `<label>` placement and DTD validity;
- parser regressions built from synthetic DOCX structures without official
  filenames or copied article text;
- complete backend pytest, frontend production build, Docker image build, and
  official five-sample acceptance evaluation.

## Acceptance Criteria

- average official semantic similarity is at least 94%;
- minimum official sample score is at least 90;
- JATS Publishing 1.3 DTD valid rate is 100%;
- no existing API response field is removed or changed incompatibly;
- no sample-specific rule or external commercial service is introduced;
- all backend tests and the frontend production build pass;
- backend and frontend Docker images build successfully.

If the semantic gates cannot be reached with evidence-backed transformations,
the implementation stops with measured results rather than weakening metric
weights or adding article-specific rules.
