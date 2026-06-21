import re
from typing import Any

from lxml import etree


class XrefResolver:
    """Recognize body references and write JATS mixed-content paragraphs."""

    WORD_NUMBERS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    }
    NUMBER_EXPR = r"\d+(?:\s*[-\u2013\u2014]\s*\d+|(?:\s*(?:,|and|&)\s*\d+)+)"
    COMPOUND_PATTERNS = (
        (
            "fig",
            re.compile(
                rf"(?P<text>(?:Figs?|Figures?)\.?\s+(?P<numbers>{NUMBER_EXPR}))",
                re.I,
            ),
            "fig",
        ),
        (
            "table",
            re.compile(rf"(?P<text>Tables?\s+(?P<numbers>{NUMBER_EXPR}))", re.I),
            "tab",
        ),
        (
            "disp-formula",
            re.compile(
                r"(?P<text>Eqs?\.?\s+(?P<numbers>\(\s*\d+\s*\)(?:\s*[-\u2013\u2014]\s*\(\s*\d+\s*\)|(?:\s*(?:,|and|&)\s*\(\s*\d+\s*\))+)))",
                re.I,
            ),
            "eq",
        ),
    )
    WORD_TABLE_RE = re.compile(
        r"(?P<text>Table\s+(?P<word>" + "|".join(WORD_NUMBERS) + r"))\b", re.I
    )
    PATTERNS = (
        (
            "fig",
            re.compile(r"(?P<text>图\s*(?P<zh>\d+)|(?:Fig(?:ure)?\.?)\s*(?P<en>\d+))", re.I),
            "fig",
        ),
        (
            "table",
            re.compile(r"(?P<text>表\s*(?P<zh>\d+)|Table\s+(?P<en>\d+))", re.I),
            "tab",
        ),
        (
            "disp-formula",
            re.compile(
                r"(?P<text>(?:式|公式)\s*[（(]\s*(?P<zh>\d+)\s*[）)]|Eq\.?\s*\(\s*(?P<en>\d+)\s*\))",
                re.I,
            ),
            "eq",
        ),
        (
            "bibr",
            re.compile(
                r"(?P<text>\[\s*(?P<numbers>\d+(?:\s*[-\u2013\u2014,，]\s*\d+)*)\s*\])"
            ),
            "ref",
        ),
    )

    def resolve(self, text: str) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for match in self.WORD_TABLE_RE.finditer(text):
            number = self.WORD_NUMBERS[match.group("word").casefold()]
            matches.append(self._match_item(match, "table", f"tab{number}"))
        for ref_type, pattern, prefix in self.COMPOUND_PATTERNS:
            for match in pattern.finditer(text):
                numbers = self._expand_numbers(match.group("numbers"))
                matches.append(self._match_item(
                    match, ref_type, " ".join(f"{prefix}{number}" for number in numbers)
                ))
        for ref_type, pattern, prefix in self.PATTERNS:
            for match in pattern.finditer(text):
                numbers = (
                    self._expand_reference_numbers(match.group("numbers"))
                    if ref_type == "bibr"
                    else [int(match.group("zh") or match.group("en"))]
                )
                matches.append(self._match_item(
                    match, ref_type, " ".join(f"{prefix}{number}" for number in numbers)
                ))
        matches.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
        resolved = []
        cursor = -1
        for item in matches:
            if item["start"] >= cursor:
                resolved.append(item)
                cursor = item["end"]
        return resolved

    @staticmethod
    def _match_item(match: Any, ref_type: str, rid: str) -> dict[str, Any]:
        return {
            "start": match.start(), "end": match.end(), "text": match.group("text"),
            "ref_type": ref_type, "rid": rid,
        }

    def append_mixed_content(
        self, element: Any, text: str, allowed_ids: set[str] | None = None
    ) -> None:
        cursor = 0
        previous = None
        for match in self.resolve(text):
            if allowed_ids is not None:
                valid_ids = [rid for rid in match["rid"].split() if rid in allowed_ids]
                if not valid_ids:
                    continue
                match = {**match, "rid": " ".join(valid_ids)}
            plain_text = text[cursor:match["start"]]
            if previous is None:
                element.text = plain_text
            else:
                previous.tail = plain_text
            previous = etree.SubElement(
                element, "xref", attrib={"ref-type": match["ref_type"], "rid": match["rid"]}
            )
            previous.text = match["text"]
            cursor = match["end"]
        remainder = text[cursor:]
        if previous is None:
            element.text = remainder
        else:
            previous.tail = remainder

    @staticmethod
    def _expand_reference_numbers(value: str) -> list[int]:
        normalized = (
            value.replace("\u2013", "-").replace("\u2014", "-").replace("，", ",")
        )
        numbers = []
        for part in normalized.split(","):
            part = part.strip()
            if "-" in part:
                start, end = (int(item.strip()) for item in part.split("-", 1))
                step = 1 if end >= start else -1
                numbers.extend(range(start, end + step, step))
            elif part:
                numbers.append(int(part))
        return list(dict.fromkeys(numbers))

    @staticmethod
    def _expand_numbers(value: str) -> list[int]:
        normalized = re.sub(r"[()]", "", value)
        normalized = re.sub(r"\s+(?:and|&)\s+", ",", normalized, flags=re.I)
        return XrefResolver._expand_reference_numbers(normalized)
