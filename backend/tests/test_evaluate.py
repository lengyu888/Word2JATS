from evaluate import aggregate_results, compare_articles, evaluate_dataset, render_report


def test_compare_articles_calculates_required_metrics():
    golden = {
        "title": "测试标题",
        "abstract": "测试摘要",
        "keywords": ["JATS", "Word", "XML"],
        "sections": [{"title": "引言"}, {"title": "方法"}],
        "figures": [{}, {}],
        "formulas": [{}],
        "references": [{}, {}],
    }
    predicted = {
        "title": "测试标题",
        "abstract": "错误摘要",
        "keywords": ["JATS", "Word", "额外词"],
        "sections": [{"title": "引言"}, {"title": "结果"}],
        "figures": [{}, {}],
        "formulas": [],
        "references": [{}, {}],
    }

    result = compare_articles("sample.docx", predicted, golden, xml_valid=True, elapsed=0.25)

    assert result["title_accuracy"] == 1.0
    assert result["abstract_accuracy"] == 0.0
    assert result["keyword_precision"] == 2 / 3
    assert result["keyword_recall"] == 2 / 3
    assert result["section_title_accuracy"] == 0.5
    assert result["figure_count_accuracy"] == 1.0
    assert result["formula_count_accuracy"] == 0.0
    assert result["reference_count_accuracy"] == 1.0
    assert result["xml_valid_rate"] == 1.0
    assert result["average_time_seconds"] == 0.25
    assert "abstract" in result["failed_items"]


def test_aggregate_results_averages_each_metric():
    first = {
        "sample": "a.docx",
        "title_accuracy": 1.0,
        "abstract_accuracy": 0.0,
        "keyword_precision": 0.5,
        "keyword_recall": 1.0,
        "section_title_accuracy": 0.5,
        "figure_count_accuracy": 1.0,
        "formula_count_accuracy": 0.0,
        "reference_count_accuracy": 1.0,
        "xml_valid_rate": 1.0,
        "average_time_seconds": 0.2,
        "failed_items": ["abstract"],
    }
    second = {**first, "sample": "b.docx", "title_accuracy": 0.0, "average_time_seconds": 0.4}

    metrics = aggregate_results([first, second])

    assert metrics["title_accuracy"] == 0.5
    assert metrics["keyword_precision"] == 0.5
    assert metrics["average_time_seconds"] == 0.3


def test_render_report_contains_metrics_and_cases():
    result = {
        "sample": "sample.docx",
        "title_accuracy": 1.0,
        "abstract_accuracy": 0.0,
        "keyword_precision": 1.0,
        "keyword_recall": 1.0,
        "section_title_accuracy": 1.0,
        "figure_count_accuracy": 1.0,
        "formula_count_accuracy": 1.0,
        "reference_count_accuracy": 1.0,
        "xml_valid_rate": 1.0,
        "average_time_seconds": 0.1,
        "failed_items": ["abstract"],
    }

    report = render_report([result], aggregate_results([result]))

    assert "# Word2JATS 评测报告" in report
    assert "测试样本数量：**1**" in report
    assert "title_accuracy" in report
    assert "典型成功案例" in report
    assert "典型失败案例" in report
    assert "后续优化方向" in report


def test_evaluate_dataset_runs_all_committed_goldens():
    results, metrics = evaluate_dataset()

    assert len(results) == 4
    assert {item["sample"] for item in results} == {
        "word2jats_demo.docx",
        "word2jats_feature_acceptance.docx",
        "word2jats_image_edge_cases.docx",
        "word2jats_omml_formulas.docx",
    }
    assert metrics["xml_valid_rate"] == 1.0
