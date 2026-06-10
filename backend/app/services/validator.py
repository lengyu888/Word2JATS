from typing import Any

from lxml import etree
from app.services.jats_schema_validator import JatsSchemaValidator


class ArticleValidator:
    def __init__(self, schema_validator: JatsSchemaValidator | None = None):
        self.schema_validator = schema_validator or JatsSchemaValidator()

    def validate(
        self,
        article: dict[str, Any],
        xml: str,
        schema_result: dict[str, Any] | None = None,
        auto_fix: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        xref_checks: list[str] = []
        self._validate_required_content(article, errors)
        self._validate_quality(article, warnings)
        self._validate_xml(xml, errors, warnings, xref_checks)
        schema = schema_result or self.schema_validator.validate(xml)
        business_rules = {
            "passed": not errors,
            "errors": list(errors),
            "warnings": list(warnings),
        }
        return {
            # Keep the legacy aggregate status stable across environments.
            # Formal JATS conformance is reported separately by jats_schema_valid.
            "passed": not errors and schema["xml_well_formed"],
            "errors": errors,
            "warnings": warnings,
            "schema_errors": schema["schema_errors"],
            "xref_checks": xref_checks,
            "xml_well_formed": schema["xml_well_formed"],
            "jats_schema_valid": schema["jats_schema_valid"],
            "schema_file": schema["schema_file"],
            "business_rules": business_rules,
            "auto_fix": auto_fix or {
                "attempted": False,
                "applied_fixes": [],
                "remaining_schema_errors": list(schema["schema_errors"]),
                "before_schema_error_count": len(schema["schema_errors"]),
                "after_schema_error_count": len(schema["schema_errors"]),
            },
        }

    @staticmethod
    def _validate_required_content(article: dict[str, Any], errors: list[str]) -> None:
        if not article.get("title", "").strip():
            errors.append("标题不能为空。")
        if not article.get("abstract", "").strip():
            errors.append("摘要不能为空。")
        if not article.get("keywords"):
            errors.append("关键词不能为空。")
        if not article.get("sections"):
            errors.append("至少需要一个章节。")

    @staticmethod
    def _validate_quality(article: dict[str, Any], warnings: list[str]) -> None:
        authors = article.get("authors", [])
        affiliations = article.get("affiliations", [])
        references = article.get("references", [])
        keywords = article.get("keywords", [])

        if not authors:
            warnings.append("作者为空，建议补充作者信息。")
        if not affiliations:
            warnings.append("单位为空，建议补充作者单位。")
        if not references:
            warnings.append("参考文献为空，建议补充参考文献。")

        for author in authors:
            if not author.get("orcid", "").strip():
                warnings.append(f"作者 {author.get('name', '未命名作者')} 缺少 ORCID。")
        for figure in article.get("figures", []):
            if not figure.get("caption", "").strip():
                warnings.append(f"图片 {figure.get('id', '未命名图片')} 缺少图题。")
        for index, table in enumerate(article.get("tables", []), start=1):
            table_id = table.get("id") or index
            if not table.get("caption", "").strip():
                warnings.append(f"表格 {table_id} 缺少表题。")
            if not table.get("rows"):
                warnings.append(f"表格 {table_id} 没有数据行。")
        for index, formula in enumerate(article.get("formulas", []), start=1):
            content = (
                formula.get("latex")
                or formula.get("content")
                or formula.get("tex")
                or formula.get("plain_text")
                or ""
            )
            if not content.strip():
                warnings.append(f"公式 {formula.get('id') or index} 内容为空。")
            if formula.get("type") == "omml" and not formula.get("mathml", "").strip():
                warnings.append(
                    f"公式 {formula.get('id') or index} 的 OMML 无法转换为 MathML，已保留文本回退。"
                )
        for section in article.get("sections", []):
            if not section.get("paragraphs"):
                warnings.append(f"章节“{section.get('title', '未命名章节')}”没有正文段落。")
        if len(keywords) < 3:
            warnings.append("关键词少于 3 个，建议补充关键词。")

    @staticmethod
    def _validate_xml(
        xml: str, errors: list[str], warnings: list[str], xref_checks: list[str]
    ) -> None:
        try:
            root = etree.fromstring(xml.encode("utf-8"))
        except (etree.XMLSyntaxError, ValueError) as exc:
            errors.append(f"XML 无法解析：{exc}")
            return

        required_nodes = (
            ("journal-meta", "缺少 JATS journal-meta 节点。"),
            ("article-meta", "缺少 JATS article-meta 节点。"),
            ("title-group", "缺少 JATS title-group 节点。"),
            ("contrib-group", "缺少 JATS contrib-group 节点。"),
            ("body", "缺少 JATS body 节点。"),
            ("back", "缺少 JATS back 节点。"),
        )
        for node_name, message in required_nodes:
            if not root.xpath(f"//*[local-name()='{node_name}']"):
                errors.append(message)

        ArticleValidator._validate_xrefs(root, warnings, xref_checks)

    @staticmethod
    def _validate_xrefs(root: Any, warnings: list[str], xref_checks: list[str]) -> None:
        ids = set(root.xpath("//@id"))
        xrefs = root.xpath(
            "//body//xref[@ref-type='fig' or @ref-type='table' or "
            "@ref-type='disp-formula' or @ref-type='bibr']"
        )
        if not xrefs:
            xref_checks.append("未检测到正文交叉引用。")
            return
        for xref in xrefs:
            rid = xref.get("rid", "")
            missing = [target for target in rid.split() if target not in ids]
            if missing:
                for target in missing:
                    message = f"交叉引用目标不存在：{target}。"
                    if message not in warnings:
                        warnings.append(message)
            else:
                message = f"交叉引用检查通过：{rid}。"
                if message not in xref_checks:
                    xref_checks.append(message)
