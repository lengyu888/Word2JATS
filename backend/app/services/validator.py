from typing import Any

from lxml import etree


class ArticleValidator:
    def validate(self, article: dict[str, Any], xml: str) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        self._validate_required_content(article, errors)
        self._validate_quality(article, warnings)
        self._validate_xml(xml, errors)
        return {"passed": not errors, "errors": errors, "warnings": warnings}

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
                formula.get("content")
                or formula.get("tex")
                or formula.get("plain_text")
                or ""
            )
            if not content.strip():
                warnings.append(f"公式 {formula.get('id') or index} 内容为空。")
        for section in article.get("sections", []):
            if not section.get("paragraphs"):
                warnings.append(f"章节“{section.get('title', '未命名章节')}”没有正文段落。")
        if len(keywords) < 3:
            warnings.append("关键词少于 3 个，建议补充关键词。")

    @staticmethod
    def _validate_xml(xml: str, errors: list[str]) -> None:
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
