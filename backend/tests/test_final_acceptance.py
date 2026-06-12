from pathlib import Path

from app.services.docx_parser import DocxParser
from app.services.flow_view_builder import FlowViewBuilder
from app.services.jats_auto_fixer import JatsAutoFixer
from app.services.jats_generator import JatsGenerator
from app.services.profile_loader import ProfileLoader
from app.services.quality_scorer import QualityScorer
from app.services.validator import ArticleValidator
from app.services.visual_preview_builder import VisualPreviewBuilder


SAMPLE = Path(__file__).resolve().parents[2] / "sample_documents" / "word2jats_final_acceptance.docx"


def test_final_acceptance_document_covers_full_conversion_flow(tmp_path):
    profile = ProfileLoader().load("chinese_journal")
    parser = DocxParser(SAMPLE, tmp_path / "media", profile)
    article = parser.parse()

    assert article["title"] == "Word2JATS：学术期刊智能结构化转换全流程验收稿"
    assert len(article["authors"]) == 3
    assert len(article["keywords"]) == 5
    assert len(article["sections"]) == 6
    assert len(article["figures"]) == 2
    assert len(article["tables"]) == 2
    assert len(article["lists"]) == 3
    assert len(article["formulas"]) == 5
    assert len(article["references"]) == 3
    assert [formula["conversion_status"] for formula in article["formulas"]] == [
        "success", "success", "success", "success", "partial"
    ]

    xml = JatsGenerator(profile).generate(article)
    validator = ArticleValidator()
    initial_schema = validator.schema_validator.validate(xml)
    xml, auto_fix, final_schema = JatsAutoFixer(validator.schema_validator).fix(xml, initial_schema)
    validation = validator.validate(article, xml, schema_result=final_schema, auto_fix=auto_fix)
    quality = QualityScorer().score(article, validation)
    VisualPreviewBuilder().enrich(article, "a" * 32, quality)
    flow_view = FlowViewBuilder().build(article, parser.document_flow_nodes, validation, quality)

    assert validation["xml_well_formed"] is True
    assert quality["total_score"] > 0
    assert quality["formula_summary"]["partial"] == 1
    assert all(figure["media_url"].startswith("/api/media/") for figure in article["figures"])
    assert all(table["row_count"] > 0 for table in article["tables"])
    assert any(item["jats_tag"] == "article-title" for item in flow_view)
    assert "<fig " in xml
    assert "<table-wrap " in xml
    assert "<disp-formula " in xml
    assert '<xref ref-type="fig"' in xml
    assert '<xref ref-type="table"' in xml
    assert '<xref ref-type="bibr"' in xml


def test_final_acceptance_document_passes_schema_after_publication_metadata_correction(tmp_path):
    profile = ProfileLoader().load("chinese_journal")
    article = DocxParser(SAMPLE, tmp_path / "media", profile).parse()
    article.update({
        "doi": "10.9999/word2jats.final.001",
        "issn": "2099-9999",
        "pub_year": "2026",
        "pub_month": "06",
        "pub_day": "12",
    })
    for index, author in enumerate(article["authors"], start=1):
        author["orcid"] = f"0000-0002-0000-{index:04d}"
        author["affiliation_ids"] = ["aff1"]

    xml = JatsGenerator(profile).generate(article)
    validator = ArticleValidator()
    initial = validator.schema_validator.validate(xml)
    xml, auto_fix, schema = JatsAutoFixer(validator.schema_validator).fix(xml, initial)
    validation = validator.validate(article, xml, schema_result=schema, auto_fix=auto_fix)

    assert validation["xml_well_formed"] is True
    assert validation["jats_schema_valid"] is True
