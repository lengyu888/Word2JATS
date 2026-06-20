from collections import Counter
from pathlib import Path
from typing import Any

from lxml import etree


class OfficialXmlComparator:
    """Compare generated JATS XML against an official reference XML."""

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

    def compare(self, generated_xml: str, official_xml_path: Path) -> dict[str, Any]:
        result: dict[str, Any] = {
            "available": False,
            "official_xml": official_xml_path.name,
            "generated_xml_valid": False,
            "official_xml_valid": False,
            "similarity_score": 0,
            "counts": {"generated": {}, "official": {}},
            "differences": [],
        }
        if not official_xml_path.is_file():
            result["differences"].append({
                "level": "warning",
                "metric": "official_xml",
                "message": "未找到官方 XML 结果文件。",
            })
            return result

        generated_root, generated_valid = self._parse_xml(generated_xml.encode("utf-8"))
        official_root, official_valid = self._parse_xml(official_xml_path.read_bytes())
        result["available"] = generated_root is not None and official_root is not None
        result["generated_xml_valid"] = generated_valid
        result["official_xml_valid"] = official_valid
        if generated_root is None or official_root is None:
            result["differences"].append({
                "level": "error",
                "metric": "xml_parse",
                "message": "生成 XML 或官方 XML 无法解析，无法完成结构对比。",
            })
            return result

        generated_counts = self._key_counts(generated_root)
        official_counts = self._key_counts(official_root)
        result["counts"] = {"generated": generated_counts, "official": official_counts}
        result["similarity_score"] = self._score_counts(generated_counts, official_counts)
        result["differences"] = self._differences(generated_counts, official_counts)
        return result

    @staticmethod
    def _parse_xml(content: bytes) -> tuple[Any | None, bool]:
        try:
            return etree.fromstring(content, etree.XMLParser(no_network=True)), True
        except (etree.XMLSyntaxError, ValueError):
            try:
                return etree.fromstring(content, etree.XMLParser(no_network=True, recover=True)), False
            except (etree.XMLSyntaxError, ValueError):
                return None, False

    def _key_counts(self, root: Any) -> dict[str, int]:
        counter = Counter()
        for element in root.iter():
            counter[etree.QName(element).localname] += 1
        return {tag: counter.get(tag, 0) for tag in self.KEY_TAGS}

    @staticmethod
    def _score_counts(generated: dict[str, int], official: dict[str, int]) -> int:
        scores = []
        for tag, official_count in official.items():
            generated_count = generated.get(tag, 0)
            if official_count == generated_count:
                scores.append(1.0)
            elif official_count == 0:
                scores.append(0.0 if generated_count else 1.0)
            else:
                scores.append(max(0.0, 1 - abs(generated_count - official_count) / official_count))
        return round(sum(scores) / len(scores) * 100) if scores else 0

    @staticmethod
    def _differences(generated: dict[str, int], official: dict[str, int]) -> list[dict[str, Any]]:
        differences = []
        for tag, official_count in official.items():
            generated_count = generated.get(tag, 0)
            if generated_count != official_count:
                differences.append({
                    "level": "warning",
                    "metric": tag,
                    "generated": generated_count,
                    "official": official_count,
                    "message": f"{tag} 数量与官方结果不同：生成 {generated_count}，官方 {official_count}。",
                })
        return differences
