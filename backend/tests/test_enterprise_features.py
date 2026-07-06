from pathlib import Path

from app.services.jats_generator import JatsGenerator
from app.services.jats_schema_validator import JatsSchemaValidator
from app.services.jats_auto_fixer import JatsAutoFixer
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


def test_reference_parser_extracts_compact_english_journal_tail():
    parser = ReferenceParser()
    citation = parser.parse(
        "[2] Smith AB, Jones CD. Prediction models for structured publishing. "
        "Journal of XML Methods 2024;12(3):101-109. "
        "https://doi.org/10.1234/jxml.2024.001",
        index=2,
    )

    assert citation["label"] == "[2]"
    assert citation["authors"] == ["Smith AB", "Jones CD"]
    assert citation["article_title"] == "Prediction models for structured publishing"
    assert citation["source"] == "Journal of XML Methods"
    assert citation["year"] == "2024"
    assert citation["volume"] == "12"
    assert citation["issue"] == "3"
    assert citation["fpage"] == "101"
    assert citation["lpage"] == "109"
    assert citation["doi"] == "10.1234/jxml.2024.001"
    assert citation["publication_type"] == "journal"


def test_reference_parser_extracts_period_separated_journal_tail_and_doi_url():
    parser = ReferenceParser()
    citation = parser.parse(
        "[3] Brown EF, Green GH. Neural fatigue detection using EEG. "
        "Brain Monitoring Journal. 2025;18(2):44-52. "
        "doi: https://doi.org/10.5678/bmj.2025.002",
        index=3,
    )

    assert citation["authors"] == ["Brown EF", "Green GH"]
    assert citation["article_title"] == "Neural fatigue detection using EEG"
    assert citation["source"] == "Brain Monitoring Journal"
    assert citation["year"] == "2025"
    assert citation["volume"] == "18"
    assert citation["issue"] == "2"
    assert citation["fpage"] == "44"
    assert citation["lpage"] == "52"
    assert citation["doi"] == "10.5678/bmj.2025.002"
    assert citation["publication_type"] == "journal"


def test_reference_parser_extracts_comma_separated_journal_reference():
    parser = ReferenceParser()
    citation = parser.parse(
        "[4] Faggiano P, Dasseni N, Gaibazzi N, Rossi A, Henein M, Pressman G, "
        "Cardiac calcification as a marker of subclinical atherosclerosis and predictor "
        "of cardiovascular events: A review of the evidence, European Journal of "
        "Preventive Cardiology, 26 (2019) 1191-1204.",
        index=4,
    )

    assert citation["authors"] == [
        "Faggiano P",
        "Dasseni N",
        "Gaibazzi N",
        "Rossi A",
        "Henein M",
        "Pressman G",
    ]
    assert citation["article_title"] == (
        "Cardiac calcification as a marker of subclinical atherosclerosis and predictor "
        "of cardiovascular events: A review of the evidence"
    )
    assert citation["source"] == "European Journal of Preventive Cardiology"
    assert citation["year"] == "2019"
    assert citation["volume"] == "26"
    assert citation["fpage"] == "1191"
    assert citation["lpage"] == "1204"
    assert citation["publication_type"] == "journal"


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


def test_schema_validator_selects_schema_matching_dtd_version(tmp_path: Path):
    schema_13 = tmp_path / "JATS-Publishing-1-3-MathML3-DTD"
    schema_14 = tmp_path / "JATS-Publishing-1-4-MathML3-DTD"
    schema_13.mkdir()
    schema_14.mkdir()
    (schema_13 / "JATS-journalpublishing1-3-mathml3.dtd").write_text(
        "<!ELEMENT article EMPTY>\n<!ATTLIST article dtd-version CDATA #IMPLIED>",
        encoding="utf-8",
    )
    (schema_14 / "JATS-journalpublishing1-4-mathml3.dtd").write_text(
        "<!ELEMENT article (body)>\n<!ELEMENT body EMPTY>\n<!ATTLIST article dtd-version CDATA #IMPLIED>",
        encoding="utf-8",
    )

    result = JatsSchemaValidator(tmp_path).validate('<article dtd-version="1.4"><body/></article>')

    assert result["schema_file"] == "JATS-journalpublishing1-4-mathml3.dtd"
    assert result["jats_schema_valid"] is True


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


def test_generator_preserves_mixed_citation_for_structured_reference():
    article = {
        "title": "References", "abstract": "Abstract", "keywords": ["a", "b", "c"],
        "sections": [{"title": "Intro", "paragraphs": ["Text"]}],
        "authors": [], "affiliations": [], "figures": [], "tables": [],
        "formulas": [], "lists": [],
        "references": [{
            "id": "ref1", "label": "[1]",
            "raw": "Zhang S. Structured publishing. Journal of XML. 2025;12:10-18.",
            "mixed_citation": "Zhang S. Structured publishing. Journal of XML. 2025;12:10-18.",
            "authors": ["Zhang S"], "article_title": "Structured publishing",
            "source": "Journal of XML", "year": "2025", "publication_type": "journal",
        }],
    }

    xml = JatsGenerator().generate(article)

    assert "<mixed-citation>Zhang S. Structured publishing." in xml
    assert '<element-citation publication-type="journal">' in xml


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


def test_auto_fixer_reduces_official_dtd_graphic_errors():
    article = {
        "title": "Schema fix", "abstract": "Abstract", "keywords": ["a", "b", "c"],
        "sections": [{"title": "Intro", "paragraphs": ["Text"]}],
        "authors": [{"name": "Alice Smith", "orcid": "0000-0000-0000-0001"}],
        "affiliations": ["Demo Lab"], "tables": [], "formulas": [], "lists": [],
        "references": [], "journal_id": "DEMO", "journal_title": "Demo Journal",
        "publisher_name": "Demo Publisher", "issn": "1234-5678",
        "figures": [{"id": "fig1", "caption": "Figure 1", "path": "media/figure.png"}],
    }
    validator = JatsSchemaValidator()
    xml = JatsGenerator().generate(article).replace("xlink:href", "href")
    initial = validator.validate(xml)

    fixed_xml, report, final = JatsAutoFixer(validator).fix(xml, initial)

    assert len(final["schema_errors"]) < len(initial["schema_errors"])
    assert final["jats_schema_valid"] is True
    assert 'xlink:href="media/figure.png"' in fixed_xml
    assert any(item["code"] == "GRAPHIC_XLINK_HREF" for item in report["applied_fixes"])
