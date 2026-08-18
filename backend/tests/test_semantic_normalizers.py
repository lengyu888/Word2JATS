from app.services.contributor_normalizer import ContributorNormalizer
from app.services.caption_normalizer import CaptionNormalizer
from app.services.formula_semantic_normalizer import FormulaSemanticNormalizer


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
    assert result["normalization_status"] == "unchanged"


def test_splits_english_figure_and_table_labels():
    normalizer = CaptionNormalizer()

    assert normalizer.split("Fig. 1: Calibration plot", "figure") == {
        "label": "Fig. 1",
        "caption": "Calibration plot",
        "status": "normalized",
    }
    assert normalizer.split("Table 2. Results", "table") == {
        "label": "Table 2",
        "caption": "Results",
        "status": "normalized",
    }


def test_splits_scheme_label_from_figure_caption_body():
    assert CaptionNormalizer().split(
        "Scheme 1: Structure of the complex", "figure"
    ) == {
        "label": "Scheme 1",
        "caption": "Structure of the complex",
        "status": "normalized",
    }


def test_splits_chinese_compound_label_and_preserves_unlabeled_text():
    normalizer = CaptionNormalizer()

    assert normalizer.split("图 1-1 系统架构", "figure")["label"] == "图 1-1"
    assert normalizer.split("Calibration plot", "figure") == {
        "label": "",
        "caption": "Calibration plot",
        "status": "unchanged",
    }


def test_extracts_equation_label_and_deduplicates_latex_suffix():
    result = FormulaSemanticNormalizer().normalize({
        "content": (
            "AF = sum P(f_i) x f_i / sum P "
            "AF=\\frac{\\sum_i P(f_i)f_i}{\\sum P} (1)"
        ),
        "latex": "AF=\\frac{\\sum_i P(f_i)f_i}{\\sum P}",
        "type": "omml",
    })

    assert result["label"] == "(1)"
    assert result["content"] == "AF = sum P(f_i) x f_i / sum P"
    assert result["normalization_status"] == "normalized"


def test_extracts_leading_equation_label():
    result = FormulaSemanticNormalizer().normalize({
        "content": "(2) x + y",
        "latex": "x+y",
        "type": "plain_text",
    })

    assert result["label"] == "(2)"
    assert result["content"] == "x + y"


def test_conflicting_formula_representations_degrade_to_partial():
    result = FormulaSemanticNormalizer().normalize({
        "content": "x + y",
        "latex": "z^2",
        "type": "omml",
        "conversion_status": "success",
    })

    assert result["conversion_status"] == "partial"
    assert result["issues"]
    assert result["issues"][0]["code"] == "formula_representation_conflict"
