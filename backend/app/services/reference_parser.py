import re
from typing import Any


class ReferenceParser:
    LABEL_RE = re.compile(
        r"^\s*(?P<label>\[\s*\d+\s*\]|［\s*\d+\s*］|\(\s*\d+\s*\)|"
        r"（\s*\d+\s*）|\d+\s*[.)．、])\s*(?P<raw>.*)$"
    )
    DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
    YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
    PAGES_RE = re.compile(r"(?P<fpage>\d+)\s*[-\u2013\u2014]\s*(?P<lpage>\d+)")
    VOLUME_ISSUE_RE = re.compile(r"(?P<volume>\d+)\s*\(\s*(?P<issue>[^)]+)\s*\)")
    TYPE_RE = re.compile(r"\[(?P<type>[JMCDBR])\]", re.I)
    JOURNAL_TAIL_RE = re.compile(
        r"^(?P<source>.+?)\s*[,;]?\s*"
        r"(?P<year>(?:19|20)\d{2})"
        r"(?:\s*[,;]\s*(?P<volume>\d+))?"
        r"(?:\s*\(\s*(?P<issue>[^)]+)\s*\))?"
        r"(?:\s*[:：]\s*(?P<fpage>\d+)\s*[-\u2013\u2014]\s*(?P<lpage>\d+))?"
        r"\.?\s*$"
    )

    COMMA_JOURNAL_TAIL_RE = re.compile(
        r"^(?P<head>.+?),\s*"
        r"(?P<source>[^,]+?),\s*"
        r"(?P<volume>\d+)\s*"
        r"\(\s*(?P<year>(?:19|20)\d{2})\s*\)\s*"
        r"(?P<fpage>\d+)\s*[-\u2013\u2014]\s*(?P<lpage>\d+)"
        r"\.?\s*$"
    )

    TYPE_MAP = {
        "J": "journal",
        "M": "book",
        "C": "conference",
        "D": "thesis",
        "B": "book",
        "R": "report",
    }

    def parse(self, text: str, index: int = 1) -> dict[str, Any]:
        match = self.LABEL_RE.match(text)
        label = match.group("label").strip() if match else ""
        raw = match.group("raw").strip() if match else text.strip()
        result: dict[str, Any] = {
            "id": f"ref{index}",
            "label": label,
            "raw": raw,
            "mixed_citation": raw,
            "authors": [],
            "article_title": "",
            "source": "",
            "year": "",
            "volume": "",
            "issue": "",
            "fpage": "",
            "lpage": "",
            "doi": "",
            "publication_type": "",
            "parse_confidence": 0.0,
        }
        self._parse_identifiers(raw, result)
        self._parse_main_parts(raw, result)
        populated = sum(
            bool(result[field])
            for field in (
                "authors", "article_title", "source", "year", "volume",
                "issue", "fpage", "lpage", "doi", "publication_type",
            )
        )
        result["parse_confidence"] = round(min(1.0, populated / 7), 2)
        return result

    def _parse_identifiers(self, raw: str, result: dict[str, Any]) -> None:
        doi = self.DOI_RE.search(raw)
        year = self.YEAR_RE.search(raw)
        pages = self.PAGES_RE.search(raw)
        volume_issue = self.VOLUME_ISSUE_RE.search(raw)
        publication_type = self.TYPE_RE.search(raw)
        if doi:
            result["doi"] = doi.group(0).rstrip(".")
        if year:
            result["year"] = year.group(0)
        if pages:
            result["fpage"], result["lpage"] = (
                pages.group("fpage"), pages.group("lpage")
            )
        if volume_issue:
            result["volume"], result["issue"] = (
                volume_issue.group("volume"), volume_issue.group("issue")
            )
        if publication_type:
            result["publication_type"] = self.TYPE_MAP.get(
                publication_type.group("type").upper(), "other"
            )

    @staticmethod
    def _parse_main_parts(raw: str, result: dict[str, Any]) -> None:
        clean = re.sub(r"\[[JMCDBR]\]", "", raw, flags=re.I)
        clean = re.sub(
            r"\bdoi\s*:\s*(?:https?://(?:dx\.)?doi\.org/)?\S+",
            "",
            clean,
            flags=re.I,
        )
        clean = re.sub(r"https?://(?:dx\.)?doi\.org/\S+", "", clean, flags=re.I)
        if ReferenceParser._parse_comma_separated_journal(clean, result):
            return
        parts = [
            part.strip(" ,;。")
            for part in re.split(r"\.\s+", clean)
            if part.strip(" ,;。")
        ]
        if len(parts) >= 2:
            result["authors"] = ReferenceParser._split_authors(parts[0])
            result["article_title"] = parts[1].strip(" ,;。")
        tail = " ".join(parts[2:]) if len(parts) >= 3 else ""
        if tail:
            ReferenceParser._parse_journal_tail(tail, result)
        if not result["publication_type"] and result["source"]:
            result["publication_type"] = "journal"

    @staticmethod
    def _parse_comma_separated_journal(clean: str, result: dict[str, Any]) -> bool:
        match = ReferenceParser.COMMA_JOURNAL_TAIL_RE.match(clean.strip())
        if not match:
            return False
        head_parts = [
            part.strip()
            for part in match.group("head").split(",")
            if part.strip()
        ]
        authors: list[str] = []
        title_parts: list[str] = []
        for index, part in enumerate(head_parts):
            if not title_parts and ReferenceParser._looks_like_author_segment(part):
                authors.append(part)
                continue
            title_parts = head_parts[index:]
            break
        if not title_parts:
            return False
        if authors:
            result["authors"] = authors
        result["article_title"] = ", ".join(title_parts).strip(" ,;.")
        result["source"] = match.group("source").strip(" ,;.")
        for field in ("year", "volume", "fpage", "lpage"):
            value = match.group(field)
            if value:
                result[field] = value.strip()
        result["publication_type"] = result.get("publication_type") or "journal"
        return bool(result["article_title"] and result["source"])

    @staticmethod
    def _looks_like_author_segment(value: str) -> bool:
        text = value.strip()
        if re.fullmatch(r"et\s+al\.?", text, flags=re.I):
            return True
        if len(text.split()) > 6:
            return False
        return bool(re.search(r"(?:^|\s)[A-Z]{1,4}\.?$", text))

    @staticmethod
    def _split_authors(value: str) -> list[str]:
        authors = [
            item.strip()
            for item in re.split(r"[;,，；]|(?:\s+and\s+)", value, flags=re.I)
            if item.strip()
        ]
        return authors

    @staticmethod
    def _parse_journal_tail(tail: str, result: dict[str, Any]) -> None:
        tail = tail.strip(" ,;。.")
        match = ReferenceParser.JOURNAL_TAIL_RE.match(tail)
        if match:
            result["source"] = match.group("source").strip(" ,;.")
            for field in ("year", "volume", "issue", "fpage", "lpage"):
                value = match.group(field)
                if value:
                    result[field] = value.strip()
            return
        if not re.match(r"^(?:19|20)\d{2}\b", tail):
            source = re.split(r"[,，]\s*(?:19|20)\d{2}", tail, maxsplit=1)[0]
            result["source"] = source.strip(" ,;。.")
