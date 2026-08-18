import re
import zipfile
from pathlib import Path
from typing import Any

from app.services.document_flow_parser import DocumentFlowParser
from app.services.contributor_normalizer import ContributorNormalizer
from app.services.float_candidate_matcher import FloatCandidateMatcher
from app.services.formula_semantic_normalizer import FormulaSemanticNormalizer
from app.services.media_preview import TiffPreviewConverter
from app.services.profile_loader import ProfileLoader
from app.services.reference_parser import ReferenceParser
from app.services.structure_evidence import StructureEvidence


class DocxParser:
    PRE_BODY_HEADINGS = {"abbreviations", "abbreviations and acronyms"}
    CONVENTIONAL_SUBHEADINGS = {
        "limitations", "strengths and limitations",
        "limitations and future directions", "future directions",
        "main findings", "principal findings", "key findings",
    }
    PUBLISHER_BACK_HEADINGS = {
        "funding", "funding information", "conflict of interest",
        "conflicts of interest", "competing interests", "author contributions",
        "authors' contributions", "ethics approval", "ethical approval",
        "data availability", "data availability statement", "acknowledgments",
        "acknowledgements", "informed consent statement",
        "institutional review board statement",
        "abbreviations", "abbreviations and acronyms",
        "availability of data and materials",
    }
    EXACT_PUBLISHER_BACK_HEADINGS = {
        "abbreviations", "abbreviations and acronyms",
        "availability of data and materials",
    }
    MULTI_PANEL_RE = re.compile(
        r"(?:\([A-Za-z]\s*[-\u2013]\s*[A-Za-z]\)|\bpanels?\b|\bplots?\b)", re.I
    )
    CAPTION_CONTINUATION_RE = re.compile(
        r"^\s*(?:"
        r"(?:The\s+)?[xy]-axis\b|"
        r"(?:Error\s+bars?|Bars?|Whiskers?|Dots?|Circles?|Squares?|Triangles?)\b|"
        r"(?:Solid|Dashed|Dotted)\s+(?:line|curve|bar)s?\b|"
        r"(?:Data|Values|Results)\s+(?:are|were|represent|show)\b|"
        r"(?:Panels?|Plots?)\s+[A-Z](?:\s*[-\u2013]\s*[A-Z])?\b|"
        r"(?:Note|Notes|Abbreviations?)\s*[:.]|"
        r"(?:[A-Z][A-Za-z0-9()/ -]{1,40})\s*:\s*[a-z]|"
        r"[\*\u2020\u2021]\s+"
        r")",
        re.I,
    )
    SECTION_PATTERNS = (
        re.compile(r"^(\d+(?:\.\d+)*\.?)\s+(.+)$"),
        re.compile(r"^(\d+(?:\.\d+)*)[\s、.]+(.+)$"),
        re.compile(r"^([一二三四五六七八九十]+)、\s*(.+)$"),
        re.compile(r"^[（(]([一二三四五六七八九十]+)[）)]\s*(.+)$"),
    )
    AFFILIATION_WORDS = (
        "大学", "学院", "研究院", "实验室", "中心", "医院", "系", "部",
        "school", "university", "institute", "laboratory", "center",
        "department", "faculty", "hospital", "college", "academy",
        "independent researcher",
    )
    ABSTRACT_RE = re.compile(r"^\s*(摘要|摘\s*要|abstract)\s*[:：]?\s*", re.I)
    KEYWORD_RE = re.compile(r"^\s*(关键词|关\s*键\s*词|key\s*words?|keywords)\s*[:：]?\s*", re.I)
    REFERENCE_RE = re.compile(
        r"^\s*(?:参考\s*文献|references?(?:\s*(?:and|&)\s*notes?)?)\s*[:：]?\s*$",
        re.I,
    )
    ARTICLE_TYPE_LABELS = {
        "original research", "research article", "original article", "review",
        "review article", "case report", "short communication", "editorial",
        "letter", "protocol", "article",
    }
    AUTHOR_HEADING_LABELS = {
        "author", "authors", "author information", "author details",
    }
    ABSTRACT_TRAILING_METADATA_RE = re.compile(
        r"(?:\s|^)\(?\s*(?:received|revised|accepted|published|copyright)\b.*$",
        re.I,
    )
    ABSTRACT_NON_APPLICABLE_REGISTRATION_RE = re.compile(
        r"(?:\s|^)clinical\s+trial\s+registration\s*:\s*not\s+applicable\.?\s*$",
        re.I,
    )
    REFERENCE_LABEL_RE = re.compile(
        r"^\s*(?P<label>\[\s*\d+\s*\]|\(\s*\d+\s*\)|（\s*\d+\s*）|\d+\s*[.．、])"
        r"\s*(?P<raw>.*)$"
    )
    FIGURE_RE = DocumentFlowParser.FIGURE_RE
    TABLE_RE = DocumentFlowParser.TABLE_RE
    LIST_RE = DocumentFlowParser.LIST_RE

    def __init__(
        self, docx_path: str | Path, media_dir: str | Path, profile: dict[str, Any] | None = None
    ):
        self.docx_path = Path(docx_path)
        self.media_dir = Path(media_dir)
        self.profile = profile or {}
        self.reference_parser = ReferenceParser()
        self.contributor_normalizer = ContributorNormalizer()
        self.structure_evidence = StructureEvidence()
        self.float_matcher = FloatCandidateMatcher()
        self.formula_normalizer = FormulaSemanticNormalizer()
        self.tiff_preview_converter = TiffPreviewConverter()
        self.abstract_re = self._marker_regex(
            self.profile.get("abstract_markers"), self.ABSTRACT_RE
        )
        self.keyword_re = self._marker_regex(
            self.profile.get("keyword_markers"), self.KEYWORD_RE
        )
        self.figure_patterns = self._compile_patterns(
            self.profile.get("figure_caption_patterns")
        )
        self.table_patterns = self._compile_patterns(
            self.profile.get("table_caption_patterns")
        )
        self.title_styles = {
            str(style).casefold() for style in self.profile.get("title_styles", [])
        }

    def parse(self) -> dict[str, Any]:
        flow = DocumentFlowParser(self.docx_path).parse()
        self.document_flow_nodes = flow
        paragraphs = [node for node in flow if node.get("text", "").strip()]
        article = self._empty_article()
        skipped: set[int] = set()
        if paragraphs:
            title_index = self._find_title_index(paragraphs)
            article["title"] = paragraphs[title_index]["text"].strip()
            _, _, front_indexes = self._extract_front_matter(
                paragraphs, title_index, article
            )
            skipped = {
                paragraphs[index]["flow_index"]
                for index in front_indexes
            }
        self._parse_flow_content(flow, article, skipped)
        self._assign_style_section_labels(article)
        article["authors"] = [
            self.contributor_normalizer.normalize(author)
            for author in article["authors"]
        ]
        article["formulas"] = [
            self.formula_normalizer.normalize(formula)
            for formula in article["formulas"]
        ]
        self._resolve_table_image_fallbacks(article)
        self._annotate_structure_evidence(article)
        return ProfileLoader.apply_metadata(article, self.profile)

    def _parse_flow_content(
        self, flow: list[dict[str, Any]], article: dict[str, Any], skipped: set[int]
    ) -> None:
        current_section: dict[str, Any] | None = None
        current_section_index = -1
        abstract_parts: list[str] = []
        in_abstract = False
        in_references = False
        in_publisher_back_matter = False
        awaiting_keywords = False
        unbound_figures: list[int] = []
        pending_figures: list[int] = []
        unbound_tables: list[int] = []
        pending_tables: list[int] = []
        last_caption_target: tuple[str, int, int] | None = None
        active_embedded_table_index: int | None = None
        last_native_table_index: int | None = None

        for node in flow:
            if node["flow_index"] in skipped:
                continue
            node_type = node["type"]
            text = node.get("text", "").strip()
            if self._matches_any(self.figure_patterns, text) and self._profile_caption_evidence(
                node, text, "figure"
            ):
                node_type = "figure_caption"
            elif self._matches_any(self.table_patterns, text) and self._profile_caption_evidence(
                node, text, "table"
            ):
                node_type = "table_caption"

            if node_type == "image":
                in_abstract = False
                if last_caption_target and last_caption_target[0] != "figure":
                    last_caption_target = None
                active_embedded_table_index = None
                if current_section is None:
                    media_index = len(article["figures"]) + len(
                        article["auxiliary_media"]
                    ) + 1
                    media = self._save_flow_image(
                        node.get("media_path", ""), media_index
                    )
                    article["auxiliary_media"].append({
                        "id": f"media{len(article['auxiliary_media']) + 1}",
                        **media,
                        "role": "front-matter",
                    })
                    continue
                pending_index = self._pop_in_section(
                    pending_figures, article["figures"], current_section_index
                )
                figure_number = (
                    len(article["auxiliary_media"]) + pending_index + 1
                    if pending_index is not None
                    else len(article["auxiliary_media"]) + len(article["figures"]) + 1
                )
                media = self._save_flow_image(
                    node.get("media_path", ""), figure_number
                )
                if pending_index is not None:
                    article["figures"][pending_index].update(
                        **media,
                        section_index=current_section_index,
                        _media_flow_index=node["flow_index"],
                    )
                else:
                    article["figures"].append({
                        "id": f"fig{len(article['figures']) + 1}",
                        "caption": "",
                        **media,
                        "section_index": current_section_index,
                        "_media_flow_index": node["flow_index"],
                    })
                    unbound_figures.append(len(article["figures"]) - 1)
                continue

            if node_type == "table":
                in_abstract = False
                if last_caption_target and last_caption_target[0] == "table":
                    last_caption_target = None
                active_embedded_table_index = None
                pending_index = self._pop_in_section(
                    pending_tables, article["tables"], current_section_index
                )
                if pending_index is not None:
                    article["tables"][pending_index].update(
                        rows=node.get("rows", []),
                        section_index=current_section_index,
                        _media_flow_index=node["flow_index"],
                    )
                    last_native_table_index = pending_index
                    caption_flow_index = article["tables"][pending_index].get(
                        "_caption_flow_index"
                    )
                    clustered_figures = [
                        figure_index
                        for figure_index in unbound_figures
                        if article["figures"][figure_index].get("section_index", -1)
                        == current_section_index
                        and caption_flow_index is not None
                        and caption_flow_index
                        < article["figures"][figure_index].get(
                            "_media_flow_index", -1
                        )
                        < node["flow_index"]
                    ]
                    if len(clustered_figures) == 1:
                        figure_index = clustered_figures[0]
                        figure = article["figures"][figure_index]
                        article["tables"][pending_index]["path"] = figure.get(
                            "path", ""
                        )
                        figure["_absorbed_by_table"] = True
                        unbound_figures.remove(figure_index)
                else:
                    article["tables"].append({
                        "id": f"tab{len(article['tables']) + 1}",
                        "caption": "",
                        "rows": node.get("rows", []),
                        "section_index": current_section_index,
                        "_media_flow_index": node["flow_index"],
                    })
                    last_native_table_index = len(article["tables"]) - 1
                    unbound_tables.append(last_native_table_index)
                continue

            if self.REFERENCE_RE.match(text):
                in_references = True
                in_publisher_back_matter = False
                in_abstract = False
                awaiting_keywords = False
                active_embedded_table_index = None
                last_native_table_index = None
                continue
            if in_references:
                if text:
                    label_match = self.reference_parser.LABEL_RE.match(text)
                    numbered_mode = bool(
                        article["references"] and article["references"][0].get("label")
                    )
                    if (
                        not label_match
                        and numbered_mode
                        and self._looks_like_unlabeled_reference(text)
                    ):
                        synthetic_label = f"[{len(article['references']) + 1}]"
                        article["references"].append(
                            self._parse_reference(
                                f"{synthetic_label} {text}",
                                len(article["references"]) + 1,
                            )
                        )
                    elif (
                        not label_match
                        and numbered_mode
                        and self._looks_like_reference_continuation(text)
                    ):
                        previous = article["references"][-1]
                        combined = " ".join(
                            part for part in (previous.get("raw", ""), text) if part
                        )
                        article["references"][-1] = self._parse_reference(
                            f"{previous.get('label', '')} {combined}",
                            len(article["references"]),
                        )
                    else:
                        article["references"].append(
                            self._parse_reference(text, len(article["references"]) + 1)
                        )
                continue

            if self._is_publisher_back_heading(text) and current_section is not None:
                in_abstract = False
                in_publisher_back_matter = True
                active_embedded_table_index = None
                last_native_table_index = None
                continue
            if in_publisher_back_matter:
                continue

            if self.keyword_re.match(text):
                in_abstract = False
                active_embedded_table_index = None
                last_native_table_index = None
                keyword_text = self.keyword_re.sub("", text, count=1)
                article["keywords"] = self._split_values(keyword_text)
                awaiting_keywords = not bool(article["keywords"])
                continue
            if self.abstract_re.match(text):
                in_abstract = True
                active_embedded_table_index = None
                last_native_table_index = None
                abstract_text = self.abstract_re.sub("", text, count=1)
                if abstract_text:
                    abstract_parts.append(abstract_text)
                continue

            if awaiting_keywords and text:
                article["keywords"] = self._split_values(text)
                awaiting_keywords = False
                active_embedded_table_index = None
                last_native_table_index = None
                continue

            if (
                current_section is None
                and self._normalized_heading(text) in self.PRE_BODY_HEADINGS
            ):
                in_abstract = False
                active_embedded_table_index = None
                last_native_table_index = None
                continue

            if node_type == "figure_caption":
                in_abstract = False
                matching_figures = [
                    index for index in unbound_figures
                    if article["figures"][index].get("section_index", -1)
                    == current_section_index
                ]
                if len(matching_figures) > 1 and self.MULTI_PANEL_RE.search(text):
                    unbound_index = matching_figures[0]
                    paths = [
                        article["figures"][index].get("path", "")
                        for index in matching_figures
                        if article["figures"][index].get("path")
                    ]
                    article["figures"][unbound_index]["paths"] = paths
                    article["figures"][unbound_index]["_media_flow_index"] = min(
                        article["figures"][index].get(
                            "_media_flow_index", node["flow_index"]
                        )
                        for index in matching_figures
                    )
                    for index in reversed(matching_figures[1:]):
                        article["figures"].pop(index)
                    unbound_figures[:] = [
                        index for index in unbound_figures
                        if index not in matching_figures
                    ]
                else:
                    unbound_index = self._pop_in_section(
                        unbound_figures, article["figures"], current_section_index
                    )
                if unbound_index is not None:
                    article["figures"][unbound_index]["caption"] = text
                    article["figures"][unbound_index]["_caption_flow_index"] = node[
                        "flow_index"
                    ]
                    caption_index = unbound_index
                else:
                    article["figures"].append({
                        "id": f"fig{len(article['figures']) + 1}",
                        "caption": text,
                        "path": "",
                        "section_index": current_section_index,
                        "_caption_flow_index": node["flow_index"],
                    })
                    pending_figures.append(len(article["figures"]) - 1)
                    caption_index = len(article["figures"]) - 1
                last_caption_target = ("figure", caption_index, current_section_index)
                active_embedded_table_index = None
                last_native_table_index = None
                continue
            if node_type == "table_caption":
                in_abstract = False
                unbound_index = self._pop_in_section(
                    unbound_tables, article["tables"], current_section_index
                )
                if unbound_index is not None:
                    article["tables"][unbound_index]["caption"] = text
                    article["tables"][unbound_index]["_caption_flow_index"] = node[
                        "flow_index"
                    ]
                    caption_index = unbound_index
                else:
                    article["tables"].append({
                        "id": f"tab{len(article['tables']) + 1}",
                        "caption": text,
                        "rows": [],
                        "section_index": current_section_index,
                        "_caption_flow_index": node["flow_index"],
                    })
                    pending_tables.append(len(article["tables"]) - 1)
                    caption_index = len(article["tables"]) - 1
                last_caption_target = ("table", caption_index, current_section_index)
                active_embedded_table_index = None
                last_native_table_index = None
                continue

            if self._is_caption_continuation(
                text, node_type, current_section_index, last_caption_target, article
            ):
                self._append_caption_continuation(article, last_caption_target, text)
                continue

            if self._is_embedded_figure_table_row(
                text, node_type, current_section_index, last_caption_target
            ):
                active_embedded_table_index = self._append_embedded_figure_table_row(
                    article, active_embedded_table_index, current_section_index, text
                )
                continue

            if self._is_table_note(text, node_type, last_native_table_index, article):
                article["tables"][last_native_table_index].setdefault("notes", []).append(text)

            if (
                node_type == "heading"
                and not str(node.get("style", "")).strip()
                and current_section is not None
                and int(current_section.get("level", 1) or 1) >= 3
                and self._normalized_heading(text) not in self.CONVENTIONAL_SUBHEADINGS
                and not re.match(r"^\d+(?:\.\d+)*\.?\s+", text)
                and not text.lstrip().startswith(("\u25cf", "\u2022"))
            ):
                current_section["paragraphs"].append(text)
                last_caption_target = None
                active_embedded_table_index = None
                last_native_table_index = None
                continue

            section = self._parse_section_title(text, node)
            if section:
                in_abstract = False
                last_caption_target = None
                active_embedded_table_index = None
                last_native_table_index = None
                if text.lstrip().startswith(("●", "•")) and current_section:
                    section["level"] = min(
                        6, int(current_section.get("level", 1)) + 1
                    )
                article["sections"].append(section)
                current_section = section
                current_section_index = len(article["sections"]) - 1
                continue
            if in_abstract:
                if text:
                    abstract_parts.append(text)
                continue

            if node_type == "list":
                last_caption_target = None
                active_embedded_table_index = None
                last_native_table_index = None
                item = self.LIST_RE.sub("", text, count=1).strip()
                article["lists"].append({
                    "id": f"list{len(article['lists']) + 1}",
                    "items": [item or text],
                    "section_index": current_section_index,
                })
                continue
            if node_type == "formula":
                last_caption_target = None
                active_embedded_table_index = None
                last_native_table_index = None
                article["formulas"].append({
                    "id": f"eq{len(article['formulas']) + 1}",
                    "content": text,
                    "type": node.get("formula_type", "plain_text"),
                    "omml": node.get("omml", ""),
                    "mathml": node.get("mathml", ""),
                    "latex": node.get("latex", ""),
                    "conversion_status": node.get(
                        "conversion_status",
                        "failed" if node.get("formula_type") == "omml" else "success",
                    ),
                    "supported_features": node.get("supported_features", []),
                    "unsupported_features": node.get("unsupported_features", []),
                    "issues": node.get("issues", []),
                    "_display_signals": node.get("display_signals", {}),
                    "section_index": current_section_index,
                })
                continue
            if current_section is not None and text:
                current_section["paragraphs"].append(text)
                last_caption_target = None
                active_embedded_table_index = None
                last_native_table_index = None

        article["abstract"] = self._clean_abstract("\n".join(abstract_parts))

    def _resolve_table_image_fallbacks(self, article: dict[str, Any]) -> None:
        article["figures"] = [
            figure
            for figure in article["figures"]
            if not figure.pop("_absorbed_by_table", False)
        ]
        captions = [
            {
                "flow_index": table.get("_caption_flow_index"),
                "section_index": table.get("section_index", -1),
                "kind": "table",
                "number": self._caption_number(table.get("caption", "")),
                "table_id": table.get("id"),
            }
            for table in article["tables"]
            if table.get("caption") and not table.get("rows") and not table.get("path")
        ]
        objects = [
            {
                "flow_index": figure.get("_media_flow_index"),
                "section_index": figure.get("section_index", -1),
                "kind": "image",
                "id": figure.get("id"),
            }
            for figure in article["figures"]
            if figure.get("path") and not figure.get("caption")
        ]
        matches = self.float_matcher.match(captions, objects)
        matched_figure_ids = set()
        for caption, match in zip(captions, matches):
            if not match.get("object_id"):
                continue
            table = next(
                item for item in article["tables"] if item.get("id") == caption["table_id"]
            )
            figure = next(
                item for item in article["figures"]
                if item.get("id") == match["object_id"]
            )
            table["path"] = figure.get("path", "")
            table["_media_flow_index"] = figure.get("_media_flow_index")
            matched_figure_ids.add(figure.get("id"))
        if matched_figure_ids:
            article["figures"] = [
                figure
                for figure in article["figures"]
                if figure.get("id") not in matched_figure_ids
            ]
        article["figures"] = self._deduplicate_float_candidates(
            article["figures"], evidence_fields=("path", "paths")
        )
        article["tables"] = self._deduplicate_float_candidates(
            article["tables"], evidence_fields=("rows", "path")
        )
        self._renumber_float_ids(article["figures"], "fig")
        self._renumber_float_ids(article["tables"], "tab")

    @classmethod
    def _deduplicate_float_candidates(
        cls, items: list[dict[str, Any]], *, evidence_fields: tuple[str, ...]
    ) -> list[dict[str, Any]]:
        """Prefer a media/table-backed candidate when caption numbers repeat."""
        grouped: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for index, item in enumerate(items):
            number = cls._caption_number(str(item.get("caption", "")))
            if number:
                grouped.setdefault(number, []).append((index, item))
        removed: set[int] = set()
        for candidates in grouped.values():
            evidenced = [
                (index, item)
                for index, item in candidates
                if any(bool(item.get(field)) for field in evidence_fields)
            ]
            if not evidenced:
                continue
            best_index, _ = max(
                evidenced,
                key=lambda pair: (
                    int(bool(pair[1].get("path") or pair[1].get("paths"))),
                    len(pair[1].get("rows", []) or []),
                    len(str(pair[1].get("caption", ""))),
                    -pair[0],
                ),
            )
            for index, item in candidates:
                if index != best_index and not any(
                    bool(item.get(field)) for field in evidence_fields
                ):
                    removed.add(index)
        return [item for index, item in enumerate(items) if index not in removed]

    @staticmethod
    def _renumber_float_ids(items: list[dict[str, Any]], prefix: str) -> None:
        for index, item in enumerate(items, start=1):
            item["id"] = f"{prefix}{index}"

    def _assign_style_section_labels(self, article: dict[str, Any]) -> None:
        counters = [0] * 6
        for section in article.get("sections", []):
            level = max(1, min(6, int(section.get("level", 1) or 1)))
            existing = section.get("label", "")
            if existing:
                numbers = [int(value) for value in re.findall(r"\d+", existing)]
                if numbers:
                    for index, number in enumerate(numbers[:6]):
                        counters[index] = number
                    for index in range(len(numbers), len(counters)):
                        counters[index] = 0
                section.pop("_numbered_style_heading", None)
                continue
            if not section.pop("_numbered_style_heading", False):
                continue
            for index in range(level - 1):
                if counters[index] == 0:
                    counters[index] = 1
            counters[level - 1] += 1
            for index in range(level, len(counters)):
                counters[index] = 0
            parts = counters[:level]
            label = ".".join(str(part) for part in parts)
            section["label"] = f"{label}." if level == 1 else label

    @staticmethod
    def _caption_number(text: str) -> str:
        match = re.search(r"\d+(?:[-.]\d+)?[a-z]?", text, re.I)
        return match.group(0).casefold() if match else ""

    def _is_caption_continuation(
        self,
        text: str,
        node_type: str,
        current_section_index: int,
        target: tuple[str, int, int] | None,
        article: dict[str, Any],
    ) -> bool:
        if not target or not text or node_type not in {"paragraph", "heading"}:
            return False
        object_type, index, section_index = target
        if section_index != current_section_index or len(text) > 700:
            return False
        collection_name = "figures" if object_type == "figure" else "tables"
        collection = article.get(collection_name, [])
        if index >= len(collection) or not collection[index].get("caption"):
            return False
        if self._parse_section_title(text, {"type": node_type}):
            return False
        if self._matches_any(self.figure_patterns, text) or self._matches_any(
            self.table_patterns, text
        ):
            return False
        if self.FIGURE_RE.match(text) or self.TABLE_RE.match(text):
            return False
        return bool(
            self.CAPTION_CONTINUATION_RE.match(text)
            or text.startswith(("注:", "注：", "说明:", "说明："))
        )

    @staticmethod
    def _append_caption_continuation(
        article: dict[str, Any], target: tuple[str, int, int] | None, text: str
    ) -> None:
        if not target:
            return
        object_type, index, _ = target
        collection_name = "figures" if object_type == "figure" else "tables"
        collection = article.get(collection_name, [])
        if index >= len(collection):
            return
        caption = collection[index].get("caption", "").rstrip()
        separator = " " if caption and not caption.endswith(("\n", " ")) else ""
        collection[index]["caption"] = f"{caption}{separator}{text.strip()}"

    def _is_embedded_figure_table_row(
        self,
        text: str,
        node_type: str,
        current_section_index: int,
        target: tuple[str, int, int] | None,
    ) -> bool:
        if not target or not text or node_type not in {"paragraph", "heading"}:
            return False
        object_type, _, section_index = target
        if object_type != "figure" or section_index != current_section_index:
            return False
        if len(text) > 220 or self.FIGURE_RE.match(text) or self.TABLE_RE.match(text):
            return False
        cells = self._split_inline_table_row(text)
        if len(cells) < 3:
            return False
        numeric_cells = sum(bool(re.search(r"\d", cell)) for cell in cells)
        lower = text.casefold()
        is_time_header = "month" in lower and numeric_cells >= 2
        is_numeric_row = bool(re.match(r"^\s*[\d<>=+-]+(?:\s+|$)", text)) and numeric_cells >= 3
        return is_time_header or is_numeric_row

    @staticmethod
    def _split_inline_table_row(text: str) -> list[str]:
        cells = [cell.strip() for cell in re.split(r"\s{2,}", text) if cell.strip()]
        if len(cells) >= 3:
            return cells
        if re.fullmatch(r"[\d\s<>=+.\-–—%]+", text):
            return [cell.strip() for cell in text.split() if cell.strip()]
        return cells

    def _append_embedded_figure_table_row(
        self,
        article: dict[str, Any],
        table_index: int | None,
        section_index: int,
        text: str,
    ) -> int:
        if table_index is None or table_index >= len(article["tables"]):
            article["tables"].append({
                "id": f"tab{len(article['tables']) + 1}",
                "caption": "patients at risk",
                "rows": [],
                "section_index": section_index,
            })
            table_index = len(article["tables"]) - 1
        article["tables"][table_index].setdefault("rows", []).append(
            self._split_inline_table_row(text)
        )
        return table_index

    @staticmethod
    def _is_table_note(
        text: str,
        node_type: str,
        table_index: int | None,
        article: dict[str, Any],
    ) -> bool:
        if table_index is None or table_index >= len(article.get("tables", [])):
            return False
        if node_type not in {"paragraph", "heading"} or not text or len(text) > 800:
            return False
        table = article["tables"][table_index]
        if not table.get("rows"):
            return False
        return bool(
            re.match(r"^\s*(?:Note|Notes|Abbreviations?)\s*[:：.]", text, re.I)
            or text.startswith(("注:", "注：", "说明:", "说明："))
        )

    def _annotate_structure_evidence(self, article: dict[str, Any]) -> None:
        for object_type, collection in (
            ("figure", article["figures"]),
            ("table", article["tables"]),
        ):
            for item in collection:
                caption = item.get("caption", "").strip()
                has_content = bool(
                    item.get("path")
                    or item.get("paths")
                    or (object_type == "table" and item.get("rows"))
                )
                if caption and has_content:
                    media_index = item.get("_media_flow_index")
                    caption_index = item.get("_caption_flow_index")
                    distance = (
                        abs(media_index - caption_index)
                        if media_index is not None and caption_index is not None
                        else None
                    )
                    result = self.structure_evidence.score_binding(
                        object_type=object_type,
                        same_section=True,
                        distance=distance,
                        number_match=self._caption_number_matches(item, caption),
                        explicit_caption=True,
                    )
                elif caption:
                    noun = "图片" if object_type == "figure" else "表格"
                    result = self.structure_evidence.review_result(
                        f"{noun}标题未绑定{noun}内容，需要人工复核。",
                        f"请确认标题对应的{noun}并在人工校正页完成绑定。",
                    )
                else:
                    noun = "图片" if object_type == "figure" else "表格"
                    caption_name = "图题" if object_type == "figure" else "表题"
                    result = self.structure_evidence.review_result(
                        f"{noun}缺少{caption_name}，需要人工复核。",
                        f"请补充{caption_name}后重新生成 XML。",
                    )
                item.update(result)
                item.pop("_media_flow_index", None)
                item.pop("_caption_flow_index", None)

        for formula in article["formulas"]:
            signals = formula.pop("_display_signals", {})
            result = self.structure_evidence.score_formula(
                has_math_paragraph=bool(signals.get("has_math_paragraph")),
                pure_math=bool(signals.get("pure_math", True)),
                aligned=bool(signals.get("aligned")),
                numbered=bool(signals.get("numbered")),
            )
            conversion_status = formula.get("conversion_status", "success")
            if conversion_status == "partial":
                result["status"] = "need_review"
                result["confidence"] = min(result["confidence"], 0.70)
            elif conversion_status == "failed":
                result["status"] = "warning"
                result["confidence"] = min(result["confidence"], 0.40)
            result["issues"] = [*formula.get("issues", []), *result["issues"]]
            formula.update(result)

    @staticmethod
    def _caption_number_matches(item: dict[str, Any], caption: str) -> bool:
        item_number = re.search(r"\d+$", str(item.get("id", "")))
        caption_number = re.search(r"\d+", caption)
        return bool(
            item_number
            and caption_number
            and item_number.group() == caption_number.group()
        )

    @staticmethod
    def _empty_article() -> dict[str, Any]:
        return {
            "title": "", "authors": [], "affiliations": [], "abstract": "",
            "keywords": [], "sections": [], "figures": [], "auxiliary_media": [],
            "tables": [], "lists": [],
            "formulas": [], "references": [],
            "document_flow_view": [],
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
            style = str(paragraph.get("style", "")).casefold()
            if style in self.title_styles:
                score += 5
            if "title" in style and "type" not in style:
                score += 10
            if "articletype" in style or text.casefold().strip(" .:") in self.ARTICLE_TYPE_LABELS:
                score -= 12
            affiliation_hits = sum(
                word in text.casefold() for word in self.AFFILIATION_WORDS
            )
            if affiliation_hits >= 2 or (
                affiliation_hits
                and re.match(r"^\s*(?:\d+|[a-z])(?:[\s.)]|(?=[A-Z]))", text)
            ):
                score -= 8
            if any(marker in text.casefold() for marker in ("correspondence", "orcid")):
                score -= 10
            if 4 <= len(text) <= 45:
                score += 2
            if 46 <= len(text) <= 350:
                score += 3
            if index == 0 and len(text) >= 20 and paragraph.get("type") in {"title", "heading"}:
                score += 3
            if self.abstract_re.match(text) or self.keyword_re.match(text):
                score -= 8
            if score > best_score:
                best_index, best_score = index, score
        return best_index

    def _extract_front_matter(
        self, paragraphs: list[dict[str, Any]], title_index: int, article: dict[str, Any]
    ) -> tuple[set[int], set[int], set[int]]:
        author_indexes: set[int] = set()
        affiliation_indexes: set[int] = set()
        boundary = self._front_matter_boundary(paragraphs, title_index)
        front_indexes = set(range(0, boundary))
        collecting_affiliations = True
        window = range(title_index + 1, boundary)
        for index in window:
            text = paragraphs[index]["text"].strip()
            lower = text.lower()
            if any(marker in lower for marker in ("correspond", "orcid", "academic editor")):
                collecting_affiliations = False
            if collecting_affiliations and self._looks_like_affiliation_paragraph(
                paragraphs[index]
            ):
                article["affiliations"].append(text)
                affiliation_indexes.add(index)
                continue
            if not author_indexes:
                names = self._parse_author_names(text)
            else:
                names = []
            if names:
                article["authors"] = [{"name": name, "orcid": ""} for name in names]
                author_indexes.add(index)
        article["affiliations"] = list(dict.fromkeys(article["affiliations"]))
        return author_indexes, affiliation_indexes, front_indexes

    def _front_matter_boundary(
        self, paragraphs: list[dict[str, Any]], title_index: int
    ) -> int:
        for index in range(title_index + 1, len(paragraphs)):
            text = paragraphs[index]["text"].strip()
            if self.abstract_re.match(text) or self.keyword_re.match(text):
                return index
        return title_index + 1

    def _parse_author_names(self, text: str) -> list[str]:
        lower = text.casefold()
        if (
            not text
            or len(text) > 300
            or self._normalized_heading(text) in self.AUTHOR_HEADING_LABELS
            or "@" in text
            or any(word in lower for word in self.AFFILIATION_WORDS)
            or any(marker in lower for marker in (
                "correspond", "contributed", "affiliation", "address", "orcid",
                "submitted", "revised", "accepted", "editor",
            ))
        ):
            return []
        cleaned = re.sub(
            r"\b(?:m\.?\s?d\.?|ph\.?\s?d\.?|m\.?\s?sc\.?|"
            r"b\.?\s?sc\.?|m\.?\s?b\.?)\s*(?=\d|\W|$)",
            "",
            text,
            flags=re.I,
        )
        cleaned = re.sub(r"\s+and\s+", ",", cleaned, flags=re.I)
        candidates = re.split(
            r"[,，;；]|\.\s+(?=[A-Z\u00c0-\u024f])|"
            r"\s{2,}(?=[A-Z\u00c0-\u024f])",
            cleaned,
        )
        names = []
        for candidate in candidates:
            value = candidate.strip(" .:()")
            value = re.sub(
                r"[\d¹²³⁴⁵⁶⁷⁸⁹⁰†‡#*]+(?:\s*)$", "", value
            ).strip(" .:()")
            value = re.sub(r"^[\d¹²³⁴⁵⁶⁷⁸⁹⁰†‡#*]+", "", value).strip()
            words = [word for word in value.split() if any(char.isalpha() for char in word)]
            is_chinese_name = bool(re.fullmatch(r"[\u3400-\u9fff]{2,4}", value))
            if is_chinese_name or (2 <= len(words) <= 6 and len(value) <= 80):
                names.append(value)
        return list(dict.fromkeys(names))

    def _looks_like_affiliation_paragraph(
        self, paragraph: dict[str, Any]
    ) -> bool:
        text = str(paragraph.get("text", "")).strip()
        lower = text.casefold()
        style = str(paragraph.get("style", "")).casefold()
        if "affiliation" in style:
            return True
        if any(word in lower for word in self.AFFILIATION_WORDS):
            return True
        return bool(
            re.match(r"^\s*(?:\d+|[a-z])(?=[A-Z\u00c0-\u024f])", text)
            and text.count(",") >= 2
            and len(text) >= 20
        )

    @staticmethod
    def _profile_caption_evidence(
        node: dict[str, Any], text: str, expected_kind: str
    ) -> bool:
        if node.get("type") in {"figure_caption", "table_caption"}:
            return True
        return DocumentFlowParser._looks_like_float_caption(
            text,
            str(node.get("style", "")).casefold(),
            expected_kind,
        )

    def _clean_abstract(self, text: str) -> str:
        cleaned = self.ABSTRACT_TRAILING_METADATA_RE.sub("", text).strip()
        return self.ABSTRACT_NON_APPLICABLE_REGISTRATION_RE.sub("", cleaned).strip()

    def _parse_reference(self, text: str, index: int) -> dict[str, Any]:
        return self.reference_parser.parse(text, index)

    @classmethod
    def _is_publisher_back_heading(cls, text: str) -> bool:
        normalized = cls._normalized_heading(text)
        if any(
            normalized.startswith(f"{heading}:")
            for heading in cls.EXACT_PUBLISHER_BACK_HEADINGS
        ):
            return False
        prefix = normalized.split(":", 1)[0].strip()
        return normalized in cls.PUBLISHER_BACK_HEADINGS or prefix in cls.PUBLISHER_BACK_HEADINGS

    @staticmethod
    def _normalized_heading(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip(" .:").casefold()

    @staticmethod
    def _looks_like_unlabeled_reference(text: str) -> bool:
        author_start = re.match(
            r"^[A-Z][A-Za-z'\u2019-]+\s+[A-Z]{1,4}(?:\s*,|,)", text
        )
        has_year = bool(re.search(r"\b(?:19|20)\d{2}\b", text))
        has_bibliographic_numbers = bool(
            re.search(r"\b\d+\s*(?:\([^)]+\))?\s*:\s*\d+", text)
        )
        return bool(author_start and has_year and has_bibliographic_numbers)

    @staticmethod
    def _looks_like_reference_continuation(text: str) -> bool:
        normalized = text.strip().casefold()
        if normalized.startswith(("http://", "https://", "doi:")):
            return True
        source_prefixes = (
            "journal ", "jama ", "jama netw", "bmj ", "circulation",
            "nature ", "science ", "frontiers ", "proceedings ", "ieee ",
        )
        return normalized.startswith(source_prefixes) and bool(
            re.search(r"\b(?:19|20)\d{2}\b", text)
        )

    @staticmethod
    def _marker_regex(markers: list[str] | None, fallback: re.Pattern) -> re.Pattern:
        if not markers:
            return fallback
        choices = "|".join(re.escape(marker) for marker in markers)
        return re.compile(rf"^\s*(?:{choices})\s*[:：]?\s*", re.I)

    @staticmethod
    def _compile_patterns(patterns: list[str] | None) -> list[re.Pattern]:
        return [re.compile(pattern, re.I) for pattern in (patterns or [])]

    @staticmethod
    def _matches_any(patterns: list[re.Pattern], text: str) -> bool:
        return any(pattern.match(text) for pattern in patterns)

    def _parse_section_title(
        self, text: str, node: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        node = node or {}
        for pattern in self.SECTION_PATTERNS:
            match = pattern.match(text)
            if not match:
                continue
            marker, title = match.groups()
            marker_core = marker.rstrip(".")
            if marker[0].isdigit() and int(marker_core.split(".")[0]) > 99:
                continue
            if not any(char.isalpha() for char in title):
                continue
            if len(title) > 220 or len(title.split()) > 30:
                continue
            compact_title = re.sub(r"\s+", "", title)
            digit_ratio = sum(char.isdigit() for char in title) / max(
                1, len(compact_title)
            )
            if marker[0].isdigit() and digit_ratio >= 0.15:
                continue
            level = marker_core.count(".") + 1 if marker[0].isdigit() else (
                2 if text.startswith(("（", "(")) else 1
            )
            return {
                "label": self._section_label(marker, text),
                "title": title.strip(),
                "level": level,
                "paragraphs": [],
            }
        if re.match(r"^\d+(?:\.\d+)*\s+", text):
            return None
        if self._normalized_heading(text) in self.CONVENTIONAL_SUBHEADINGS:
            return {"title": text.strip(), "level": 2, "paragraphs": []}
        style = str(node.get("style", "")).strip()
        if style.isdigit() and 1 <= int(style) <= 6 and any(char.isalpha() for char in text):
            return {
                "title": text.strip(),
                "level": int(style),
                "paragraphs": [],
                "_numbered_style_heading": True,
            }
        if node.get("type") == "heading" and text and any(char.isalpha() for char in text):
            return {"title": text.strip(), "level": 1, "paragraphs": []}
        return None

    @staticmethod
    def _split_values(text: str) -> list[str]:
        return [
            value.strip()
            for value in re.split(r"[；;，,、:：]+", text)
            if value.strip()
        ]

    @staticmethod
    def _section_label(marker: str, text: str) -> str:
        if marker and marker[0].isdigit():
            marker = marker.rstrip(".")
            return f"{marker}." if "." not in marker else marker
        stripped = text.strip()
        return stripped[: stripped.find(marker) + len(marker)] if marker in stripped else marker

    @staticmethod
    def _pop_in_section(
        indexes: list[int], items: list[dict[str, Any]], section_index: int
    ) -> int | None:
        for position, item_index in enumerate(indexes):
            if items[item_index].get("section_index", -1) == section_index:
                indexes.pop(position)
                return item_index
        return None

    def _save_flow_image(self, media_path: str, index: int) -> dict[str, str]:
        if not media_path:
            return {"path": ""}
        self.media_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(media_path).suffix.lower() or ".bin"
        path = self.media_dir / f"figure_{index}{suffix}"
        with zipfile.ZipFile(self.docx_path) as archive:
            if media_path not in archive.namelist():
                return {"path": ""}
            path.write_bytes(archive.read(media_path))
        result = {"path": self._relative_path(path)}
        preview = self.tiff_preview_converter.create(path)
        if preview:
            result["preview_path"] = self._relative_path(preview)
        return result

    def _relative_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return (Path(self.media_dir.name) / path.name).as_posix()
