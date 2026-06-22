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
    assert result["normalization_status"] == "unchanged"
