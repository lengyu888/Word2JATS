from pathlib import Path
from typing import Any

from app.services.xref_resolver import XrefResolver


class VisualPreviewBuilder:
    """Enrich figures and tables with presentation and quality metadata."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    STATUS_PRIORITY = {"ok": 0, "need_review": 1, "warning": 2, "error": 3}

    def __init__(self):
        self.xref_resolver = XrefResolver()

    def enrich(
        self, article: dict[str, Any], conversion_id: str, quality_report: dict[str, Any]
    ) -> dict[str, Any]:
        references = self._reverse_xrefs(article)
        issues = quality_report.get("issues", [])
        for figure in article.get("figures", []):
            self._enrich_figure(figure, article, conversion_id, references, issues)
        for table in article.get("tables", []):
            self._enrich_table(table, article, references, issues)
        return article

    def _enrich_figure(
        self,
        figure: dict[str, Any],
        article: dict[str, Any],
        conversion_id: str,
        references: dict[str, list[str]],
        quality_issues: list[dict[str, Any]],
    ) -> None:
        path = Path(figure.get("path", ""))
        filename = figure.get("filename") or (path.name if figure.get("path") else "")
        figure["filename"] = filename
        if conversion_id and filename and path.suffix.lower() in self.IMAGE_EXTENSIONS:
            figure["media_url"] = f"/api/media/{conversion_id}/{filename}"
        else:
            figure.setdefault("media_url", "")
        self._common(figure, article, references, quality_issues)
        if not figure.get("caption"):
            self._add_issue(figure, "warning", "图片缺少图题", "在人工校正页面补充图题")
        if not figure.get("path"):
            self._add_issue(figure, "warning", "图片文件缺失", "检查 Word 内嵌图片或重新上传文档")
        elif not figure.get("media_url"):
            self._add_issue(figure, "need_review", "图片格式暂不支持在线预览", "通过 ZIP 结果包检查原始媒体文件")

    def _enrich_table(
        self,
        table: dict[str, Any],
        article: dict[str, Any],
        references: dict[str, list[str]],
        quality_issues: list[dict[str, Any]],
    ) -> None:
        rows = table.get("rows", [])
        table["row_count"] = len(rows)
        table["column_count"] = max((len(row) for row in rows), default=0)
        self._common(table, article, references, quality_issues)
        if not table.get("caption"):
            self._add_issue(table, "warning", "表格缺少表题", "在人工校正页面补充表题")
        if not rows:
            self._add_issue(table, "warning", "表格没有数据行", "检查 Word 表格或在人工校正页面补充 rows")

    def _common(
        self,
        item: dict[str, Any],
        article: dict[str, Any],
        references: dict[str, list[str]],
        quality_issues: list[dict[str, Any]],
    ) -> None:
        section_index = item.get("section_index", -1)
        sections = article.get("sections", [])
        item["section_id"] = f"sec{section_index + 1}" if 0 <= section_index < len(sections) else ""
        item["section_title"] = (
            sections[section_index].get("title", "") if 0 <= section_index < len(sections) else ""
        )
        item["referenced_by"] = references.get(item.get("id", ""), [])
        item["status"] = "ok"
        item["issues"] = []
        for issue in quality_issues:
            if item.get("id") and item["id"] in str(issue.get("location", "")):
                self._add_issue(
                    item,
                    issue.get("level", "need_review"),
                    issue.get("message", ""),
                    issue.get("suggestion", ""),
                )

    def _reverse_xrefs(self, article: dict[str, Any]) -> dict[str, list[str]]:
        referenced_by: dict[str, list[str]] = {}
        for section_index, section in enumerate(article.get("sections", []), start=1):
            for paragraph_index, paragraph in enumerate(section.get("paragraphs", []), start=1):
                for xref_index, match in enumerate(self.xref_resolver.resolve(paragraph), start=1):
                    if match["ref_type"] not in {"fig", "table"}:
                        continue
                    source = f"sec{section_index}-p{paragraph_index}-xref{xref_index}"
                    for rid in match["rid"].split():
                        referenced_by.setdefault(rid, []).append(source)
        return referenced_by

    def _add_issue(
        self, item: dict[str, Any], level: str, message: str, suggestion: str
    ) -> None:
        normalized_level = level if level in self.STATUS_PRIORITY else "need_review"
        issue = {
            "level": normalized_level,
            "message": message,
            "suggestion": suggestion,
        }
        if issue not in item["issues"]:
            item["issues"].append(issue)
        if self.STATUS_PRIORITY[normalized_level] > self.STATUS_PRIORITY[item["status"]]:
            item["status"] = normalized_level
