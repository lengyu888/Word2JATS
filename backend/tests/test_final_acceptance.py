from pathlib import Path

import pytest

from app.services.docx_parser import DocxParser
from app.services.flow_view_builder import FlowViewBuilder
from app.services.jats_auto_fixer import JatsAutoFixer
from app.services.jats_generator import JatsGenerator
from app.services.profile_loader import ProfileLoader
from app.services.quality_scorer import QualityScorer
from app.services.validator import ArticleValidator
from app.services.visual_preview_builder import VisualPreviewBuilder


SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_documents"
SAMPLE_NAMES = (
    "样例1.docx",
    "样例2.docx",
    "样例3.docx",
    "样例4.docx",
    "样例5.docx",
)


@pytest.mark.parametrize("sample_name", SAMPLE_NAMES)
def test_sample_documents_cover_conversion_flow(sample_name, tmp_path):
    sample = SAMPLE_DIR / sample_name
    assert sample.is_file(), f"Missing sample document: {sample_name}"

    profile = ProfileLoader().load("chinese_journal")
    parser = DocxParser(sample, tmp_path / "media", profile)
    article = parser.parse()

    assert article["title"]
    assert article["sections"]
    assert article["figures"]
    assert article["tables"]
    assert article["references"]

    xml = JatsGenerator(profile).generate(article)
    validator = ArticleValidator()
    initial_schema = validator.schema_validator.validate(xml)
    xml, auto_fix, final_schema = JatsAutoFixer(validator.schema_validator).fix(
        xml, initial_schema
    )
    validation = validator.validate(
        article, xml, schema_result=final_schema, auto_fix=auto_fix
    )
    quality = QualityScorer().score(article, validation)
    VisualPreviewBuilder().enrich(article, "a" * 32, quality)
    flow_view = FlowViewBuilder().build(
        article, parser.document_flow_nodes, validation, quality
    )

    assert validation["xml_well_formed"] is True
    assert validation["jats_schema_valid"] is True
    assert quality["total_score"] > 0
    assert flow_view
    assert any(item["jats_tag"] == "article-title" for item in flow_view)
    assert "<fig " in xml
    assert "<table-wrap " in xml
    assert "<ref-list>" in xml


@pytest.mark.parametrize("sample_name", SAMPLE_NAMES)
def test_sample_documents_stay_schema_valid_after_metadata_correction(sample_name, tmp_path):
    sample = SAMPLE_DIR / sample_name
    profile = ProfileLoader().load("chinese_journal")
    article = DocxParser(sample, tmp_path / "media", profile).parse()
    article.update({
        "doi": "10.9999/word2jats.sample.001",
        "issn": "2099-9999",
        "pub_year": "2026",
        "pub_month": "06",
        "pub_day": "29",
    })
    for index, author in enumerate(article.get("authors", []), start=1):
        author["orcid"] = f"0000-0002-0000-{index:04d}"
        author["affiliation_ids"] = ["aff1"]

    xml = JatsGenerator(profile).generate(article)
    validator = ArticleValidator()
    initial = validator.schema_validator.validate(xml)
    xml, auto_fix, schema = JatsAutoFixer(validator.schema_validator).fix(xml, initial)
    validation = validator.validate(article, xml, schema_result=schema, auto_fix=auto_fix)

    assert validation["xml_well_formed"] is True
    assert validation["jats_schema_valid"] is True
