from typing import Any

from lxml import etree

from app.services.jats_schema_validator import JatsSchemaValidator


class JatsAutoFixer:
    """Apply deterministic, information-preserving fixes for known Schema errors."""

    XLINK_NS = "http://www.w3.org/1999/xlink"
    JOURNAL_META_ORDER = (
        "journal-id",
        "journal-title-group",
        "contrib-group",
        "aff",
        "aff-alternatives",
        "issn",
        "issn-l",
        "isbn",
        "publisher",
        "notes",
        "self-uri",
        "custom-meta-group",
    )

    def __init__(self, schema_validator: JatsSchemaValidator | None = None, max_rounds: int = 2):
        self.schema_validator = schema_validator or JatsSchemaValidator()
        self.max_rounds = max_rounds

    def fix(
        self, xml: str, initial_schema: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        schema = initial_schema or self.schema_validator.validate(xml)
        report = {
            "attempted": schema.get("jats_schema_valid") is False,
            "applied_fixes": [],
            "remaining_schema_errors": list(schema.get("schema_errors", [])),
            "before_schema_error_count": len(schema.get("schema_errors", [])),
            "after_schema_error_count": len(schema.get("schema_errors", [])),
        }
        if schema.get("jats_schema_valid") is not False:
            return xml, report, schema

        current_xml = xml
        for _ in range(self.max_rounds):
            root = etree.fromstring(current_xml.encode("utf-8"))
            fixes = self._apply_known_fixes(root, schema.get("schema_errors", []))
            if not fixes:
                break
            report["applied_fixes"].extend(fixes)
            current_xml = self._serialize(root)
            schema = self.schema_validator.validate(current_xml)
            if schema.get("jats_schema_valid") is True:
                break

        report["remaining_schema_errors"] = list(schema.get("schema_errors", []))
        report["after_schema_error_count"] = len(schema.get("schema_errors", []))
        return current_xml, report, schema

    def _apply_known_fixes(
        self, root: Any, schema_errors: list[str]
    ) -> list[dict[str, str]]:
        error_text = "\n".join(schema_errors).lower()
        fixes: list[dict[str, str]] = []
        if "graphic" in error_text and ("xlink:href" in error_text or "attribute href" in error_text):
            fixes.extend(self._fix_graphic_href(root))
        if "journal-meta content does not follow" in error_text:
            fixes.extend(self._fix_journal_meta_order(root))
        if "id " in error_text and ("already defined" in error_text or "duplicate" in error_text):
            fixes.extend(self._fix_duplicate_ids(root))
        if "unknown id" in error_text or "dtd_unknown_id" in error_text:
            fixes.extend(self._fix_unknown_idrefs(root))
        return fixes

    def _fix_graphic_href(self, root: Any) -> list[dict[str, str]]:
        fixes = []
        etree.register_namespace("xlink", self.XLINK_NS)
        for index, graphic in enumerate(root.xpath("//*[local-name()='graphic']"), start=1):
            href = graphic.get("href")
            if href and not graphic.get(f"{{{self.XLINK_NS}}}href"):
                graphic.set(f"{{{self.XLINK_NS}}}href", href)
                del graphic.attrib["href"]
                fixes.append({
                    "code": "GRAPHIC_XLINK_HREF",
                    "location": f"graphic[{index}]",
                    "message": "已将 graphic/@href 修复为正式 JATS xlink:href。",
                })
        if fixes:
            etree.cleanup_namespaces(root, top_nsmap={"xlink": self.XLINK_NS})
        return fixes

    def _fix_journal_meta_order(self, root: Any) -> list[dict[str, str]]:
        fixes = []
        order = {name: index for index, name in enumerate(self.JOURNAL_META_ORDER)}
        for index, meta in enumerate(root.xpath("//*[local-name()='journal-meta']"), start=1):
            children = list(meta)
            sorted_children = sorted(
                children,
                key=lambda child: order.get(etree.QName(child).localname, len(order)),
            )
            if children != sorted_children:
                for child in sorted_children:
                    meta.append(child)
                fixes.append({
                    "code": "JOURNAL_META_ORDER",
                    "location": f"journal-meta[{index}]",
                    "message": "已按 JATS DTD 内容模型重新排列 journal-meta 子节点。",
                })
        return fixes

    @staticmethod
    def _fix_duplicate_ids(root: Any) -> list[dict[str, str]]:
        fixes = []
        seen: set[str] = set()
        counters: dict[str, int] = {}
        for element in root.xpath("//*[@id]"):
            current = element.get("id", "")
            if current not in seen:
                seen.add(current)
                continue
            counters[current] = counters.get(current, 1) + 1
            replacement = f"{current}-auto{counters[current]}"
            while replacement in seen:
                counters[current] += 1
                replacement = f"{current}-auto{counters[current]}"
            element.set("id", replacement)
            seen.add(replacement)
            fixes.append({
                "code": "DUPLICATE_ID",
                "location": f"//*[@id='{current}']",
                "message": f"已将重复 ID {current} 修复为 {replacement}。",
            })
        return fixes

    @staticmethod
    def _fix_unknown_idrefs(root: Any) -> list[dict[str, str]]:
        fixes = []
        known_ids = set(root.xpath("//@id"))
        for index, xref in enumerate(root.xpath("//*[local-name()='xref'][@rid]"), start=1):
            original = xref.get("rid", "")
            valid = [rid for rid in original.split() if rid in known_ids]
            if len(valid) == len(original.split()):
                continue
            if valid:
                xref.set("rid", " ".join(valid))
            else:
                parent = xref.getparent()
                position = parent.index(xref)
                content = "".join(xref.itertext())
                tail = xref.tail or ""
                if position == 0:
                    parent.text = (parent.text or "") + content + tail
                else:
                    previous = parent[position - 1]
                    previous.tail = (previous.tail or "") + content + tail
                parent.remove(xref)
            fixes.append({
                "code": "UNKNOWN_IDREF",
                "location": f"xref[{index}]",
                "message": f"Removed unresolved target(s) from xref/@rid: {original}.",
            })
        return fixes

    @staticmethod
    def _serialize(root: Any) -> str:
        content = etree.tostring(root, encoding="unicode", pretty_print=True)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{content}'
