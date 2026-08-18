import re
from pathlib import Path
from typing import Any


class FlowViewBuilder:
    """Build a presentation-friendly DOCX flow to JATS mapping."""

    XREF_RE = re.compile(
        r"(?:图\s*\d+|fig(?:ure)?\.?\s*\d+|表\s*\d+|table\s*\d+|"
        r"(?:式|公式)\s*[（(]\d+[）)]|eq\.?\s*[（(]\d+[）)]|\[\s*\d+(?:\s*[-,]\s*\d+)*\s*\])",
        re.I,
    )
    ABSTRACT_RE = re.compile(r"^\s*(?:摘要|摘\s*要|abstract)\s*[:：]?\s*", re.I)
    KEYWORD_RE = re.compile(r"^\s*(?:关键词|关\s*键\s*词|key\s*words?|keywords)\s*[:：]?\s*", re.I)
    REFERENCE_RE = re.compile(r"^\s*(?:参考\s*文献|references?)\s*[:：]?\s*$", re.I)
    STATUS_PRIORITY = {"ok": 0, "need_review": 1, "warning": 2, "error": 3}

    def build(
        self,
        article: dict[str, Any],
        document_flow_nodes: list[dict[str, Any]] | None,
        validation: dict[str, Any] | None,
        quality_report: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        nodes = document_flow_nodes or self._nodes_from_article(article)
        view = self._map_nodes(article, nodes)
        self._attach_issues(view, validation or {}, quality_report or {})
        for index, item in enumerate(view, start=1):
            item["index"] = index
        return view

    def _map_nodes(
        self, article: dict[str, Any], nodes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        view = []
        counters = {"heading": 0, "figure": 0, "figure_caption": 0, "table": 0,
                    "table_caption": 0, "formula": 0, "list": 0, "reference": 0}
        current_section = -1
        in_references = False
        authors = {item.get("name", "") for item in article.get("authors", [])}
        affiliations = set(article.get("affiliations", []))

        for node in nodes:
            raw_type = node.get("type", "unknown")
            text = str(node.get("text", "") or "").strip()
            node_type = "formula" if raw_type == "formula_image" else raw_type
            target_id = None

            if text == article.get("title") or raw_type == "title":
                node_type = "title"
            elif text in authors:
                node_type = "author"
            elif authors and all(name in text for name in authors):
                node_type = "author"
            elif text in affiliations:
                node_type = "affiliation"
            elif self.ABSTRACT_RE.match(text):
                node_type = "abstract"
            elif self.KEYWORD_RE.match(text):
                node_type = "keyword"
            elif self.REFERENCE_RE.match(text):
                node_type = "unknown"
                in_references = True
            elif in_references and text:
                node_type = "reference"
            elif raw_type == "heading":
                current_section = counters["heading"]
                counters["heading"] += 1
                target_id = f"sec{current_section + 1}"
            elif raw_type == "image":
                node_type = "figure"
            elif raw_type == "paragraph" and self.XREF_RE.search(text):
                node_type = "xref_paragraph"

            if node.get("section_index") is not None:
                current_section = int(node["section_index"])
            if node_type in {"figure", "figure_caption", "table", "table_caption",
                             "formula", "list", "reference"}:
                key = node_type
                number = counters[key] + 1
                counters[key] = number
                prefix = {
                    "figure": "fig", "figure_caption": "fig", "table": "tab",
                    "table_caption": "tab", "formula": "eq", "list": "list",
                    "reference": "ref",
                }[key]
                target_id = node.get("target_id") or f"{prefix}{number}"

            section_id = f"sec{current_section + 1}" if current_section >= 0 else ""
            section_title = self._section_title(article, current_section)
            mapping = self._mapping(node_type, target_id, section_id)
            if node_type == "formula":
                formula_tag = "alternatives/mml:math" if node.get("mathml") else "tex-math"
                mapping = {
                    "path": f"{mapping['path']}/{formula_tag}",
                    "tag": f"disp-formula/{formula_tag}",
                }
            status = "need_review" if node_type == "unknown" else "ok"
            confidence = 0.35 if node_type == "unknown" else (
                0.98 if node_type in {"title", "author", "affiliation", "abstract", "keyword"} else 0.88
            )
            view.append({
                "index": 0,
                "node_type": node_type,
                "text": text or self._node_summary(node),
                "preview": self._preview(text or self._node_summary(node)),
                "section_id": section_id,
                "section_title": section_title,
                "jats_path": mapping["path"],
                "jats_tag": mapping["tag"],
                "target_id": target_id,
                "confidence": confidence,
                "status": status,
                "issues": [],
                "source": {
                    "paragraph_index": node.get("paragraph_index"),
                    "table_index": node.get("table_index"),
                    "media_name": Path(node.get("media_path", "")).name or None,
                },
            })
        return view

    def _nodes_from_article(self, article: dict[str, Any]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = [{"type": "title", "text": article.get("title", "")}]
        nodes.extend({"type": "author", "text": item.get("name", "")} for item in article.get("authors", []))
        nodes.extend({"type": "affiliation", "text": item} for item in article.get("affiliations", []))
        nodes.append({"type": "abstract", "text": article.get("abstract", "")})
        nodes.extend({"type": "keyword", "text": item} for item in article.get("keywords", []))
        for section_index, section in enumerate(article.get("sections", [])):
            nodes.append({"type": "heading", "text": section.get("title", ""), "section_index": section_index})
            nodes.extend(
                {"type": "xref_paragraph" if self.XREF_RE.search(text) else "paragraph",
                 "text": text, "section_index": section_index}
                for text in section.get("paragraphs", [])
            )
        for kind in ("figures", "tables", "formulas", "lists"):
            raw_type = {"figures": "figure", "tables": "table", "formulas": "formula", "lists": "list"}[kind]
            for item in article.get(kind, []):
                nodes.append({
                    "type": raw_type, "text": self._article_item_text(raw_type, item),
                    "section_index": item.get("section_index"), "target_id": item.get("id"),
                    "mathml": item.get("mathml", ""), "latex": item.get("latex", ""),
                })
                if raw_type in {"figure", "table"}:
                    nodes.append({
                        "type": f"{raw_type}_caption", "text": item.get("caption", ""),
                        "section_index": item.get("section_index"), "target_id": item.get("id"),
                    })
        nodes.extend(
            {"type": "reference", "text": item.get("raw", ""), "target_id": item.get("id")}
            for item in article.get("references", [])
        )
        return nodes

    @staticmethod
    def _article_item_text(node_type: str, item: dict[str, Any]) -> str:
        if node_type == "formula":
            return item.get("content") or item.get("latex") or "MathML formula"
        if node_type == "list":
            return "；".join(item.get("items", []))
        if node_type == "table":
            rows = item.get("rows", [])
            return f"{len(rows)} 行表格"
        return item.get("path") or "内嵌图片"

    @staticmethod
    def _node_summary(node: dict[str, Any]) -> str:
        if node.get("type") == "table":
            return f"{len(node.get('rows', []))} 行表格"
        if node.get("type") == "image":
            return Path(node.get("media_path", "")).name or "内嵌图片"
        return ""

    @staticmethod
    def _preview(text: str) -> str:
        return text if len(text) <= 120 else f"{text[:117]}..."

    @staticmethod
    def _section_title(article: dict[str, Any], index: int) -> str:
        sections = article.get("sections", [])
        return sections[index].get("title", "") if 0 <= index < len(sections) else ""

    @staticmethod
    def _mapping(node_type: str, target_id: str | None, section_id: str) -> dict[str, str]:
        body = f"article/body/sec[@id='{section_id}']" if section_id else "article/body"
        mappings = {
            "title": ("article/front/article-meta/title-group/article-title", "article-title"),
            "author": ("article/front/article-meta/contrib-group/contrib", "contrib"),
            "affiliation": ("article/front/article-meta/aff", "aff"),
            "abstract": ("article/front/article-meta/abstract/p", "abstract/p"),
            "keyword": ("article/front/article-meta/kwd-group/kwd", "kwd"),
            "heading": (f"{body}/title", "sec/title"),
            "paragraph": (f"{body}/p", "p"),
            "xref_paragraph": (f"{body}/p/xref", "p + xref"),
            "figure": (f"{body}/fig[@id='{target_id}']/graphic", "fig/graphic"),
            "figure_caption": (f"{body}/fig[@id='{target_id}']/caption/p", "fig/caption/p"),
            "table": (f"{body}/table-wrap[@id='{target_id}']/table", "table-wrap/table"),
            "table_caption": (f"{body}/table-wrap[@id='{target_id}']/caption/p", "table-wrap/caption/p"),
            "formula": (f"{body}/disp-formula[@id='{target_id}']", "disp-formula"),
            "list": (f"{body}/list[@id='{target_id}']/list-item", "list/list-item"),
            "reference": (f"article/back/ref-list/ref[@id='{target_id}']", "ref-list/ref"),
            "unknown": ("", "unknown"),
        }
        path, tag = mappings.get(node_type, mappings["unknown"])
        return {"path": path, "tag": tag}

    def _attach_issues(
        self, view: list[dict[str, Any]], validation: dict[str, Any], quality_report: dict[str, Any]
    ) -> None:
        issues = list(quality_report.get("issues", []))
        known_messages = {item.get("message") for item in issues}
        for level, key in (("error", "errors"), ("warning", "warnings")):
            for message in validation.get(key, []):
                if message not in known_messages:
                    issues.append({
                        "level": level, "location": f"validation.{key}",
                        "message": message, "suggestion": "在人工校正页面复核对应内容",
                    })
        for issue in issues:
            target = self._find_issue_target(view, str(issue.get("location", "")))
            if target is None:
                continue
            normalized = {
                "level": issue.get("level", "warning"),
                "message": issue.get("message", ""),
                "suggestion": issue.get("suggestion", ""),
            }
            target["issues"].append(normalized)
            status = {"error": "error", "warning": "warning", "suggestion": "need_review"}.get(
                normalized["level"], "need_review"
            )
            if self.STATUS_PRIORITY[status] > self.STATUS_PRIORITY[target["status"]]:
                target["status"] = status

    @staticmethod
    def _find_issue_target(view: list[dict[str, Any]], location: str) -> dict[str, Any] | None:
        for item in view:
            if item.get("target_id") and item["target_id"] in location:
                return item
        match = re.search(r"sections\[(\d+)\]", location)
        if match:
            section_id = f"sec{int(match.group(1)) + 1}"
            return next((item for item in view if item.get("section_id") == section_id), None)
        for field, node_type in (
            ("article.title", "title"), ("article.abstract", "abstract"),
            ("article.keywords", "keyword"), ("article.authors", "author"),
            ("article.affiliations", "affiliation"), ("article.references", "reference"),
        ):
            if field in location:
                return next((item for item in view if item["node_type"] == node_type), None)
        return view[0] if view else None
