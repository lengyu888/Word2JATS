from app.services.quality_scorer import QualityScorer


def test_quality_report_summarizes_structure_and_xref_evidence():
    article = {
        "title": "Evidence",
        "abstract": "Abstract",
        "keywords": ["JATS", "XML", "quality"],
        "authors": [{"name": "Alice", "orcid": "0000-0000-0000-0001"}],
        "affiliations": ["Publishing Lab"],
        "journal_title": "Journal",
        "publisher_name": "Publisher",
        "sections": [{"title": "Results", "paragraphs": ["See Figure 1."]}],
        "figures": [{
            "id": "fig1", "caption": "Figure 1", "path": "image.png",
            "status": "need_review", "confidence": 0.65,
            "evidence": ["位于同一章节"], "issues": [],
        }],
        "tables": [],
        "formulas": [{
            "id": "eq1", "content": "x=1", "conversion_status": "partial",
            "status": "need_review", "confidence": 0.70,
            "unsupported_features": ["complex_accent"], "issues": [],
        }],
        "references": [{"id": "ref1", "raw": "Reference", "parse_confidence": 0.8}],
        "lists": [],
    }
    validation = {
        "xml_well_formed": True,
        "jats_schema_valid": True,
        "schema_errors": [],
        "errors": [],
        "warnings": ["交叉引用目标不存在：fig9。"],
        "xref_checks": [
            "交叉引用检查通过：fig1。",
            "交叉引用需要人工复核：Figure 9 缺少目标 fig9。",
            "交叉引用已归一化：fig1a -> fig1。",
        ],
    }

    report = QualityScorer().score(article, validation)

    assert report["structure_evidence"]["need_review"] == 2
    assert report["structure_evidence"]["average_confidence"] == 0.68
    assert report["formula_summary"]["partial"] == 1
    assert "complex_accent" in report["formula_summary"]["unsupported_features"]
    assert report["xref_summary"] == {
        "passed": 1, "need_review": 1, "missing": 1, "normalized": 1
    }
    assert report["float_evidence_summary"] == {
        "total": 1, "ok": 0, "need_review": 1, "warning": 0, "error": 0,
        "average_confidence": 0.65,
    }
    assert report["xref_normalization_summary"] == {"normalized": 1}


def test_quality_report_counts_semantic_normalizations():
    article = {
        "title": "Normalization evidence",
        "abstract": "Abstract",
        "keywords": ["JATS", "XML", "quality"],
        "authors": [{
            "name": "Alice Smith",
            "original_name": "Alice Smith²",
            "normalization_status": "normalized",
        }],
        "affiliations": ["Publishing Lab"],
        "journal_title": "Journal",
        "publisher_name": "Publisher",
        "sections": [{"title": "Results", "paragraphs": ["Results text."]}],
        "figures": [{"id": "fig1", "caption": "Fig. 1 Architecture"}],
        "tables": [{"id": "tab1", "caption": "Table 1. Results", "rows": [["A"]]}],
        "formulas": [{
            "id": "eq1",
            "label": "(1)",
            "content": "x+y",
            "latex": "z^2",
            "conversion_status": "partial",
            "issues": [{
                "code": "formula_representation_conflict",
                "level": "warning",
                "message": "Formula semantic representations conflict.",
                "suggestion": "Review the source equation.",
            }],
        }],
        "references": [{"id": "ref1", "raw": "Reference", "parse_confidence": 0.8}],
        "lists": [],
    }
    validation = {
        "xml_well_formed": True,
        "jats_schema_valid": True,
        "schema_errors": [],
        "errors": [],
        "warnings": [],
        "xref_checks": [],
    }

    report = QualityScorer().score(article, validation)

    assert report["normalization_summary"] == {
        "contributors": 1,
        "captions": 2,
        "labeled_formulas": 1,
        "formula_conflicts": 1,
    }
