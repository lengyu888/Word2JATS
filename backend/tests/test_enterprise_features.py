from pathlib import Path

from app.services.jats_generator import JatsGenerator
from app.services.jats_schema_validator import JatsSchemaValidator
from app.services.profile_loader import ProfileLoader
from app.services.reference_parser import ReferenceParser
from app.services.quality_scorer import QualityScorer
from app.services.validator import ArticleValidator


def test_profile_loader_lists_and_applies_metadata():
    loader = ProfileLoader()
    ids = {item["id"] for item in loader.list_profiles()}
    assert {"default", "chinese_journal", "english_journal", "imr_journal"} <= ids

    article = loader.apply_metadata({"title": "Test"}, loader.load("english_journal"))
    assert article["lang"] == "en"
    assert article["journal_id"] == "EN-DEMO"
    assert article["profile"] == "english_journal"


def test_reference_parser_extracts_gbt_and_english_fields():
    parser = ReferenceParser()
    gbt = parser.parse(
        "[1] Zhang S, Li Q. Structured publishing[J]. Journal of XML, 2025, 12(3): 10-18. doi:10.1234/demo.1"
    )
    assert gbt["label"] == "[1]"
    assert gbt["authors"] == ["Zhang S", "Li Q"]
    assert gbt["article_title"] == "Structured publishing"
    assert gbt["year"] == "2025"
    assert gbt["volume"] == "12"
    assert gbt["issue"] == "3"
    assert gbt["fpage"] == "10"
    assert gbt["lpage"] == "18"
    assert gbt["doi"] == "10.1234/demo.1"
    assert gbt["parse_confidence"] > 0.5


def test_schema_validator_uses_local_rng(tmp_path: Path):
    rng = tmp_path / "jats-test.rng"
    rng.write_text(
        """<grammar xmlns="http://relaxng.org/ns/structure/1.0">
        <start><element name="article"><empty/></element></start>
        </grammar>""",
        encoding="utf-8",
    )
    validator = JatsSchemaValidator(tmp_path)
    assert validator.validate("<article/>")["jats_schema_valid"] is True
    invalid = validator.validate("<article><body/></article>")
    assert invalid["jats_schema_valid"] is False
    assert invalid["schema_errors"]


def test_validator_reports_unconfigured_schema_without_false_pass():
    validator = ArticleValidator(JatsSchemaValidator(Path("missing-schema-directory")))
    article = {
        "title": "Test", "abstract": "Abstract", "keywords": ["a", "b", "c"],
        "sections": [{"title": "Intro", "paragraphs": ["Text"]}],
        "authors": [], "affiliations": [], "figures": [], "tables": [],
        "formulas": [], "references": [], "lists": [],
    }
    xml = JatsGenerator().generate(article)
    result = validator.validate(article, xml)
    assert result["passed"] is True
    assert result["xml_well_formed"] is True
    assert result["jats_schema_valid"] is None
    assert result["business_rules"]["passed"] is True
    assert result["schema_errors"]


def test_generator_emits_element_citation_for_structured_reference():
    article = {
        "title": "References", "abstract": "Abstract", "keywords": ["a", "b", "c"],
        "sections": [{"title": "Intro", "paragraphs": ["Text"]}],
        "authors": [], "affiliations": [], "figures": [], "tables": [],
        "formulas": [], "lists": [],
        "references": [{
            "id": "ref1", "label": "[1]", "raw": "Raw citation",
            "authors": ["Zhang S"], "article_title": "Structured publishing",
            "source": "Journal of XML", "year": "2025", "publication_type": "journal",
            "doi": "10.1234/demo.1",
        }],
    }
    xml = JatsGenerator().generate(article)
    assert '<element-citation publication-type="journal">' in xml
    assert "<article-title>Structured publishing</article-title>" in xml
    assert '<pub-id pub-id-type="doi">10.1234/demo.1</pub-id>' in xml


def test_quality_scorer_returns_scores_and_located_issues():
    article = {
        "title": "Test", "abstract": "Abstract", "keywords": ["JATS"],
        "authors": [], "affiliations": [], "journal_title": "", "publisher_name": "",
        "sections": [{"title": "Intro", "paragraphs": []}],
        "figures": [{"id": "fig1", "caption": "", "path": "image.png"}],
        "tables": [], "formulas": [], "references": [], "lists": [],
    }
    validation = {
        "xml_well_formed": True, "jats_schema_valid": False,
        "schema_errors": ["journal-meta requires issn"], "warnings": [],
        "xref_checks": [], "errors": [],
    }

    report = QualityScorer().score(article, validation)

    assert 0 <= report["total_score"] <= 100
    assert set(report["scores"]) == set(QualityScorer.WEIGHTS)
    assert report["issues"]
    assert all(
        {"level", "module", "location", "message", "suggestion"} <= set(issue)
        for issue in report["issues"]
    )
