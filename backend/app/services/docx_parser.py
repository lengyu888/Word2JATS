import re
import zipfile
from pathlib import Path
from typing import Any

from app.services.document_flow_parser import DocumentFlowParser


class DocxParser:
    SECTION_PATTERNS = (
        re.compile(r"^(\d+(?:\.\d+)*)[\s、.]+(.+)$"),
        re.compile(r"^([一二三四五六七八九十]+)、\s*(.+)$"),
        re.compile(r"^[（(]([一二三四五六七八九十]+)[）)]\s*(.+)$"),
    )
    AFFILIATION_WORDS = (
        "大学", "学院", "研究院", "实验室", "中心",
        "school", "university", "institute", "laboratory", "center",
    )
    ABSTRACT_RE = re.compile(r"^\s*(摘要|摘\s*要|abstract)\s*[:：]?\s*", re.I)
    KEYWORD_RE = re.compile(r"^\s*(关键词|关\s*键\s*词|key\s*words?|keywords)\s*[:：]?\s*", re.I)
    REFERENCE_RE = re.compile(r"^\s*(?:参考\s*文献|references?)\s*[:：]?\s*$", re.I)
    REFERENCE_LABEL_RE = re.compile(
        r"^\s*(?P<label>\[\s*\d+\s*\]|\(\s*\d+\s*\)|（\s*\d+\s*）|\d+\s*[.．、])"
        r"\s*(?P<raw>.*)$"
    )
    FIGURE_RE = DocumentFlowParser.FIGURE_RE
    TABLE_RE = DocumentFlowParser.TABLE_RE
    LIST_RE = DocumentFlowParser.LIST_RE

    def __init__(self, docx_path: str | Path, media_dir: str | Path):
        self.docx_path = Path(docx_path)
        self.media_dir = Path(media_dir)

    def parse(self) -> dict[str, Any]:
        flow = DocumentFlowParser(self.docx_path).parse()
        paragraphs = [node for node in flow if node.get("text", "").strip()]
        article = self._empty_article()
        skipped: set[int] = set()
        if paragraphs:
            title_index = self._find_title_index(paragraphs)
            article["title"] = paragraphs[title_index]["text"].strip()
            author_indexes, affiliation_indexes = self._extract_front_matter(
                paragraphs, title_index, article
            )
            skipped = {
                paragraphs[index]["flow_index"]
                for index in {title_index, *author_indexes, *affiliation_indexes}
            }
        self._parse_flow_content(flow, article, skipped)
        return article

    def _parse_flow_content(
        self, flow: list[dict[str, Any]], article: dict[str, Any], skipped: set[int]
    ) -> None:
        current_section: dict[str, Any] | None = None
        current_section_index = -1
        abstract_parts: list[str] = []
        in_abstract = False
        in_references = False
        unbound_figures: list[int] = []
        pending_figures: list[int] = []
        unbound_tables: list[int] = []
        pending_tables: list[int] = []

        for node in flow:
            if node["flow_index"] in skipped:
                continue
            node_type = node["type"]
            text = node.get("text", "").strip()

            if node_type == "image":
                in_abstract = False
                pending_index = self._pop_in_section(
                    pending_figures, article["figures"], current_section_index
                )
                figure_number = (
                    pending_index + 1
                    if pending_index is not None
                    else len(article["figures"]) + 1
                )
                path = self._save_flow_image(
                    node.get("media_path", ""), figure_number
                )
                if pending_index is not None:
                    article["figures"][pending_index].update(
                        path=path, section_index=current_section_index
                    )
                else:
                    article["figures"].append({
                        "id": f"fig{len(article['figures']) + 1}",
                        "caption": "",
                        "path": path,
                        "section_index": current_section_index,
                    })
                    unbound_figures.append(len(article["figures"]) - 1)
                continue

            if node_type == "table":
                in_abstract = False
                pending_index = self._pop_in_section(
                    pending_tables, article["tables"], current_section_index
                )
                if pending_index is not None:
                    article["tables"][pending_index].update(
                        rows=node.get("rows", []), section_index=current_section_index
                    )
                else:
                    article["tables"].append({
                        "id": f"tab{len(article['tables']) + 1}",
                        "caption": "",
                        "rows": node.get("rows", []),
                        "section_index": current_section_index,
                    })
                    unbound_tables.append(len(article["tables"]) - 1)
                continue

            if self.REFERENCE_RE.match(text):
                in_references = True
                in_abstract = False
                continue
            if in_references:
                if text:
                    article["references"].append(
                        self._parse_reference(text, len(article["references"]) + 1)
                    )
                continue

            if self.KEYWORD_RE.match(text):
                in_abstract = False
                article["keywords"] = self._split_values(
                    self.KEYWORD_RE.sub("", text, count=1)
                )
                continue
            if self.ABSTRACT_RE.match(text):
                in_abstract = True
                abstract_text = self.ABSTRACT_RE.sub("", text, count=1)
                if abstract_text:
                    abstract_parts.append(abstract_text)
                continue

            if node_type == "figure_caption":
                in_abstract = False
                unbound_index = self._pop_in_section(
                    unbound_figures, article["figures"], current_section_index
                )
                if unbound_index is not None:
                    article["figures"][unbound_index]["caption"] = text
                else:
                    article["figures"].append({
                        "id": f"fig{len(article['figures']) + 1}",
                        "caption": text,
                        "path": "",
                        "section_index": current_section_index,
                    })
                    pending_figures.append(len(article["figures"]) - 1)
                continue
            if node_type == "table_caption":
                in_abstract = False
                unbound_index = self._pop_in_section(
                    unbound_tables, article["tables"], current_section_index
                )
                if unbound_index is not None:
                    article["tables"][unbound_index]["caption"] = text
                else:
                    article["tables"].append({
                        "id": f"tab{len(article['tables']) + 1}",
                        "caption": text,
                        "rows": [],
                        "section_index": current_section_index,
                    })
                    pending_tables.append(len(article["tables"]) - 1)
                continue

            section = self._parse_section_title(text)
            if section:
                in_abstract = False
                article["sections"].append(section)
                current_section = section
                current_section_index = len(article["sections"]) - 1
                continue
            if in_abstract:
                if text:
                    abstract_parts.append(text)
                continue

            if node_type == "list":
                item = self.LIST_RE.sub("", text, count=1).strip()
                article["lists"].append({
                    "id": f"list{len(article['lists']) + 1}",
                    "items": [item or text],
                    "section_index": current_section_index,
                })
                continue
            if node_type == "formula":
                article["formulas"].append({
                    "id": f"eq{len(article['formulas']) + 1}",
                    "content": text,
                    "type": node.get("formula_type", "plain_text"),
                    "section_index": current_section_index,
                })
                continue
            if current_section is not None and text:
                current_section["paragraphs"].append(text)

        article["abstract"] = "\n".join(abstract_parts)

    @staticmethod
    def _empty_article() -> dict[str, Any]:
        return {
            "title": "", "authors": [], "affiliations": [], "abstract": "",
            "keywords": [], "sections": [], "figures": [], "tables": [], "lists": [],
            "formulas": [], "references": [],
        }

    def _find_title_index(self, paragraphs: list[dict[str, Any]]) -> int:
        best_index = 0
        best_score = -1.0
        for index, paragraph in enumerate(paragraphs[:10]):
            text = paragraph["text"].strip()
            score = 0.0
            if paragraph.get("alignment") == "center":
                score += 4
            if paragraph.get("bold"):
                score += 3
            if paragraph.get("font_size"):
                score += min(paragraph["font_size"] / 4, 5)
            if paragraph.get("type") == "title":
                score += 5
            if 4 <= len(text) <= 45:
                score += 2
            if self.ABSTRACT_RE.match(text) or self.KEYWORD_RE.match(text):
                score -= 8
            if score > best_score:
                best_index, best_score = index, score
        return best_index

    def _extract_front_matter(
        self, paragraphs: list[dict[str, Any]], title_index: int, article: dict[str, Any]
    ) -> tuple[set[int], set[int]]:
        author_indexes: set[int] = set()
        affiliation_indexes: set[int] = set()
        window = range(title_index + 1, min(len(paragraphs), title_index + 7))
        for index in window:
            text = paragraphs[index]["text"].strip()
            lower = text.lower()
            if (
                self.ABSTRACT_RE.match(text)
                or self.KEYWORD_RE.match(text)
                or self.REFERENCE_RE.match(text)
                or self._parse_section_title(text)
            ):
                break
            if any(word in lower for word in self.AFFILIATION_WORDS):
                article["affiliations"].append(text)
                affiliation_indexes.add(index)
                continue
            if (
                not author_indexes
                and len(text) <= 80
                and not self.FIGURE_RE.match(text)
                and not self.TABLE_RE.match(text)
                and paragraphs[index].get("type") != "formula"
                and re.search(r"[，,；;\s、]", text)
            ):
                names = [name for name in re.split(r"[，,；;\s、]+", text) if name]
                article["authors"] = [{"name": name, "orcid": ""} for name in names]
                author_indexes.add(index)
        return author_indexes, affiliation_indexes

    def _parse_reference(self, text: str, index: int) -> dict[str, str]:
        match = self.REFERENCE_LABEL_RE.match(text)
        label = match.group("label").strip() if match else ""
        raw = match.group("raw").strip() if match else text.strip()
        return {"id": f"ref{index}", "label": label, "raw": raw}

    def _parse_section_title(self, text: str) -> dict[str, Any] | None:
        for pattern in self.SECTION_PATTERNS:
            match = pattern.match(text)
            if not match:
                continue
            marker, title = match.groups()
            level = marker.count(".") + 1 if marker[0].isdigit() else (
                2 if text.startswith(("（", "(")) else 1
            )
            return {"title": title.strip(), "level": level, "paragraphs": []}
        return None

    @staticmethod
    def _split_values(text: str) -> list[str]:
        return [value.strip() for value in re.split(r"[；;，,、]+", text) if value.strip()]

    @staticmethod
    def _pop_in_section(
        indexes: list[int], items: list[dict[str, Any]], section_index: int
    ) -> int | None:
        for position, item_index in enumerate(indexes):
            if items[item_index].get("section_index", -1) == section_index:
                indexes.pop(position)
                return item_index
        return None

    def _save_flow_image(self, media_path: str, index: int) -> str:
        if not media_path:
            return ""
        self.media_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(media_path).suffix.lower() or ".bin"
        path = self.media_dir / f"figure_{index}{suffix}"
        with zipfile.ZipFile(self.docx_path) as archive:
            if media_path not in archive.namelist():
                return ""
            path.write_bytes(archive.read(media_path))
        return self._relative_path(path)

    def _relative_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return (Path(self.media_dir.name) / path.name).as_posix()
