import re
from typing import Any


class ReferenceParser:
    LABEL_RE = re.compile(
        r"^\s*(?P<label>\[\s*\d+\s*\]|\(\s*\d+\s*\)|（\s*\d+\s*）|\d+\s*[.．、])\s*(?P<raw>.*)$"
    )
    DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
    YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
    PAGES_RE = re.compile(r"(?P<fpage>\d+)\s*[-–—]\s*(?P<lpage>\d+)")
    VOLUME_ISSUE_RE = re.compile(r"(?P<volume>\d+)\s*\(\s*(?P<issue>\d+)\s*\)")
    TYPE_RE = re.compile(r"\[(?P<type>[JMCDBR])\]", re.I)

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
            result["fpage"], result["lpage"] = pages.group("fpage"), pages.group("lpage")
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
        clean = re.sub(r"\bdoi\s*:\s*\S+", "", clean, flags=re.I)
        parts = [part.strip(" ,;。") for part in re.split(r"\.\s+", clean) if part.strip()]
        if len(parts) >= 2:
            result["authors"] = [
                item.strip() for item in re.split(r"[,，;；]|\s+and\s+", parts[0], flags=re.I)
                if item.strip()
            ]
            result["article_title"] = parts[1]
        tail = parts[2] if len(parts) >= 3 else ""
        if tail and not re.match(r"^(?:19|20)\d{2}\b", tail):
            source = re.split(r"[,，]\s*(?:19|20)\d{2}", tail, maxsplit=1)[0].strip()
            result["source"] = source
        if not result["publication_type"] and result["source"]:
            result["publication_type"] = "journal"
