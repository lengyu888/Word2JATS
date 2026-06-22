from app.services.contributor_normalizer import ContributorNormalizer
from app.services.caption_normalizer import CaptionNormalizer


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


def test_splits_chinese_compound_label_and_preserves_unlabeled_text():
    normalizer = CaptionNormalizer()

    assert normalizer.split("图 1-1 系统架构", "figure")["label"] == "图 1-1"
    assert normalizer.split("Calibration plot", "figure") == {
        "label": "",
        "caption": "Calibration plot",
        "status": "unchanged",
    }
