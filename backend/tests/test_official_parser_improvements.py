from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt
from lxml import etree

from app.services.docx_parser import DocxParser
from app.services.jats_generator import JatsGenerator
from app.services.validator import ArticleValidator
from app.services.document_flow_parser import DocumentFlowParser
from tests.test_services import make_png


def append_omml(paragraph, text: str) -> None:
    math = OxmlElement("m:oMath")
    run = OxmlElement("m:r")
    value = OxmlElement("m:t")
    value.text = text
    run.append(value)
    math.append(run)
    paragraph._p.append(math)


def test_article_title_style_beats_article_type_and_correspondence(tmp_path):
    path = tmp_path / "styled-front.docx"
    document = Document()
    article_type = document.add_paragraph("Original Research")
    article_type.style = document.styles.add_style("Articletype", 1)
    title = document.add_paragraph("A Long and Accurate Academic Article Title")
    title.style = document.styles.add_style("Articletitle", 1)
    document.add_paragraph("Alice Smith1, Bob Jones2")
    document.add_paragraph("1 Department of Medicine, Example University")
    correspondence = document.add_paragraph("Correspondences:")
    correspondence.runs[0].bold = True
    document.add_paragraph("Abstract")
    document.add_paragraph("This is the abstract text.")
    document.add_paragraph("Keywords")
    document.add_paragraph("JATS; XML; publishing")
    heading = document.add_paragraph("Introduction")
    heading.style = document.styles.add_style("1", 1)
    document.add_paragraph("Body text.")
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert article["title"] == "A Long and Accurate Academic Article Title"
    assert [author["name"] for author in article["authors"]] == [
        "Alice Smith", "Bob Jones"
    ]
    assert article["affiliations"] == [
        "1 Department of Medicine, Example University"
    ]
    assert article["keywords"] == ["JATS", "XML", "publishing"]
    assert [section["title"] for section in article["sections"]] == ["Introduction"]


def test_numbered_affiliations_and_numeric_table_text_are_not_sections(tmp_path):
    path = tmp_path / "section-exclusions.docx"
    document = Document()
    title = document.add_paragraph("Reliable Section Detection")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Alice Smith1")
    document.add_paragraph("1 Department of Medicine, Example University")
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; publishing")
    document.add_paragraph("1. Introduction")
    document.add_paragraph("274 242 13844")
    document.add_paragraph("2. Methods")
    document.add_paragraph("Method text.")
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert [section["title"] for section in article["sections"]] == [
        "Introduction", "Methods"
    ]
    assert "274 242 13844" in article["sections"][0]["paragraphs"]


def test_bold_numeric_table_lines_are_not_unnumbered_headings(tmp_path):
    path = tmp_path / "bold-table-lines.docx"
    document = Document()
    title = document.add_paragraph("Table Line Classification")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; tables")
    heading = document.add_paragraph("Results")
    heading.runs[0].bold = True
    data = document.add_paragraph("month 60 months 120 months 180 months")
    data.runs[0].bold = True
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert [section["title"] for section in article["sections"]] == ["Results"]
    assert data.text in article["sections"][0]["paragraphs"]


def test_number_prefixed_table_text_is_not_a_section(tmp_path):
    path = tmp_path / "number-prefixed-table-text.docx"
    document = Document()
    title = document.add_paragraph("Numeric Table Text")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; tables")
    document.add_paragraph("1. Results")
    document.add_paragraph("2 or more procedures 1137/1835 (62.0) 299/417 (71.7)")
    document.add_paragraph("1 month 60 months 120 months 180 months")
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert [section["title"] for section in article["sections"]] == ["Results"]


def test_bullet_subheading_inherits_one_level_below_current_heading(tmp_path):
    path = tmp_path / "bullet-subheading.docx"
    document = Document()
    title = document.add_paragraph("Bullet Subheading")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; headings")
    document.add_paragraph("2.1.1 Device Evidence")
    key_points = document.add_paragraph("\u25cf Key Points")
    key_points.runs[0].bold = True
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert [section["level"] for section in article["sections"]] == [3, 4]


def test_inline_omml_stays_in_paragraph_and_display_omml_is_one_formula(tmp_path):
    path = tmp_path / "inline-display-math.docx"
    document = Document()
    inline = document.add_paragraph("The statistic ")
    append_omml(inline, "χ2")
    inline.add_run(" was significant.")
    display = document.add_paragraph()
    display.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    append_omml(display, "x=1")
    display.add_run(" (1)")
    document.save(path)

    nodes = [node for node in DocumentFlowParser(path).parse() if node.get("text")]

    assert nodes[0]["type"] == "paragraph"
    assert "statistic" in nodes[0]["text"]
    assert nodes[1]["type"] == "formula"
    assert nodes[1]["text"].startswith("x=1")


def test_greek_abbreviation_definition_is_not_plain_text_formula(tmp_path):
    path = tmp_path / "greek-abbreviation.docx"
    document = Document()
    document.add_paragraph("α-KG: α-ketoglutarate")
    document.add_paragraph(r"\frac{a}{b} = sqrt(c)")
    document.save(path)

    nodes = [node for node in DocumentFlowParser(path).parse() if node.get("text")]

    assert nodes[0]["type"] == "paragraph"
    assert nodes[1]["type"] == "formula"


def test_image_after_table_caption_becomes_table_graphic(tmp_path):
    image_path = tmp_path / "table.png"
    image_path.write_bytes(make_png((20, 80, 120)))
    path = tmp_path / "image-table.docx"
    document = Document()
    title = document.add_paragraph("Image Table")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; tables")
    document.add_paragraph("1. Results")
    document.add_paragraph("Table 1. Image-based results")
    document.add_picture(str(image_path), width=Inches(1))
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()
    xml = JatsGenerator().generate(article)

    assert article["figures"] == []
    assert article["tables"][0]["path"].endswith(".png")
    assert article["tables"][0]["status"] == "ok"
    assert article["tables"][0]["confidence"] >= 0.80
    assert "位于同一章节" in article["tables"][0]["evidence"]
    assert '<table-wrap id="tab1">' in xml
    assert '<graphic xlink:href="' in xml


def test_unbound_image_is_preserved_for_review(tmp_path):
    image_path = tmp_path / "unbound.png"
    image_path.write_bytes(make_png((80, 40, 20)))
    path = tmp_path / "unbound-image.docx"
    document = Document()
    title = document.add_paragraph("Unbound Figure")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; figures")
    document.add_paragraph("1. Results")
    document.add_picture(str(image_path), width=Inches(1))
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()
    figure = article["figures"][0]

    assert figure["status"] == "need_review"
    assert figure["confidence"] < 0.80
    assert figure["issues"][0]["level"] == "warning"
    assert "图题" in figure["issues"][0]["message"]


def test_table_caption_prefers_native_table_over_nearby_image(tmp_path):
    image_path = tmp_path / "near-table.png"
    image_path.write_bytes(make_png((40, 70, 110)))
    path = tmp_path / "native-table-preference.docx"
    document = Document()
    title = document.add_paragraph("Native Table Preference")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; tables")
    document.add_paragraph("1. Results")
    document.add_paragraph("Table 1 Results")
    document.add_picture(str(image_path), width=Inches(1))
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Metric"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Accuracy"
    table.cell(1, 1).text = "95%"
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert len(article["tables"]) == 1
    assert article["tables"][0]["caption"] == "Table 1 Results"
    assert article["tables"][0]["rows"] == [
        ["Metric", "Value"], ["Accuracy", "95%"]
    ]
    assert article["tables"][0]["status"] == "ok"
    assert len(article["figures"]) == 1
    assert article["figures"][0]["caption"] == ""
    assert article["figures"][0]["status"] == "need_review"


def test_generator_nests_sections_by_level():
    article = {
        "title": "Nested Sections",
        "authors": [],
        "affiliations": [],
        "abstract": "Summary",
        "keywords": ["JATS", "XML", "sections"],
        "sections": [
            {"title": "Methods", "level": 1, "paragraphs": ["Overview"]},
            {"title": "Dataset", "level": 2, "paragraphs": ["Data"]},
            {"title": "Model", "level": 3, "paragraphs": ["Model text"]},
            {"title": "Results", "level": 1, "paragraphs": ["Results text"]},
        ],
        "figures": [],
        "tables": [],
        "lists": [],
        "formulas": [],
        "references": [],
    }

    root = etree.fromstring(JatsGenerator().generate(article).encode("utf-8"))

    assert len(root.xpath("./body/sec")) == 2
    assert root.xpath("string(./body/sec[1]/title)") == "Methods"
    assert root.xpath("string(./body/sec[1]/sec/title)") == "Dataset"
    assert root.xpath("string(./body/sec[1]/sec/sec/title)") == "Model"
    assert root.xpath("string(./body/sec[2]/title)") == "Results"


def test_parent_section_floats_are_emitted_before_nested_sections():
    article = {
        "title": "Nested Float",
        "journal_title": "Test Journal",
        "journal_id": "TEST",
        "issn": "2750-0001",
        "publisher_name": "Test Publisher",
        "authors": [],
        "affiliations": [],
        "abstract": "Summary",
        "keywords": ["JATS", "XML", "figures"],
        "sections": [
            {"title": "Methods", "level": 1, "paragraphs": ["Overview"]},
            {"title": "Dataset", "level": 2, "paragraphs": ["Data"]},
        ],
        "figures": [{
            "id": "fig1", "caption": "Figure 1", "path": "image.png",
            "section_index": 0,
        }],
        "tables": [],
        "lists": [],
        "formulas": [],
        "references": [],
    }

    xml = JatsGenerator().generate(article)
    root = etree.fromstring(xml.encode("utf-8"))

    assert [child.tag for child in root.xpath("./body/sec[1]/*")] == [
        "title", "p", "fig", "sec"
    ]
    assert ArticleValidator().schema_validator.validate(xml)["jats_schema_valid"] is True


def test_publisher_back_matter_headings_are_not_body_sections(tmp_path):
    path = tmp_path / "publisher-back-matter.docx"
    document = Document()
    title = document.add_paragraph("Back Matter Boundaries")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; publishing")
    document.add_paragraph("1. Introduction")
    document.add_paragraph("Body text.")
    for heading, value in (
        ("Funding", "Supported by the Example Foundation."),
        ("Conflict of Interest", "The authors declare no conflict."),
        ("Author Contributions", "A.S. designed the study."),
        ("Ethics Approval", "Approval was obtained."),
    ):
        paragraph = document.add_paragraph(heading)
        paragraph.runs[0].bold = True
        document.add_paragraph(value)
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert [section["title"] for section in article["sections"]] == ["Introduction"]
    assert len(article["references"]) == 1


def test_numbered_reference_continuation_is_merged(tmp_path):
    path = tmp_path / "reference-continuation.docx"
    document = Document()
    title = document.add_paragraph("Reference Continuations")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; references")
    document.add_paragraph("1. Introduction")
    document.add_paragraph("Body text [1].")
    document.add_paragraph("References")
    document.add_paragraph("[1] Smith A. A long reference title.")
    document.add_paragraph("Journal of Examples. 2024; 1: 1-9.")
    document.add_paragraph("[2] Jones B. Another reference. 2023; 2: 10-12.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()

    assert len(article["references"]) == 2
    assert "Journal of Examples" in article["references"][0]["raw"]


def test_unlabeled_author_year_reference_after_numbered_list_is_new_entry(tmp_path):
    path = tmp_path / "missing-final-label.docx"
    document = Document()
    title = document.add_paragraph("Missing Final Reference Label")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; references")
    document.add_paragraph("1. Introduction")
    document.add_paragraph("Body text [2].")
    document.add_paragraph("References")
    document.add_paragraph("[1] Smith A. First reference. 2023;1:1-2.")
    document.add_paragraph(
        "Jones AB, Brown CD. Second reference. Journal. 2024;2:3-4."
    )
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()
    assert [reference["label"] for reference in article["references"]] == [
        "[1]", "[2]"
    ]


def test_explicit_multi_panel_caption_groups_consecutive_images(tmp_path):
    first = tmp_path / "panel-a.png"
    second = tmp_path / "panel-b.png"
    first.write_bytes(make_png((10, 20, 30)))
    second.write_bytes(make_png((40, 50, 60)))
    path = tmp_path / "multi-panel.docx"
    document = Document()
    title = document.add_paragraph("Multi-panel Figure")
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(18)
    document.add_paragraph("Abstract: Summary")
    document.add_paragraph("Keywords: JATS; XML; figures")
    document.add_paragraph("1. Results")
    document.add_picture(str(first), width=Inches(1))
    document.add_picture(str(second), width=Inches(1))
    document.add_paragraph("Figure 1. Calibration plots of models (A-B)")
    document.add_paragraph("References")
    document.add_paragraph("[1] Example reference.")
    document.save(path)

    article = DocxParser(path, tmp_path / "media").parse()
    root = etree.fromstring(JatsGenerator().generate(article).encode("utf-8"))

    assert len(article["figures"]) == 1
    assert len(article["figures"][0]["paths"]) == 2
    assert len(root.xpath(".//fig[@id='fig1']/graphic")) == 2
