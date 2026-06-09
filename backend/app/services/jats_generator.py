from typing import Any

from lxml import etree


class JatsGenerator:
    NSMAP = {"mml": "http://www.w3.org/1998/Math/MathML"}

    def generate(self, article: dict[str, Any]) -> str:
        root = etree.Element("article", nsmap=self.NSMAP)
        root.set("article-type", "research-article")
        front = etree.SubElement(root, "front")
        meta = etree.SubElement(front, "article-meta")
        self._build_front(meta, article)

        body = etree.SubElement(root, "body")
        section_elements = []
        for section in article["sections"]:
            sec = etree.SubElement(body, "sec")
            sec.set("sec-type", f"level-{section.get('level', 1)}")
            etree.SubElement(sec, "title").text = section["title"]
            for paragraph in section.get("paragraphs", []):
                etree.SubElement(sec, "p").text = paragraph
            section_elements.append(sec)

        fallback = section_elements[0] if section_elements else body
        for figure in article["figures"]:
            parent = self._parent_for(figure, section_elements, fallback)
            fig = etree.SubElement(parent, "fig", id=figure["id"])
            caption = etree.SubElement(fig, "caption")
            etree.SubElement(caption, "p").text = figure.get("caption", "")
            if figure.get("path"):
                etree.SubElement(fig, "graphic", href=figure["path"])
        for list_data in article["lists"]:
            parent = self._parent_for(list_data, section_elements, fallback)
            list_element = etree.SubElement(parent, "list", id=list_data["id"])
            for item in list_data.get("items", []):
                item_element = etree.SubElement(list_element, "list-item")
                etree.SubElement(item_element, "p").text = item
        for index, formula in enumerate(article["formulas"], start=1):
            parent = self._parent_for(formula, section_elements, body)
            disp = etree.SubElement(parent, "disp-formula", id=formula.get("id") or f"eq{index}")
            content = (
                formula.get("content")
                or formula.get("tex")
                or formula.get("plain_text")
                or ""
            )
            etree.SubElement(disp, "tex-math").text = etree.CDATA(content)

        back = etree.SubElement(root, "back")
        ref_list = etree.SubElement(back, "ref-list")
        for index, reference in enumerate(article["references"], start=1):
            ref = etree.SubElement(ref_list, "ref", id=f"ref{index}")
            etree.SubElement(ref, "mixed-citation").text = reference["raw"]
        return etree.tostring(
            root, encoding="unicode", pretty_print=True, xml_declaration=False
        ).join(("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n", ""))

    def _build_front(self, meta: Any, article: dict[str, Any]) -> None:
        title_group = etree.SubElement(meta, "title-group")
        etree.SubElement(title_group, "article-title").text = article["title"]
        contrib_group = etree.SubElement(meta, "contrib-group")
        for author in article["authors"]:
            contrib = etree.SubElement(contrib_group, "contrib", attrib={"contrib-type": "author"})
            name = etree.SubElement(contrib, "name")
            surname, given_names = self._split_name(author["name"])
            etree.SubElement(name, "surname").text = surname
            etree.SubElement(name, "given-names").text = given_names
            if author.get("orcid"):
                etree.SubElement(
                    contrib, "contrib-id", attrib={"contrib-id-type": "orcid"}
                ).text = author["orcid"]
        for affiliation in article["affiliations"]:
            etree.SubElement(meta, "aff").text = affiliation
        abstract = etree.SubElement(meta, "abstract")
        etree.SubElement(abstract, "p").text = article["abstract"]
        keywords = etree.SubElement(meta, "kwd-group")
        for keyword in article["keywords"]:
            etree.SubElement(keywords, "kwd").text = keyword

    @staticmethod
    def _split_name(name: str) -> tuple[str, str]:
        if not name:
            return "", ""
        if all("\u4e00" <= char <= "\u9fff" for char in name):
            return name[0], name[1:]
        return "", name

    @staticmethod
    def _parent_for(item: dict[str, Any], sections: list[Any], fallback: Any) -> Any:
        index = item.get("section_index", -1)
        return sections[index] if isinstance(index, int) and 0 <= index < len(sections) else fallback
