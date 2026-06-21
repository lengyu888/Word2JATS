import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from lxml import etree


class OfficialXmlComparator:
    """Compare generated and official XML by JATS semantics, not global tag counts."""

    METRIC_VERSION = "2.0"
    KEY_TAGS = (
        "article-title",
        "abstract",
        "kwd",
        "sec",
        "fig",
        "table-wrap",
        "disp-formula",
        "ref",
        "xref",
    )
    DIMENSION_WEIGHTS = {
        "metadata": 20,
        "structure": 25,
        "figures_tables": 15,
        "formulas": 10,
        "references": 15,
        "xrefs": 10,
        "compliance": 5,
    }
    SPACE_RE = re.compile(r"\s+")
    PUNCTUATION_RE = re.compile(r"[\s\u3000,.;:!?，。；：！？'\"“”‘’()（）\[\]【】]+")

    def compare(self, generated_xml: str, official_xml_path: Path) -> dict[str, Any]:
        result = self._empty_result(official_xml_path.name)
        if not official_xml_path.is_file():
            result["differences"].append(self._difference(
                "official_xml",
                "Official XML reference file was not found.",
                suggestion="Check the official sample mapping and file path.",
                level="warning",
            ))
            return result

        generated_root, generated_valid = self._parse_xml(generated_xml.encode("utf-8"))
        official_root, official_valid = self._parse_xml(official_xml_path.read_bytes())
        result["generated_xml_valid"] = generated_valid
        result["official_xml_valid"] = official_valid
        result["available"] = generated_root is not None and official_root is not None
        if generated_root is None or official_root is None:
            result["differences"].append(self._difference(
                "xml_parse",
                "Generated XML or official XML could not be parsed.",
                suggestion="Inspect XML syntax before comparing semantic structure.",
                level="error",
            ))
            return result

        generated_facts = self._semantic_facts(generated_root)
        official_facts = self._semantic_facts(official_root)
        result["facts"] = {"generated": generated_facts, "official": official_facts}

        generated_counts = self._key_counts(generated_root)
        official_counts = self._key_counts(official_root)
        result["counts"] = {"generated": generated_counts, "official": official_counts}

        dimensions, recoverable = self._compare_facts(
            generated_facts,
            official_facts,
            generated_valid,
        )
        enriched = self._publisher_enriched_differences(generated_facts, official_facts)
        result["dimensions"] = dimensions
        result["recoverable_differences"] = recoverable
        result["publisher_enriched_differences"] = enriched
        result["similarity_score"] = self._weighted_score(dimensions)
        result["differences"] = [*recoverable, *enriched]
        return result

    def _empty_result(self, official_name: str) -> dict[str, Any]:
        return {
            "available": False,
            "metric_version": self.METRIC_VERSION,
            "official_xml": official_name,
            "generated_xml_valid": False,
            "official_xml_valid": False,
            "similarity_score": 0,
            "dimensions": {},
            "facts": {"generated": {}, "official": {}},
            "counts": {"generated": {}, "official": {}},
            "recoverable_differences": [],
            "publisher_enriched_differences": [],
            "differences": [],
        }

    @staticmethod
    def _parse_xml(content: bytes) -> tuple[Any | None, bool]:
        parser = etree.XMLParser(
            no_network=True,
            resolve_entities=False,
            load_dtd=False,
            remove_comments=True,
        )
        try:
            return etree.fromstring(content, parser), True
        except (etree.XMLSyntaxError, ValueError):
            recovery_parser = etree.XMLParser(
                no_network=True,
                resolve_entities=False,
                load_dtd=False,
                recover=True,
                remove_comments=True,
            )
            try:
                return etree.fromstring(content, recovery_parser), False
            except (etree.XMLSyntaxError, ValueError):
                return None, False

    def _semantic_facts(self, root: Any) -> dict[str, Any]:
        article_meta = self._first(root, "./*[local-name()='front']/*[local-name()='article-meta']")
        journal_meta = self._first(root, "./*[local-name()='front']/*[local-name()='journal-meta']")
        body = self._first(root, "./*[local-name()='body']")
        back = self._first(root, "./*[local-name()='back']")

        sections = self._section_facts(body)
        figures = self._float_facts(body, "fig")
        tables = self._float_facts(body, "table-wrap")
        formulas = self._formula_facts(body)
        references = self._reference_facts(back)
        xrefs = self._xref_facts(body)

        return {
            "title": self._text_at(article_meta, "./*[local-name()='title-group']/*[local-name()='article-title'][1]"),
            "abstract": self._text_at(article_meta, "./*[local-name()='abstract'][1]"),
            "keywords": self._texts_at(article_meta, ".//*[local-name()='kwd']"),
            "authors": self._author_facts(article_meta),
            "affiliations": self._texts_at(article_meta, "./*[local-name()='aff']"),
            "doi": self._text_at(article_meta, "./*[local-name()='article-id'][@pub-id-type='doi'][1]"),
            "journal_id": self._text_at(journal_meta, "./*[local-name()='journal-id'][1]"),
            "section_titles": [item["title"] for item in sections],
            "section_levels": [item["level"] for item in sections],
            "sections": sections,
            "figures": figures,
            "tables": tables,
            "formulas": formulas,
            "references": references,
            "xrefs": xrefs,
        }

    def _section_facts(self, body: Any | None) -> list[dict[str, Any]]:
        if body is None:
            return []
        facts = []

        def visit(parent: Any, level: int) -> None:
            for section in parent.xpath("./*[local-name()='sec']"):
                facts.append({
                    "id": section.get("id", ""),
                    "title": self._text_at(section, "./*[local-name()='title'][1]"),
                    "level": level,
                    "paragraph_count": len(section.xpath("./*[local-name()='p']")),
                })
                visit(section, level + 1)

        visit(body, 1)
        return facts

    def _float_facts(self, body: Any | None, tag: str) -> list[dict[str, Any]]:
        if body is None:
            return []
        return [
            {
                "id": element.get("id", ""),
                "label": self._text_at(element, "./*[local-name()='label'][1]"),
                "caption": self._text_at(element, "./*[local-name()='caption'][1]"),
                "section": self._ancestor_section_title(element),
            }
            for element in body.xpath(f".//*[local-name()='{tag}']")
        ]

    def _formula_facts(self, body: Any | None) -> list[dict[str, Any]]:
        if body is None:
            return []
        return [
            {
                "id": element.get("id", ""),
                "label": self._text_at(element, "./*[local-name()='label'][1]"),
                "text": self._element_text(element),
                "section": self._ancestor_section_title(element),
            }
            for element in body.xpath(".//*[local-name()='disp-formula']")
        ]

    def _reference_facts(self, back: Any | None) -> list[dict[str, Any]]:
        if back is None:
            return []
        references = []
        for element in back.xpath(".//*[local-name()='ref-list']/*[local-name()='ref']"):
            references.append({
                "id": element.get("id", ""),
                "label": self._text_at(element, "./*[local-name()='label'][1]"),
                "text": self._element_text(element),
                "title": self._text_at(element, ".//*[local-name()='element-citation']/*[local-name()='article-title'][1]"),
                "doi": self._text_at(element, ".//*[local-name()='pub-id'][@pub-id-type='doi'][1]"),
                "year": self._text_at(element, ".//*[local-name()='year'][1]"),
            })
        return references

    def _xref_facts(self, body: Any | None) -> list[dict[str, str]]:
        if body is None:
            return []
        facts = []
        for element in body.xpath(".//*[local-name()='xref']"):
            rids = element.get("rid", "").split() or [""]
            text = self._element_text(element)
            for rid in rids:
                facts.append({
                    "type": element.get("ref-type", ""),
                    "rid": rid,
                    "text": text,
                })
        return facts

    def _author_facts(self, article_meta: Any | None) -> list[str]:
        if article_meta is None:
            return []
        authors = []
        for contrib in article_meta.xpath(
            "./*[local-name()='contrib-group']/*[local-name()='contrib'][@contrib-type='author']"
        ):
            surname = self._text_at(contrib, ".//*[local-name()='surname'][1]")
            given = self._text_at(contrib, ".//*[local-name()='given-names'][1]")
            collab = self._text_at(contrib, ".//*[local-name()='collab'][1]")
            value = " ".join(part for part in (given, surname) if part) or collab
            if value:
                authors.append(value)
        return authors

    def _compare_facts(
        self,
        generated: dict[str, Any],
        official: dict[str, Any],
        generated_valid: bool,
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        recoverable: list[dict[str, Any]] = []

        metadata_metrics = {
            "title": self._text_score(generated["title"], official["title"]),
            "abstract": self._text_score(generated["abstract"], official["abstract"]),
            "keywords": self._set_score(generated["keywords"], official["keywords"]),
            "authors": self._fuzzy_set_score(generated["authors"], official["authors"]),
            "affiliations": self._fuzzy_set_score(
                generated["affiliations"], official["affiliations"]
            ),
        }
        structure_metrics = {
            "section_titles": self._heading_sequence_score(
                generated["section_titles"], official["section_titles"]
            ),
            "section_levels": self._sequence_score(
                [str(value) for value in generated["section_levels"]],
                [str(value) for value in official["section_levels"]],
            ),
        }
        figure_table_metrics = {
            "figure_count": self._count_score(generated["figures"], official["figures"]),
            "figure_caption": self._paired_field_score(
                generated["figures"], official["figures"], "caption"
            ),
            "figure_section": self._paired_field_score(
                generated["figures"], official["figures"], "section"
            ),
            "table_count": self._count_score(generated["tables"], official["tables"]),
            "table_caption": self._paired_field_score(
                generated["tables"], official["tables"], "caption"
            ),
            "table_section": self._paired_field_score(
                generated["tables"], official["tables"], "section"
            ),
        }
        formula_metrics = {
            "formula_count": self._count_score(
                generated["formulas"], official["formulas"]
            ),
            "formula_content": self._paired_field_score(
                generated["formulas"], official["formulas"], "text"
            ),
            "formula_section": self._paired_field_score(
                generated["formulas"], official["formulas"], "section"
            ),
        }
        reference_metrics = {
            "references": self._reference_score(
                generated["references"], official["references"]
            ),
        }
        xref_metrics = {
            "xrefs": self._xref_score(generated["xrefs"], official["xrefs"]),
        }

        metric_groups = {
            "metadata": metadata_metrics,
            "structure": structure_metrics,
            "figures_tables": figure_table_metrics,
            "formulas": formula_metrics,
            "references": reference_metrics,
            "xrefs": xref_metrics,
            "compliance": {"xml_well_formed": 1.0 if generated_valid else 0.0},
        }
        dimensions = {}
        for dimension, metrics in metric_groups.items():
            score = round(sum(metrics.values()) / len(metrics) * 100) if metrics else 100
            dimensions[dimension] = {
                "score": score,
                "weight": self.DIMENSION_WEIGHTS[dimension],
                "metrics": {name: round(value * 100) for name, value in metrics.items()},
            }
            for metric, value in metrics.items():
                if value >= 0.999:
                    continue
                generated_value = self._metric_value(metric, generated)
                official_value = self._metric_value(metric, official)
                recoverable.append(self._difference(
                    metric,
                    f"Recoverable {metric} differs from the official JATS reference.",
                    generated=generated_value,
                    official=official_value,
                    suggestion=self._suggestion(metric),
                ))
        return dimensions, recoverable

    def _publisher_enriched_differences(
        self, generated: dict[str, Any], official: dict[str, Any]
    ) -> list[dict[str, Any]]:
        differences = []
        for metric in ("doi", "journal_id"):
            if official.get(metric) and not generated.get(metric):
                differences.append(self._difference(
                    metric,
                    f"Official XML contains {metric}, but the source conversion does not.",
                    generated="",
                    official=official[metric],
                    suggestion="Supply this publisher-enriched value through the correction form or profile.",
                    level="info",
                    category="publisher_enriched",
                ))
        return differences

    def _key_counts(self, root: Any) -> dict[str, int]:
        counter = Counter(etree.QName(element).localname for element in root.iter())
        return {tag: counter.get(tag, 0) for tag in self.KEY_TAGS}

    def _weighted_score(self, dimensions: dict[str, dict[str, Any]]) -> int:
        score = sum(
            dimensions[name]["score"] * weight
            for name, weight in self.DIMENSION_WEIGHTS.items()
        ) / sum(self.DIMENSION_WEIGHTS.values())
        return round(score)

    def _metric_value(self, metric: str, facts: dict[str, Any]) -> Any:
        mapping = {
            "section_titles": facts["section_titles"],
            "section_levels": facts["section_levels"],
            "figures": len(facts["figures"]),
            "tables": len(facts["tables"]),
            "formulas": len(facts["formulas"]),
            "references": len(facts["references"]),
            "xrefs": len(facts["xrefs"]),
            "xml_well_formed": True,
        }
        for prefix, key in (
            ("figure", "figures"),
            ("table", "tables"),
            ("formula", "formulas"),
        ):
            mapping[f"{prefix}_count"] = len(facts[key])
            mapping[f"{prefix}_caption"] = [
                item.get("caption", "") for item in facts[key]
            ]
            mapping[f"{prefix}_content"] = [
                item.get("text", "") for item in facts[key]
            ]
            mapping[f"{prefix}_section"] = [
                item.get("section", "") for item in facts[key]
            ]
        return mapping.get(metric, facts.get(metric))

    @classmethod
    def _text_score(cls, left: str, right: str) -> float:
        left_value = cls._normalize(left)
        right_value = cls._normalize(right)
        if not left_value and not right_value:
            return 1.0
        if not left_value or not right_value:
            return 0.0
        return SequenceMatcher(None, left_value, right_value).ratio()

    @classmethod
    def _set_score(cls, left: list[str], right: list[str]) -> float:
        left_set = {cls._normalize(value) for value in left if cls._normalize(value)}
        right_set = {cls._normalize(value) for value in right if cls._normalize(value)}
        if not left_set and not right_set:
            return 1.0
        if not left_set or not right_set:
            return 0.0
        overlap = len(left_set & right_set)
        precision = overlap / len(left_set)
        recall = overlap / len(right_set)
        return 2 * precision * recall / (precision + recall) if overlap else 0.0

    @classmethod
    def _fuzzy_set_score(cls, left: list[str], right: list[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        remaining = list(right)
        scores = []
        for value in left:
            if not remaining:
                scores.append(0.0)
                continue
            matches = [cls._text_score(value, candidate) for candidate in remaining]
            best_index = max(range(len(matches)), key=matches.__getitem__)
            scores.append(matches[best_index])
            remaining.pop(best_index)
        scores.extend([0.0] * len(remaining))
        return sum(scores) / len(scores)

    @classmethod
    def _sequence_score(cls, left: list[str], right: list[str]) -> float:
        left_values = [cls._normalize(value) for value in left]
        right_values = [cls._normalize(value) for value in right]
        if not left_values and not right_values:
            return 1.0
        return SequenceMatcher(None, left_values, right_values).ratio()

    @classmethod
    def _heading_sequence_score(cls, left: list[str], right: list[str]) -> float:
        left_values = [cls._normalize_heading(value) for value in left]
        right_values = [cls._normalize_heading(value) for value in right]
        if not left_values and not right_values:
            return 1.0
        if not left_values or not right_values:
            return 0.0
        matcher = SequenceMatcher(None, left_values, right_values)
        exact_ratio = matcher.ratio()
        paired = min(len(left_values), len(right_values))
        fuzzy_ratio = sum(
            SequenceMatcher(None, left_values[index], right_values[index]).ratio()
            for index in range(paired)
        ) / max(len(left_values), len(right_values))
        return max(exact_ratio, fuzzy_ratio)

    @classmethod
    def _object_score(
        cls, left: list[dict[str, Any]], right: list[dict[str, Any]], text_key: str
    ) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        count_score = min(len(left), len(right)) / max(len(left), len(right))
        matched = min(len(left), len(right))
        text_score = sum(
            cls._text_score(left[index].get(text_key, ""), right[index].get(text_key, ""))
            for index in range(matched)
        ) / matched
        return (count_score + text_score) / 2

    @staticmethod
    def _count_score(left: list[Any], right: list[Any]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return min(len(left), len(right)) / max(len(left), len(right))

    @classmethod
    def _paired_field_score(
        cls, left: list[dict[str, Any]], right: list[dict[str, Any]], field: str
    ) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        matched = min(len(left), len(right))
        score = sum(
            cls._text_score(left[index].get(field, ""), right[index].get(field, ""))
            for index in range(matched)
        )
        return score / max(len(left), len(right))

    @classmethod
    def _xref_score(cls, left: list[dict[str, str]], right: list[dict[str, str]]) -> float:
        left_values = [cls._xref_key(item) for item in left]
        right_values = [cls._xref_key(item) for item in right]
        return cls._multiset_f1(left_values, right_values)

    @classmethod
    def _reference_score(
        cls, left: list[dict[str, Any]], right: list[dict[str, Any]]
    ) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        matched = min(len(left), len(right))
        pair_scores = []
        for index in range(matched):
            generated = left[index]
            official = right[index]
            component_scores = [
                cls._text_score(
                    cls._reference_label(generated), cls._reference_label(official)
                )
            ]
            for field in ("doi", "year", "title"):
                if generated.get(field) or official.get(field):
                    component_scores.append(
                        cls._text_score(generated.get(field, ""), official.get(field, ""))
                    )
            text_score = cls._token_score(generated.get("text", ""), official.get("text", ""))
            pair_scores.append(max(text_score, sum(component_scores) / len(component_scores)))
        count_score = matched / max(len(left), len(right))
        return (count_score + sum(pair_scores) / max(len(left), len(right))) / 2

    @classmethod
    def _token_score(cls, left: str, right: str) -> float:
        left_tokens = set(re.findall(r"[\w]+", left.casefold(), re.UNICODE))
        right_tokens = set(re.findall(r"[\w]+", right.casefold(), re.UNICODE))
        if not left_tokens and not right_tokens:
            return 1.0
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = len(left_tokens & right_tokens)
        precision = overlap / len(left_tokens)
        recall = overlap / len(right_tokens)
        return 2 * precision * recall / (precision + recall) if overlap else 0.0

    @classmethod
    def _multiset_f1(cls, left: list[str], right: list[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        left_counts = Counter(left)
        right_counts = Counter(right)
        overlap = sum((left_counts & right_counts).values())
        precision = overlap / len(left)
        recall = overlap / len(right)
        return 2 * precision * recall / (precision + recall) if overlap else 0.0

    @classmethod
    def _xref_key(cls, item: dict[str, str]) -> str:
        number = re.search(r"\d+", item.get("rid", "")) or re.search(
            r"\d+", item.get("text", "")
        )
        ordinal = number.group(0) if number else cls._normalize(item.get("text", ""))
        return f"{item.get('type', '')}:{ordinal}"

    @staticmethod
    def _reference_label(reference: dict[str, Any]) -> str:
        match = re.search(r"\d+", reference.get("label", ""))
        return match.group(0) if match else reference.get("label", "")

    @classmethod
    def _normalize(cls, value: Any) -> str:
        text = cls.SPACE_RE.sub(" ", str(value or "")).strip().casefold()
        return cls.PUNCTUATION_RE.sub("", text)

    @classmethod
    def _normalize_heading(cls, value: Any) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^[●•\-–—]+\s*", "", text)
        text = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", text)
        return cls._normalize(text)

    @staticmethod
    def _first(parent: Any | None, xpath: str) -> Any | None:
        if parent is None:
            return None
        matches = parent.xpath(xpath)
        return matches[0] if matches else None

    @classmethod
    def _text_at(cls, parent: Any | None, xpath: str) -> str:
        element = cls._first(parent, xpath)
        return cls._element_text(element)

    @classmethod
    def _texts_at(cls, parent: Any | None, xpath: str) -> list[str]:
        if parent is None:
            return []
        return [value for element in parent.xpath(xpath) if (value := cls._element_text(element))]

    @classmethod
    def _element_text(cls, element: Any | None) -> str:
        if element is None:
            return ""
        parts = [part.strip() for part in element.itertext() if part.strip()]
        return cls.SPACE_RE.sub(" ", " ".join(parts)).strip()

    def _ancestor_section_title(self, element: Any) -> str:
        sections = element.xpath("ancestor::*[local-name()='sec'][1]")
        return self._text_at(sections[0], "./*[local-name()='title'][1]") if sections else ""

    @staticmethod
    def _difference(
        metric: str,
        message: str,
        *,
        generated: Any = None,
        official: Any = None,
        suggestion: str = "Review the parser classification and generated JATS structure.",
        level: str = "warning",
        category: str = "recoverable",
    ) -> dict[str, Any]:
        return {
            "level": level,
            "category": category,
            "metric": metric,
            "generated": generated,
            "official": official,
            "message": message,
            "suggestion": suggestion,
        }

    @staticmethod
    def _suggestion(metric: str) -> str:
        suggestions = {
            "title": "Review front-matter title detection.",
            "abstract": "Review abstract markers and continuation paragraphs.",
            "keywords": "Review keyword markers, adjacent values, and separators.",
            "authors": "Review contributor detection and name normalization.",
            "affiliations": "Review affiliation markers and author-affiliation grouping.",
            "section_titles": "Review heading detection, exclusions, and document order.",
            "section_levels": "Recover heading levels and generate nested sec elements.",
            "figures": "Review media classification, captions, and section binding.",
            "tables": "Review table captions, extraction, and section binding.",
            "formulas": "Prefer OMML evidence and reduce plain-text formula false positives.",
            "references": "Review reference boundaries, continuations, and structured parsing.",
            "xrefs": "Expand compound references and verify every rid target.",
            "xml_well_formed": "Repair XML syntax before structural comparison.",
        }
        if metric.startswith("figure_"):
            return suggestions["figures"]
        if metric.startswith("table_"):
            return suggestions["tables"]
        if metric.startswith("formula_"):
            return suggestions["formulas"]
        return suggestions.get(metric, "Review the generated JATS structure.")
