import re
from typing import Any

from lxml import etree


class XrefResolver:
    """Recognize body references and write JATS mixed-content paragraphs."""

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
                r"(?P<text>(?:式|公式)\s*[（(]\s*(?P<zh>\d+)\s*[）)]|"
                r"Eq\.?\s*\(\s*(?P<en>\d+)\s*\))",
                re.I,
            ),
            "eq",
        ),
        (
            "bibr",
            re.compile(r"(?P<text>\[\s*(?P<numbers>\d+(?:\s*[-,，]\s*\d+)*)\s*\])"),
            "ref",
        ),
    )

    def resolve(self, text: str) -> list[dict[str, Any]]:
        matches = []
        for ref_type, pattern, prefix in self.PATTERNS:
            for match in pattern.finditer(text):
                numbers = (
                    self._expand_reference_numbers(match.group("numbers"))
                    if ref_type == "bibr"
                    else [int(match.group("zh") or match.group("en"))]
                )
                matches.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group("text"),
                    "ref_type": ref_type,
                    "rid": " ".join(f"{prefix}{number}" for number in numbers),
                })
        matches.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
        resolved = []
        cursor = -1
        for item in matches:
            if item["start"] >= cursor:
                resolved.append(item)
                cursor = item["end"]
        return resolved

    def append_mixed_content(self, element: Any, text: str) -> None:
        cursor = 0
        previous = None
        for match in self.resolve(text):
            plain_text = text[cursor:match["start"]]
            if previous is None:
                element.text = plain_text
            else:
                previous.tail = plain_text
            previous = etree.SubElement(
                element,
                "xref",
                attrib={"ref-type": match["ref_type"], "rid": match["rid"]},
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
        numbers = []
        for part in re.split(r"[,，]", value):
            part = part.strip()
            if "-" in part:
                start, end = (int(item.strip()) for item in part.split("-", 1))
                step = 1 if end >= start else -1
                numbers.extend(range(start, end + step, step))
            elif part:
                numbers.append(int(part))
        return list(dict.fromkeys(numbers))
