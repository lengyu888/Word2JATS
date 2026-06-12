from app.services.flow_view_builder import FlowViewBuilder


def complete_article():
    return {
        "title": "Mapping title",
        "authors": [{"name": "Alice Smith", "orcid": ""}],
        "affiliations": ["Publishing Lab"],
        "abstract": "Mapping abstract",
        "keywords": ["JATS", "DOCX", "mapping"],
        "sections": [{
            "title": "Introduction", "level": 1,
            "paragraphs": ["Plain body paragraph.", "See Figure 1."],
        }],
        "figures": [{"id": "fig1", "caption": "Figure 1 Overview", "path": "media/a.png", "section_index": 0}],
        "tables": [{"id": "tab1", "caption": "Table 1 Results", "rows": [["A"]], "section_index": 0}],
        "lists": [{"id": "list1", "items": ["Item"], "section_index": 0}],
        "formulas": [{"id": "eq1", "content": "x=1", "type": "plain_text", "section_index": 0}],
        "references": [{"id": "ref1", "label": "[1]", "raw": "Reference one"}],
    }


def test_build_from_article_covers_core_jats_mappings():
    view = FlowViewBuilder().build(complete_article(), [], {}, {})

    node_types = {item["node_type"] for item in view}
    tags = {item["jats_tag"] for item in view}

    assert {
        "title", "author", "affiliation", "abstract", "keyword", "heading",
        "paragraph", "figure", "figure_caption", "table", "table_caption",
        "formula", "list", "reference",
    } <= node_types
    assert {
        "article-title", "contrib", "aff", "abstract/p", "kwd",
        "sec/title", "p", "fig/graphic", "fig/caption/p",
        "table-wrap/table", "table-wrap/caption/p", "disp-formula/tex-math",
        "list/list-item", "ref-list/ref",
    } <= tags


def test_flow_view_attaches_quality_issue_to_target_node():
    article = complete_article()
    quality = {
        "issues": [{
            "level": "warning",
            "module": "figure_table",
            "location": "article.figures.fig1",
            "message": "fig1 缺少图题或内容",
            "suggestion": "补充图题",
        }]
    }

    view = FlowViewBuilder().build(article, [], {}, quality)
    figure = next(item for item in view if item["node_type"] == "figure")

    assert figure["status"] == "warning"
    assert figure["issues"][0]["message"] == "fig1 缺少图题或内容"
    assert figure["issues"][0]["suggestion"] == "补充图题"


def test_flow_view_preserves_source_indexes_and_section_binding():
    article = complete_article()
    nodes = [
        {"flow_index": 0, "paragraph_index": 0, "type": "title", "text": "Mapping title"},
        {"flow_index": 1, "paragraph_index": 1, "type": "heading", "text": "1 Introduction"},
        {
            "flow_index": 2, "paragraph_index": 2, "type": "image", "text": "",
            "media_path": "word/media/image1.png",
        },
    ]

    view = FlowViewBuilder().build(article, nodes, {}, {})
    image = next(item for item in view if item["node_type"] == "figure")

    assert image["source"]["paragraph_index"] == 2
    assert image["source"]["media_name"] == "image1.png"
    assert image["section_id"] == "sec1"
    assert image["target_id"] == "fig1"
