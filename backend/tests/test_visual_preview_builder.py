from app.services.visual_preview_builder import VisualPreviewBuilder


def test_visual_preview_builder_enriches_figures_tables_and_xrefs():
    article = {
        "sections": [{
            "title": "结果",
            "paragraphs": ["如图1和表1所示，结果得到改善。"],
        }],
        "figures": [{"id": "fig1", "caption": "图1 架构", "path": "temp/demo/media/figure_1.png", "section_index": 0}],
        "tables": [{"id": "tab1", "caption": "表1 结果", "rows": [["指标", "值"], ["准确率", "95%"]], "section_index": 0}],
    }
    quality = {"issues": [{
        "level": "warning",
        "module": "figure_table",
        "location": "article.figures.fig1",
        "message": "图片需要复核",
        "suggestion": "核对图题",
    }]}

    VisualPreviewBuilder().enrich(article, "a" * 32, quality)

    figure = article["figures"][0]
    table = article["tables"][0]
    assert figure["filename"] == "figure_1.png"
    assert figure["media_url"] == f"/api/media/{'a' * 32}/figure_1.png"
    assert figure["section_id"] == "sec1"
    assert figure["section_title"] == "结果"
    assert figure["referenced_by"] == ["sec1-p1-xref1"]
    assert figure["status"] == "warning"
    assert figure["issues"][0]["suggestion"] == "核对图题"
    assert table["row_count"] == 2
    assert table["column_count"] == 2
    assert table["referenced_by"] == ["sec1-p1-xref2"]


def test_visual_preview_builder_warns_for_missing_content():
    article = {
        "sections": [],
        "figures": [{"id": "fig1", "caption": "", "path": "", "section_index": -1}],
        "tables": [{"id": "tab1", "caption": "", "rows": [], "section_index": -1}],
    }

    VisualPreviewBuilder().enrich(article, "", {})

    assert article["figures"][0]["status"] == "warning"
    assert article["tables"][0]["status"] == "warning"
    assert article["figures"][0]["issues"]
    assert article["tables"][0]["issues"]
