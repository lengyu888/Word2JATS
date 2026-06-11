from evaluate import (
    aggregate_results, compare_articles, evaluate_ablation, evaluate_dataset,
    render_ablation_report, render_error_analysis, render_report, category_summary,
)


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

    result = compare_articles(
        "sample.docx", predicted, golden, category="异常排版论文",
        xml_valid=True, schema_valid=False, corrected_schema_valid=True,
        schema_errors_before=5, schema_errors_after=2, elapsed=0.25,
    )

    assert result["title_accuracy"] == 1.0
    assert result["abstract_accuracy"] == 0.0
    assert result["keyword_precision"] == 2 / 3
    assert result["keyword_recall"] == 2 / 3
    assert result["section_title_accuracy"] == 0.5
    assert result["figure_count_accuracy"] == 1.0
    assert result["formula_count_accuracy"] == 0.0
    assert result["reference_count_accuracy"] == 1.0
    assert result["xml_valid_rate"] == 1.0
    assert result["jats_schema_valid_rate"] == 0.0
    assert result["manual_correction_schema_valid_rate"] == 1.0
    assert result["schema_errors_before"] == 5
    assert result["schema_errors_after"] == 2
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
        "jats_schema_valid_rate": 0.0,
        "manual_correction_schema_valid_rate": 1.0,
        "schema_errors_before": 5,
        "schema_errors_after": 2,
        "average_time_seconds": 0.2,
        "failed_items": ["abstract"],
    }
    second = {**first, "sample": "b.docx", "title_accuracy": 0.0, "average_time_seconds": 0.4}

    metrics = aggregate_results([first, second])

    assert metrics["title_accuracy"] == 0.5
    assert metrics["keyword_precision"] == 0.5
    assert metrics["average_time_seconds"] == 0.3
    assert metrics["manual_correction_schema_valid_rate"] == 1.0


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
        "jats_schema_valid_rate": 0.0,
        "manual_correction_schema_valid_rate": 1.0,
        "schema_errors_before": 5,
        "schema_errors_after": 2,
        "category": "异常排版论文",
        "average_time_seconds": 0.1,
        "failed_items": ["abstract"],
    }

    report = render_report([result], aggregate_results([result]))

    assert "# Word2JATS 评测报告" in report
    assert "测试样本数量：**1**" in report
    assert "title_accuracy" in report
    assert "jats_schema_valid_rate" in report
    assert "manual_correction_schema_valid_rate" in report
    assert "分类指标" in report
    assert "典型成功案例" in report
    assert "典型失败案例" in report
    assert "后续优化方向" in report


def test_evaluate_dataset_runs_stratified_30_sample_corpus():
    results, metrics = evaluate_dataset()

    assert len(results) == 30
    assert set(category_summary(results)) == {
        "中文普通论文", "英文普通论文", "图表密集论文",
        "公式密集论文", "参考文献复杂论文", "异常排版论文",
    }
    assert all(
        len([item for item in results if item["category"] == category]) == 5
        for category in category_summary(results)
    )
    assert metrics["xml_valid_rate"] == 1.0
    assert "jats_schema_valid_rate" in metrics
    assert "manual_correction_schema_valid_rate" in metrics


def test_ablation_and_error_reports_cover_final_metrics():
    rows = evaluate_ablation()
    assert list(rows) == [
        "baseline_rules", "document_flow", "document_flow_omml",
        "document_flow_omml_xref", "profile_schema_full",
    ]
    assert "keyword_f1" in rows["profile_schema_full"]
    assert "jats_schema_valid_rate" in rows["profile_schema_full"]
    assert "# Word2JATS 消融实验报告" in render_ablation_report(rows)
    assert "# Word2JATS 错误案例分析" in render_error_analysis([])
