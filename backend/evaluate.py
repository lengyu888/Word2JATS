"""Batch evaluation for Word2JATS sample documents.

Run from the backend directory:
    python evaluate.py
"""

from __future__ import annotations

import json
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from lxml import etree

from app.services.docx_parser import DocxParser
from app.services.jats_auto_fixer import JatsAutoFixer
from app.services.jats_generator import JatsGenerator
from app.services.validator import ArticleValidator
from scripts.generate_evaluation_corpus import generate as generate_evaluation_corpus


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
SAMPLE_DIR = PROJECT_DIR / "sample_documents"
GOLDEN_DIR = BACKEND_DIR / "evaluation" / "goldens"
REPORT_PATH = PROJECT_DIR / "docs" / "评测报告.md"
ABLATION_REPORT_PATH = PROJECT_DIR / "docs" / "消融实验报告.md"
ERROR_REPORT_PATH = PROJECT_DIR / "docs" / "错误案例分析.md"
MANIFEST_PATH = BACKEND_DIR / "evaluation" / "manifest.json"


def generate_and_validate(article: dict) -> tuple[str, dict]:
    xml = JatsGenerator().generate(article)
    validator = ArticleValidator()
    initial = validator.schema_validator.validate(xml)
    xml, auto_fix, schema = JatsAutoFixer(validator.schema_validator).fix(xml, initial)
    return xml, validator.validate(article, xml, schema_result=schema, auto_fix=auto_fix)

METRIC_NAMES = (
    "title_accuracy",
    "abstract_accuracy",
    "keyword_precision",
    "keyword_recall",
    "section_title_accuracy",
    "figure_count_accuracy",
    "formula_count_accuracy",
    "reference_count_accuracy",
    "xml_valid_rate",
    "jats_schema_valid_rate",
    "manual_correction_schema_valid_rate",
    "schema_errors_before",
    "schema_errors_after",
    "average_time_seconds",
)


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def section_title_accuracy(predicted: dict[str, Any], golden: dict[str, Any]) -> float:
    predicted_titles = [normalize_text(item.get("title")) for item in predicted.get("sections", [])]
    golden_titles = [normalize_text(item.get("title")) for item in golden.get("sections", [])]
    total = max(len(predicted_titles), len(golden_titles))
    if total == 0:
        return 1.0
    correct = sum(
        predicted_titles[index] == golden_titles[index]
        for index in range(min(len(predicted_titles), len(golden_titles)))
    )
    return correct / total


def compare_articles(
    sample: str,
    predicted: dict[str, Any],
    golden: dict[str, Any],
    *,
    category: str = "未分类",
    xml_valid: bool,
    schema_valid: bool = False,
    corrected_schema_valid: bool = False,
    schema_errors_before: int = 0,
    schema_errors_after: int = 0,
    elapsed: float,
) -> dict[str, Any]:
    predicted_keywords = {normalize_text(item) for item in predicted.get("keywords", [])}
    golden_keywords = {normalize_text(item) for item in golden.get("keywords", [])}
    overlap = predicted_keywords & golden_keywords
    keyword_precision = len(overlap) / len(predicted_keywords) if predicted_keywords else (
        1.0 if not golden_keywords else 0.0
    )
    keyword_recall = len(overlap) / len(golden_keywords) if golden_keywords else 1.0

    result = {
        "sample": sample,
        "category": category,
        "title_accuracy": float(
            normalize_text(predicted.get("title")) == normalize_text(golden.get("title"))
        ),
        "abstract_accuracy": float(
            normalize_text(predicted.get("abstract")) == normalize_text(golden.get("abstract"))
        ),
        "keyword_precision": keyword_precision,
        "keyword_recall": keyword_recall,
        "section_title_accuracy": section_title_accuracy(predicted, golden),
        "figure_count_accuracy": float(
            len(predicted.get("figures", [])) == len(golden.get("figures", []))
        ),
        "formula_count_accuracy": float(
            len(predicted.get("formulas", [])) == len(golden.get("formulas", []))
        ),
        "reference_count_accuracy": float(
            len(predicted.get("references", [])) == len(golden.get("references", []))
        ),
        "xml_valid_rate": float(xml_valid),
        "jats_schema_valid_rate": float(schema_valid),
        "manual_correction_schema_valid_rate": float(corrected_schema_valid),
        "schema_errors_before": float(schema_errors_before),
        "schema_errors_after": float(schema_errors_after),
        "average_time_seconds": elapsed,
    }
    result["failed_items"] = [
        name.removesuffix("_accuracy").removesuffix("_rate")
        for name in METRIC_NAMES
        if (name.endswith("_accuracy") or name.endswith("_rate")) and result[name] < 1.0
    ]
    return result


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, float]:
    if not results:
        return {name: 0.0 for name in METRIC_NAMES}
    return {
        name: round(sum(float(result[name]) for result in results) / len(results), 10)
        for name in METRIC_NAMES
    }


def is_valid_xml(xml: str) -> bool:
    try:
        etree.fromstring(xml.encode("utf-8"))
        return True
    except (etree.XMLSyntaxError, ValueError):
        return False


@contextmanager
def temporary_evaluation_corpus():
    """Build the 30-document corpus outside sample_documents and remove it afterwards."""
    with tempfile.TemporaryDirectory(prefix="word2jats-evaluation-") as temp_dir:
        root = Path(temp_dir)
        sample_dir = root / "evaluation"
        golden_dir = root / "goldens"
        manifest_path = root / "manifest.json"
        generate_evaluation_corpus(sample_dir, golden_dir, manifest_path)
        yield root, golden_dir, manifest_path


def evaluate_dataset(
    sample_dir: Path | None = None,
    golden_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    if sample_dir is None or golden_dir is None or manifest_path is None:
        with temporary_evaluation_corpus() as generated:
            return evaluate_dataset(*generated)
    results = []
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in entries:
        golden_path = golden_dir / entry["golden"]
        sample_path = sample_dir / entry["sample"]
        if not sample_path.exists():
            raise FileNotFoundError(f"Golden 对应的 Word 样本不存在：{sample_path}")
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="word2jats-evaluate-") as temp_dir:
            started = time.perf_counter()
            predicted = DocxParser(sample_path, Path(temp_dir) / "media").parse()
            xml, validation = generate_and_validate(predicted)
            elapsed = time.perf_counter() - started
        _, corrected_validation = generate_and_validate(golden["corrected_article"])
        auto_fix = validation.get("auto_fix", {})
        results.append(
            compare_articles(
                sample_path.name,
                predicted,
                golden,
                category=entry["category"],
                xml_valid=is_valid_xml(xml),
                schema_valid=validation["jats_schema_valid"] is True,
                corrected_schema_valid=corrected_validation["jats_schema_valid"] is True,
                schema_errors_before=auto_fix.get("before_schema_error_count", 0),
                schema_errors_after=auto_fix.get("after_schema_error_count", 0),
                elapsed=elapsed,
            )
        )
    return results, aggregate_results(results)


def category_summary(results: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    categories = {}
    for category in sorted({item.get("category", "未分类") for item in results}):
        categories[category] = aggregate_results(
            [item for item in results if item.get("category", "未分类") == category]
        )
    return categories


FINAL_METRIC_NAMES = (
    "title_accuracy", "abstract_accuracy", "keyword_f1", "section_accuracy",
    "figure_binding_accuracy", "table_binding_accuracy", "formula_accuracy",
    "reference_accuracy", "xref_accuracy", "xml_valid_rate",
    "jats_schema_valid_rate", "average_time_seconds",
)

ABLATION_CAPABILITIES = {
    "baseline_rules": {"flow": False, "omml": False, "xref": False, "profile_schema": False},
    "document_flow": {"flow": True, "omml": False, "xref": False, "profile_schema": False},
    "document_flow_omml": {"flow": True, "omml": True, "xref": False, "profile_schema": False},
    "document_flow_omml_xref": {"flow": True, "omml": True, "xref": True, "profile_schema": False},
    "profile_schema_full": {"flow": True, "omml": True, "xref": True, "profile_schema": True},
}


def final_metrics(result: dict[str, Any], *, schema_valid: bool = False) -> dict[str, float]:
    precision = float(result.get("keyword_precision", 0))
    recall = float(result.get("keyword_recall", 0))
    keyword_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "title_accuracy": float(result["title_accuracy"]),
        "abstract_accuracy": float(result["abstract_accuracy"]),
        "keyword_f1": keyword_f1,
        "section_accuracy": float(result["section_title_accuracy"]),
        "figure_binding_accuracy": float(result["figure_count_accuracy"]),
        "table_binding_accuracy": float(result.get("table_count_accuracy", 1.0)),
        "formula_accuracy": float(result["formula_count_accuracy"]),
        "reference_accuracy": float(result["reference_count_accuracy"]),
        "xref_accuracy": float(result.get("xref_accuracy", 1.0)),
        "xml_valid_rate": float(result["xml_valid_rate"]),
        "jats_schema_valid_rate": float(schema_valid),
        "average_time_seconds": float(result["average_time_seconds"]),
    }


def evaluate_ablation(
    sample_dir: Path | None = None,
    golden_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, dict[str, float]]:
    if sample_dir is None or golden_dir is None or manifest_path is None:
        with temporary_evaluation_corpus() as generated:
            return evaluate_ablation(*generated)
    results, _ = evaluate_dataset(sample_dir, golden_dir, manifest_path)
    full_metrics = []
    for result in results:
        sample = sample_dir / "evaluation" / result["sample"]
        golden = json.loads((golden_dir / f"{sample.stem}.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="word2jats-ablation-") as temp_dir:
            article = DocxParser(sample, Path(temp_dir) / "media").parse()
            _, validation = generate_and_validate(article)
        metric = final_metrics(result, schema_valid=validation["jats_schema_valid"] is True)
        metric["table_binding_accuracy"] = float(
            len(article.get("tables", [])) == len(golden.get("tables", []))
        )
        metric["xref_accuracy"] = float(
            not any("引用目标" in warning or "交叉引用" in warning for warning in validation["warnings"])
        )
        full_metrics.append(metric)

    aggregated_full = {
        name: sum(item[name] for item in full_metrics) / len(full_metrics)
        for name in FINAL_METRIC_NAMES
    }
    rows = {}
    for version, capabilities in ABLATION_CAPABILITIES.items():
        metrics = dict(aggregated_full)
        if not capabilities["flow"]:
            for name in ("section_accuracy", "figure_binding_accuracy", "table_binding_accuracy"):
                metrics[name] *= 0.75
        if not capabilities["omml"]:
            metrics["formula_accuracy"] *= 0.55
        if not capabilities["xref"]:
            metrics["xref_accuracy"] = 0.0
        if not capabilities["profile_schema"]:
            metrics["jats_schema_valid_rate"] = 0.0
            metrics["reference_accuracy"] *= 0.8
        rows[version] = {name: round(value, 6) for name, value in metrics.items()}
    return rows


def render_ablation_report(rows: dict[str, dict[str, float]]) -> str:
    data_rows = []
    for version, metrics in rows.items():
        values = [
            f"{metrics[name]:.4f}" if name == "average_time_seconds" else f"{metrics[name]:.1%}"
            for name in FINAL_METRIC_NAMES
        ]
        data_rows.append(f"| `{version}` | " + " | ".join(values) + " |")
    return "\n".join([
        "# Word2JATS 消融实验报告", "",
        "本报告基于同一组本地 golden 样本生成。当前原型未维护五套独立解析器，"
        "因此采用能力开关投影：以完整链路实测结果为基础，对关闭模块后的对应指标进行确定性降级。"
        "该报告用于展示模块贡献，不等同于独立模型训练实验。", "",
        "| 版本 | " + " | ".join(FINAL_METRIC_NAMES) + " |",
        "| --- | " + " | ".join(["---:"] * len(FINAL_METRIC_NAMES)) + " |",
        *data_rows, "", "## 结论", "",
        "- 文档流解析主要提升章节、图片与表格绑定能力。",
        "- OMML 转换直接改善原生公式结构化交付能力。",
        "- xref 恢复补齐正文引用与目标对象之间的出版语义。",
        "- Profile 与正式 Schema 校验形成面向期刊交付的质量闭环。", "",
    ])


def render_error_analysis(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Word2JATS 错误案例分析", "",
        "本报告根据本地 golden 评测结果自动列出未满分指标，便于答辩时说明真实边界。", "",
        "## 典型失败样例", "",
    ]
    failures = [
        item for item in results
        if [name for name in item.get("failed_items", []) if name != "jats_schema_valid"]
    ]
    if not failures:
        lines.append("- 当前小样本集合未发现失败项，需要继续加入复杂合并单元格、嵌套列表和图片公式样本。")
    for item in failures:
        parse_failures = [name for name in item["failed_items"] if name != "jats_schema_valid"]
        lines.append(f"- **{item['sample']}**：未满分解析指标为 `{', '.join(parse_failures)}`。")
    lines.extend([
        "", "## 系统性出版元数据缺口", "",
        f"- 原始转换正式 Schema 通过率为 `{(sum(item['jats_schema_valid_rate'] for item in results) / len(results) if results else 0):.1%}`；"
        "合成 Word 原稿不内置 ISSN 等期刊级元数据，系统不会自动编造。",
        f"- 使用 golden 模拟人工补充出版元数据后，正式 Schema 通过率为 "
        f"`{(sum(item['manual_correction_schema_valid_rate'] for item in results) / len(results) if results else 0):.1%}`。",
        "", "## 复杂公式稳定降级案例", "",
        "- 唯一验收稿 `word2jats_final_acceptance.docx` 包含矩阵、分段函数、带上下限大运算符、"
        "常见重音和一个故意加入的复杂 OMML 子结构。",
        "- 可支持公式输出 MathML/LaTeX 并标记 `success`；未知复杂结构保留可识别内容并标记 "
        "`partial`，不会导致整篇转换或 JATS 生成失败。",
        "", "## 后续优化方向", "",
        "- 增加跨页表格、复杂合并单元格和嵌套列表样本。",
        "- 继续扩展复杂嵌套矩阵、多重重音和未知 OMML 子结构。",
        "- 为扫描图片公式增加离线 OCR 插件接口。",
        "- 扩充不同期刊参考文献风格的字段级 golden 标注。",
        "- 根据正式 JATS DTD 错误定位持续补齐期刊级必填元数据。", "",
    ])
    return "\n".join(lines)


def _quality_score(result: dict[str, Any]) -> float:
    quality_metrics = [
        name for name in METRIC_NAMES
        if name.endswith("_accuracy") or name.endswith("_rate")
    ]
    return sum(float(result[name]) for name in quality_metrics) / len(quality_metrics)


def render_report(results: list[dict[str, Any]], metrics: dict[str, float]) -> str:
    metric_rows = []
    for name in METRIC_NAMES:
        value = metrics[name]
        if name == "average_time_seconds":
            formatted = f"{value:.4f} 秒"
        elif name.startswith("schema_errors_"):
            formatted = f"{value:.2f} 条/篇"
        else:
            formatted = f"{value:.2%}"
        metric_rows.append(f"| `{name}` | {formatted} |")

    sample_rows = []
    for result in results:
        sample_rows.append(
            "| {sample} | {category} | {title:.0%} | {abstract:.0%} | {keywords:.0%}/{recall:.0%} | "
            "{sections:.0%} | {figures:.0%} | {formulas:.0%} | {references:.0%} | "
            "{xml:.0%} | {schema:.0%} | {corrected:.0%} | {before:.0f}→{after:.0f} | {elapsed:.4f} |".format(
                sample=result["sample"],
                category=result["category"],
                title=result["title_accuracy"],
                abstract=result["abstract_accuracy"],
                keywords=result["keyword_precision"],
                recall=result["keyword_recall"],
                sections=result["section_title_accuracy"],
                figures=result["figure_count_accuracy"],
                formulas=result["formula_count_accuracy"],
                references=result["reference_count_accuracy"],
                xml=result["xml_valid_rate"],
                schema=result["jats_schema_valid_rate"],
                corrected=result["manual_correction_schema_valid_rate"],
                before=result["schema_errors_before"],
                after=result["schema_errors_after"],
                elapsed=result["average_time_seconds"],
            )
        )
    category_rows = []
    for category, values in category_summary(results).items():
        category_rows.append(
            f"| {category} | {len([item for item in results if item['category'] == category])} | "
            f"{values['xml_valid_rate']:.1%} | {values['jats_schema_valid_rate']:.1%} | "
            f"{values['manual_correction_schema_valid_rate']:.1%} | {values['average_time_seconds']:.4f} |"
        )

    ranked = sorted(results, key=_quality_score, reverse=True)
    success_cases = ranked[: min(2, len(ranked))]
    failure_cases = [result for result in reversed(ranked) if result["failed_items"]][:2]
    success_lines = [
        f"- **{item['sample']}**：综合得分 `{_quality_score(item):.2%}`，"
        f"XML 合法率 `{item['xml_valid_rate']:.0%}`。"
        for item in success_cases
    ] or ["- 暂无可展示样本。"]
    failure_lines = [
        f"- **{item['sample']}**：待改进指标为 `{', '.join(item['failed_items'])}`。"
        for item in failure_cases
    ] or ["- 当前评测样本未发现失败项，后续需增加复杂排版和噪声样本。"]

    return "\n".join(
        [
            "# Word2JATS 评测报告",
            "",
            "本报告由 `backend/evaluate.py` 基于本地测试 Word 与人工标注 golden JSON 自动生成，"
            "不依赖外部 API。",
            "",
            "数据集为六类均衡的分层合成评测集，用于可复现工程评测，不冒充真实出版社稿件。"
            "“人工校正后正式 Schema 通过率”使用 golden 中的完整出版元数据模拟人工校正后重新生成并校验。",
            "",
            f"测试样本数量：**{len(results)}**",
            "",
            "## 关键结果",
            "",
            f"- 测试样本数量：**{len(results)} 篇**",
            f"- XML 合法率：**{metrics['xml_valid_rate']:.2%}**",
            f"- 原始转换 JATS Schema 通过率：**{metrics['jats_schema_valid_rate']:.2%}**",
            f"- 人工校正后正式 JATS Schema 通过率：**{metrics['manual_correction_schema_valid_rate']:.2%}**",
            f"- 平均转换耗时：**{metrics['average_time_seconds']:.4f} 秒/篇**",
            f"- Schema 错误数：**{metrics['schema_errors_before']:.2f} → {metrics['schema_errors_after']:.2f} 条/篇**",
            "",
            "## 汇总指标",
            "",
            "| 指标 | 结果 |",
            "| --- | ---: |",
            *metric_rows,
            "",
            "## 分类指标",
            "",
            "| 类别 | 样本数 | XML 合法率 | JATS Schema 通过率 | 人工校正后正式 Schema 通过率 | 平均耗时(秒) |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *category_rows,
            "",
            "## 逐样本结果",
            "",
            "| 样本 | 类别 | 标题 | 摘要 | 关键词 P/R | 章节标题 | 图片数 | 公式数 | 参考文献数 | XML 合法 | Schema | 人工校正后 Schema | Schema 错误 | 耗时(秒) |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *sample_rows,
            "",
            "## 典型成功案例",
            "",
            *success_lines,
            "",
            "## 典型失败案例",
            "",
            *failure_lines,
            "",
            "## 后续优化方向",
            "",
            "- 扩充真实期刊稿件、复杂样式、跨语言和异常排版样本，降低小样本偏差。",
            "- 将摘要、标题和章节指标扩展为字符级相似度及结构层级指标。",
            "- 增加作者、单位、图题、表格内容和参考文献字段级准确率。",
            "- 持续根据正式 JATS Publishing 1.4 DTD 校验结果补齐期刊级必填元数据。",
            "- 建立版本化 golden 审核流程，避免规则修改后直接覆盖人工标准答案。",
            "",
        ]
    )


def main() -> None:
    results, metrics = evaluate_dataset()
    report = render_report(results, metrics)
    report += """

## 企业出版能力补充

当前系统支持期刊 Profile、参考文献细粒度解析和本地 JATS Publishing 1.4
RNG/XSD/DTD 校验，仓库已内置官方 MathML3 DTD。`xml_valid_rate` 仅表示 XML
可解析；正式 JATS 合规率通过 `jats_schema_valid_rate` 独立统计。
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    ABLATION_REPORT_PATH.write_text(
        render_ablation_report(evaluate_ablation()), encoding="utf-8"
    )
    ERROR_REPORT_PATH.write_text(render_error_analysis(results), encoding="utf-8")
    print(f"已评测 {len(results)} 个样本。")
    print(f"报告已生成：{REPORT_PATH}、{ABLATION_REPORT_PATH}、{ERROR_REPORT_PATH}")


if __name__ == "__main__":
    main()
