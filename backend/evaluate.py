"""Batch evaluation for Word2JATS sample documents.

Run from the backend directory:
    python evaluate.py
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from lxml import etree

from app.services.docx_parser import DocxParser
from app.services.jats_generator import JatsGenerator


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
SAMPLE_DIR = PROJECT_DIR / "sample_documents"
GOLDEN_DIR = BACKEND_DIR / "evaluation" / "goldens"
REPORT_PATH = PROJECT_DIR / "docs" / "评测报告.md"

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
    xml_valid: bool,
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
        "average_time_seconds": elapsed,
    }
    result["failed_items"] = [
        name.removesuffix("_accuracy").removesuffix("_rate")
        for name in METRIC_NAMES
        if name != "average_time_seconds" and result[name] < 1.0
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


def evaluate_dataset(
    sample_dir: Path = SAMPLE_DIR, golden_dir: Path = GOLDEN_DIR
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    results = []
    for golden_path in sorted(golden_dir.glob("*.json")):
        sample_path = sample_dir / f"{golden_path.stem}.docx"
        if not sample_path.exists():
            raise FileNotFoundError(f"Golden 对应的 Word 样本不存在：{sample_path}")
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="word2jats-evaluate-") as temp_dir:
            started = time.perf_counter()
            predicted = DocxParser(sample_path, Path(temp_dir) / "media").parse()
            xml = JatsGenerator().generate(predicted)
            elapsed = time.perf_counter() - started
        results.append(
            compare_articles(
                sample_path.name,
                predicted,
                golden,
                xml_valid=is_valid_xml(xml),
                elapsed=elapsed,
            )
        )
    return results, aggregate_results(results)


def _quality_score(result: dict[str, Any]) -> float:
    quality_metrics = [name for name in METRIC_NAMES if name != "average_time_seconds"]
    return sum(float(result[name]) for name in quality_metrics) / len(quality_metrics)


def render_report(results: list[dict[str, Any]], metrics: dict[str, float]) -> str:
    metric_rows = []
    for name in METRIC_NAMES:
        value = metrics[name]
        formatted = f"{value:.4f} 秒" if name == "average_time_seconds" else f"{value:.2%}"
        metric_rows.append(f"| `{name}` | {formatted} |")

    sample_rows = []
    for result in results:
        sample_rows.append(
            "| {sample} | {title:.0%} | {abstract:.0%} | {keywords:.0%}/{recall:.0%} | "
            "{sections:.0%} | {figures:.0%} | {formulas:.0%} | {references:.0%} | "
            "{xml:.0%} | {elapsed:.4f} |".format(
                sample=result["sample"],
                title=result["title_accuracy"],
                abstract=result["abstract_accuracy"],
                keywords=result["keyword_precision"],
                recall=result["keyword_recall"],
                sections=result["section_title_accuracy"],
                figures=result["figure_count_accuracy"],
                formulas=result["formula_count_accuracy"],
                references=result["reference_count_accuracy"],
                xml=result["xml_valid_rate"],
                elapsed=result["average_time_seconds"],
            )
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
            f"测试样本数量：**{len(results)}**",
            "",
            "## 汇总指标",
            "",
            "| 指标 | 结果 |",
            "| --- | ---: |",
            *metric_rows,
            "",
            "## 逐样本结果",
            "",
            "| 样本 | 标题 | 摘要 | 关键词 P/R | 章节标题 | 图片数 | 公式数 | 参考文献数 | XML 合法 | 耗时(秒) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
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
            "- 接入正式 JATS Publishing DTD/XSD 校验，并区分 XML 合法性与 JATS 合规性。",
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
RNG/XSD/DTD 校验。`xml_valid_rate` 仅表示 XML 可解析；正式 JATS 合规率需要
在 `backend/schemas/` 配置官方 Schema 后作为独立指标统计。
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"已评测 {len(results)} 个样本。")
    print(f"报告已生成：{REPORT_PATH}")


if __name__ == "__main__":
    main()
