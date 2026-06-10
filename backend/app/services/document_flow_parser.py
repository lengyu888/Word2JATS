import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree


class DocumentFlowParser:
    """Read the DOCX body XML and expose paragraphs and tables in real order."""

    NS = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    SECTION_RE = re.compile(
        r"^(?:\d+(?:\.\d+)*[\s、.]+.+|[一二三四五六七八九十]+、\s*.+|[（(][一二三四五六七八九十]+[）)]\s*.+)$"
    )
    FIGURE_RE = re.compile(
        r"^\s*(?:图\s*\d+(?:\s*[-－—.]\s*\d+)*|fig(?:ure)?\.?\s*\d+(?:\s*[-.]\s*\d+)*)"
        r"(?:\s+|[:：])?.*$",
        re.I,
    )
    TABLE_RE = re.compile(
        r"^\s*(?:表\s*\d+(?:\s*[-－—.]\s*\d+)*|table\s*\d+(?:\s*[-.]\s*\d+)*)"
        r"(?:\s+|[:：])?.*$",
        re.I,
    )
    LIST_RE = re.compile(r"^\s*(?:[（(]\d+[）)]|\d+[）)]|[-•·])\s*")
    FORMULA_RE = re.compile(
        r"(=|≈|≤|≥|∑|∫|√|[αβγλμσ]|\\?frac|\\?sqrt|\blim\b|\blog\b|\bsin\b|\bcos\b)",
        re.I,
    )

    def __init__(self, docx_path: str | Path):
        self.docx_path = Path(docx_path)

    def parse(self) -> list[dict[str, Any]]:
        with zipfile.ZipFile(self.docx_path) as archive:
            document = etree.fromstring(archive.read("word/document.xml"))
            relationships = self._read_relationships(archive)

        body = document.find("w:body", self.NS)
        if body is None:
            return []
        nodes = []
        for element in body:
            if element.tag == f"{{{self.NS['w']}}}p":
                nodes.extend(self._parse_paragraph(element, relationships))
            elif element.tag == f"{{{self.NS['w']}}}tbl":
                nodes.append({"type": "table", "rows": self._parse_table(element)})
        for index, node in enumerate(nodes):
            node["flow_index"] = index
        return nodes

    def _parse_paragraph(
        self, paragraph: Any, relationships: dict[str, str]
    ) -> list[dict[str, Any]]:
        text = self._text(paragraph)
        style = self._attribute(paragraph, ".//w:pPr/w:pStyle", "val")
        base = {
            "text": text,
            "style": style,
            "alignment": self._attribute(paragraph, ".//w:pPr/w:jc", "val"),
            "bold": bool(paragraph.xpath(".//w:rPr/w:b", namespaces=self.NS)),
            "font_size": self._font_size(paragraph),
        }
        embeds = paragraph.xpath(".//a:blip/@r:embed", namespaces=self.NS)
        if embeds:
            return [
                {
                    **base,
                    "type": "image",
                    "relationship_id": embed,
                    "media_path": relationships.get(embed, ""),
                }
                for embed in embeds
            ]
        if paragraph.xpath(".//m:oMath | .//m:oMathPara", namespaces=self.NS):
            return [{**base, "type": "formula", "formula_type": "omml"}]
        return [{**base, "type": self._classify_paragraph(paragraph, text, style)}]

    def _classify_paragraph(self, paragraph: Any, text: str, style: str) -> str:
        style_lower = style.lower()
        if style_lower == "title":
            return "title"
        if self.FIGURE_RE.match(text):
            return "figure_caption"
        if self.TABLE_RE.match(text):
            return "table_caption"
        if self.SECTION_RE.match(text) or style_lower.startswith("heading"):
            return "heading"
        if paragraph.xpath(".//w:pPr/w:numPr", namespaces=self.NS) or self.LIST_RE.match(text):
            return "list"
        if (
            "equation" in style_lower
            or "公式" in style
            or (len(text) <= 60 and bool(self.FORMULA_RE.search(text)))
        ):
            return "formula"
        return "paragraph"

    def _parse_table(self, table: Any) -> list[list[str]]:
        return [
            [self._text(cell).strip() for cell in row.findall("w:tc", self.NS)]
            for row in table.findall("w:tr", self.NS)
        ]

    def _read_relationships(self, archive: zipfile.ZipFile) -> dict[str, str]:
        path = "word/_rels/document.xml.rels"
        if path not in archive.namelist():
            return {}
        root = etree.fromstring(archive.read(path))
        relationships = {}
        for relationship in root.findall("pr:Relationship", self.NS):
            if relationship.get("TargetMode") == "External":
                continue
            relationship_id = relationship.get("Id", "")
            target = relationship.get("Target", "")
            relationships[relationship_id] = posixpath.normpath(posixpath.join("word", target))
        return relationships

    @classmethod
    def _text(cls, element: Any) -> str:
        return "".join(element.xpath(".//w:t/text() | .//m:t/text()", namespaces=cls.NS)).strip()

    @classmethod
    def _attribute(cls, element: Any, xpath: str, name: str) -> str:
        values = element.xpath(f"{xpath}/@w:{name}", namespaces=cls.NS)
        return values[0] if values else ""

    @classmethod
    def _font_size(cls, paragraph: Any) -> float:
        values = paragraph.xpath(".//w:rPr/w:sz/@w:val", namespaces=cls.NS)
        sizes = [float(value) / 2 for value in values if value.isdigit()]
        return max(sizes, default=0.0)
