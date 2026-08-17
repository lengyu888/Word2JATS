from __future__ import annotations

from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory
from typing import Any, Iterable

from app.services.docx_parser import DocxParser
from app.services.jats_auto_fixer import JatsAutoFixer
from app.services.jats_generator import JatsGenerator
from app.services.official_xml_comparator import OfficialXmlComparator
from app.services.profile_loader import ProfileLoader
from app.services.validator import ArticleValidator


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "sample_count": 0,
            "average_similarity": 0.0,
            "minimum_similarity": 0,
            "schema_valid_rate": 0.0,
        }
    scores = [int(item.get("similarity_score", 0)) for item in results]
    schema_passes = sum(bool(item.get("schema_valid")) for item in results)
    return {
        "sample_count": len(results),
        "average_similarity": round(mean(scores), 1),
        "minimum_similarity": min(scores),
        "schema_valid_rate": round(schema_passes / len(results), 4),
    }


def acceptance_passed(
    summary: dict[str, Any], *, average_floor: float, minimum_floor: int,
    schema_floor: float
) -> bool:
    return bool(
        summary.get("average_similarity", 0) >= average_floor
        and summary.get("minimum_similarity", 0) >= minimum_floor
        and summary.get("schema_valid_rate", 0) >= schema_floor
    )


class OfficialSampleEvaluator:
    """Run the production conversion pipeline against local official pairs."""

    def __init__(self, profile_name: str = "default"):
        self.profile_name = profile_name
        self.profile_loader = ProfileLoader()
        self.comparator = OfficialXmlComparator()

    def evaluate(
        self, samples: Iterable[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        results = [self._evaluate_one(sample) for sample in samples]
        return results, aggregate_results(results)

    def _evaluate_one(self, sample: dict[str, Any]) -> dict[str, Any]:
        docx_path = Path(sample["docx"])
        official_xml = Path(sample["xml"])
        profile = self.profile_loader.load(self.profile_name)
        with TemporaryDirectory(prefix="word2jats-official-") as temp_dir:
            article = DocxParser(docx_path, Path(temp_dir) / "media", profile).parse()
            xml = JatsGenerator(profile).generate(article)
            validator = ArticleValidator()
            initial_schema = validator.schema_validator.validate(xml)
            xml, auto_fix, schema = JatsAutoFixer(validator.schema_validator).fix(
                xml, initial_schema
            )
            validation = validator.validate(
                article, xml, schema_result=schema, auto_fix=auto_fix
            )
            comparison = self.comparator.compare(xml, official_xml)
        return {
            "filename": sample.get("filename", docx_path.name),
            "label": sample.get("label", docx_path.stem),
            "metric_version": comparison.get("metric_version", "2.0"),
            "similarity_score": comparison["similarity_score"],
            "schema_valid": validation["jats_schema_valid"],
            "xml_well_formed": validation["xml_well_formed"],
            "dimensions": comparison.get("dimensions", {}),
            "recoverable_differences": comparison.get("recoverable_differences", []),
            "publisher_enriched_differences": comparison.get(
                "publisher_enriched_differences", []
            ),
            "facts": comparison.get("facts", {}),
        }

    @staticmethod
    def write_markdown(
        output_path: str | Path,
        results: list[dict[str, Any]],
        summary: dict[str, Any],
        *,
        title: str = "官方样例对比报告",
        command: str = "python evaluate_official_samples.py",
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# {title}",
            "",
            f"> 本报告由 `{command}` 基于本地 DOCX/XML 配对自动生成。指标 V2 按 JATS 语义维度评价，不使用全局标签数量充当质量分。",
            "",
            "## 汇总",
            "",
            f"- 测试样例：{summary['sample_count']} 篇",
            f"- 平均语义相似度：{summary['average_similarity']}%",
            f"- 最低单篇相似度：{summary['minimum_similarity']}%",
            f"- JATS 1.3 DTD 通过率：{summary['schema_valid_rate'] * 100:.1f}%",
            "",
            "## 分样例结果",
            "",
            "| 样例 | 总分 | DTD | 元数据 | 章节 | 图表 | 公式 | 参考文献 | xref |",
            "|---|---:|:---:|---:|---:|---:|---:|---:|---:|",
        ]
        for item in results:
            dimensions = item.get("dimensions", {})

            def score(name: str) -> int:
                return dimensions.get(name, {}).get("score", 0)

            lines.append(
                f"| {item['filename']} | {item['similarity_score']} | "
                f"{'通过' if item['schema_valid'] else '失败'} | {score('metadata')} | "
                f"{score('structure')} | {score('figures_tables')} | {score('formulas')} | "
                f"{score('references')} | {score('xrefs')} |"
            )
        lines.extend(["", "## 主要可恢复差异", ""])
        for item in results:
            lines.append(f"### {item['filename']}")
            differences = item.get("recoverable_differences", [])
            if not differences:
                lines.append("- 未发现可恢复差异。")
            else:
                for difference in differences[:12]:
                    lines.append(
                        f"- `{difference['metric']}`：{difference['message']} "
                        f"建议：{difference['suggestion']}"
                    )
            enriched = item.get("publisher_enriched_differences", [])
            if enriched:
                lines.append(
                    "- 出版方补录字段："
                    + "、".join(difference["metric"] for difference in enriched)
                )
            lines.append("")
        output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return output
