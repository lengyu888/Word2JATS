from lxml import etree

from app.services.jats_generator import JatsGenerator
from app.services.validator import ArticleValidator
from app.services.xref_resolver import XrefResolver


def build_article(paragraph: str) -> dict:
    return {
        "title": "交叉引用测试",
        "authors": [],
        "affiliations": [],
        "abstract": "摘要",
        "keywords": ["交叉引用", "JATS", "测试"],
        "sections": [{"title": "结果", "level": 1, "paragraphs": [paragraph]}],
        "figures": [{"id": "fig1", "caption": "图1 架构", "path": "", "section_index": 0}],
        "tables": [{"id": "tab1", "caption": "表1 结果", "rows": [["A"]], "section_index": 0}],
        "lists": [],
        "formulas": [{"id": "eq1", "content": "x=1", "type": "plain_text", "section_index": 0}],
        "references": [
            {"id": "ref1", "label": "[1]", "raw": "First."},
            {"id": "ref2", "label": "[2]", "raw": "Second."},
            {"id": "ref3", "label": "[3]", "raw": "Third."},
        ],
    }


def test_xref_resolver_recognizes_supported_references():
    matches = XrefResolver().resolve(
        "见图 1、Figure 2、Table 1、式（1）、Eq. (2)、文献[1,2]和[1-3]。"
    )

    assert [(item["text"], item["ref_type"], item["rid"]) for item in matches] == [
        ("图 1", "fig", "fig1"),
        ("Figure 2", "fig", "fig2"),
        ("Table 1", "table", "tab1"),
        ("式（1）", "disp-formula", "eq1"),
        ("Eq. (2)", "disp-formula", "eq2"),
        ("[1,2]", "bibr", "ref1 ref2"),
        ("[1-3]", "bibr", "ref1 ref2 ref3"),
    ]


def test_resolve_plural_and_range_figure_table_formula_xrefs():
    matches = XrefResolver().resolve(
        "Figures 1-3 and Tables 2 and 4 summarize Eqs. (1)-(2)."
    )

    assert [(item["ref_type"], item["rid"]) for item in matches] == [
        ("fig", "fig1 fig2 fig3"),
        ("table", "tab2 tab4"),
        ("disp-formula", "eq1 eq2"),
    ]


def test_resolve_en_dash_bibliography_range_and_word_number_table():
    matches = XrefResolver().resolve(
        "Prior studies [11\u201313] are summarized in Table one and table ten."
    )

    assert [(item["ref_type"], item["rid"]) for item in matches] == [
        ("bibr", "ref11 ref12 ref13"),
        ("table", "tab1"),
        ("table", "tab10"),
    ]


def test_resolve_against_targets_reports_partial_range():
    result = XrefResolver().resolve_against_targets(
        "See [1-4].", {"ref1", "ref2", "ref3"}
    )[0]

    assert result["rid"] == "ref1 ref2 ref3"
    assert result["status"] == "need_review"
    assert result["missing_targets"] == ["ref4"]


def test_all_missing_target_remains_plain_text_in_delivery_xml():
    article = build_article("See Figure 9.")

    xml = JatsGenerator().generate(article)

    assert 'rid="fig9"' not in xml
    assert "Figure 9" in xml


def test_generator_builds_multiple_xrefs_with_text_and_tail():
    article = build_article("如图1和表 1所示，公式见Eq. (1)，相关研究见[1,2]。")

    xml = JatsGenerator().generate(article)
    root = etree.fromstring(xml.encode("utf-8"))
    paragraph = root.xpath("//body/sec/p")[0]

    assert paragraph.text == "如"
    assert [(item.get("ref-type"), item.get("rid"), item.text, item.tail) for item in paragraph] == [
        ("fig", "fig1", "图1", "和"),
        ("table", "tab1", "表 1", "所示，公式见"),
        ("disp-formula", "eq1", "Eq. (1)", "，相关研究见"),
        ("bibr", "ref1 ref2", "[1,2]", "。"),
    ]


def test_validator_reports_valid_and_unresolved_xrefs():
    article = build_article("见图1和图2，参考[1-4]。")
    xml = JatsGenerator().generate(article)

    result = ArticleValidator().validate(article, xml)

    assert "交叉引用检查通过：fig1。" in result["xref_checks"]
    assert "交叉引用检查通过：ref1 ref2 ref3 ref4。" not in result["xref_checks"]
    assert "交叉引用目标不存在：fig2。" in result["warnings"]
    assert "交叉引用目标不存在：ref4。" in result["warnings"]
