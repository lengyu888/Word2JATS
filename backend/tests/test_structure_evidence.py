from app.services.structure_evidence import StructureEvidence


def test_status_thresholds_are_conservative():
    scorer = StructureEvidence()

    assert scorer.status_for(0.80) == "ok"
    assert scorer.status_for(0.79) == "need_review"
    assert scorer.status_for(0.50) == "need_review"
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
    assert result["evidence"] == []
    assert "跨章节" in result["issues"][0]["message"]


def test_math_paragraph_is_high_confidence_display_formula():
    result = StructureEvidence().score_formula(
        has_math_paragraph=True,
        pure_math=True,
        aligned=False,
        numbered=False,
    )

    assert result["is_display"] is True
    assert result["confidence"] >= 0.80
    assert result["status"] == "ok"
    assert "OMML 公式段" in result["evidence"]


def test_inline_math_is_not_promoted_to_display_formula():
    result = StructureEvidence().score_formula(
        has_math_paragraph=False,
        pure_math=False,
        aligned=False,
        numbered=False,
    )

    assert result["is_display"] is False
    assert result["confidence"] < 0.50
    assert result["status"] == "warning"
    assert result["issues"][0]["level"] == "warning"


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
    assert result["issues"] == []
    assert "位于同一章节" in result["evidence"]
    assert "编号一致" in result["evidence"]
