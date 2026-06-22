import re
from typing import Any

from lxml import etree

from app.services.xref_resolver import XrefResolver
from app.services.profile_loader import ProfileLoader


class JatsGenerator:
    MML_NS = "http://www.w3.org/1998/Math/MathML"
    XLINK_NS = "http://www.w3.org/1999/xlink"
    NSMAP = {"mml": MML_NS, "xlink": XLINK_NS}
    XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
    XLINK_HREF = f"{{{XLINK_NS}}}href"
    DOCTYPE = (
        '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD '
        'with MathML3 v1.3 20210610//EN" "JATS-journalpublishing1-3-mathml3.dtd">'
    )
    TABLE_LABEL_RE = re.compile(
        r"^\s*(表\s*\d+(?:\s*[-－—.]\s*\d+)*|table\s*\d+(?:\s*[-.]\s*\d+)*)",
        re.I,
    )

    def __init__(self, profile: dict[str, Any] | None = None):
        self.xref_resolver = XrefResolver()
        self.profile = profile or {}

    def generate(self, article: dict[str, Any]) -> str:
        article = ProfileLoader.apply_metadata(article, self.profile)
        self._allowed_xref_ids = {
            str(item.get("id"))
            for collection in ("figures", "tables", "formulas", "references")
            for item in article.get(collection, [])
            if item.get("id")
        }
        root = etree.Element("article", nsmap=self.NSMAP)
        root.set("article-type", article.get("article_type") or "research-article")
        root.set("dtd-version", "1.3")
        root.set(self.XML_LANG, article.get("lang") or "zh")
        front = etree.SubElement(root, "front")
        journal_meta = etree.SubElement(front, "journal-meta")
        self._build_journal_meta(journal_meta, article)
        meta = etree.SubElement(front, "article-meta")
        self._build_article_meta(meta, article)

        body = etree.SubElement(root, "body")
        section_elements = []
        section_stack: list[tuple[int, Any]] = []
        for section_index, section in enumerate(article["sections"], start=1):
            level = max(1, int(section.get("level", 1) or 1))
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()
            parent = section_stack[-1][1] if section_stack else body
            sec = etree.SubElement(parent, "sec", id=f"sec{section_index}")
            sec.set("sec-type", f"level-{level}")
            etree.SubElement(sec, "title").text = section["title"]
            for paragraph in section.get("paragraphs", []):
                self._append_body_paragraph(sec, paragraph)
            section_elements.append(sec)
            section_stack.append((level, sec))

        fallback = section_elements[0] if section_elements else body
        for figure in article["figures"]:
            parent = self._parent_for(figure, section_elements, fallback)
            fig = self._floating_element(parent, "fig", id=figure["id"])
            caption = etree.SubElement(fig, "caption")
            etree.SubElement(caption, "p").text = figure.get("caption", "")
            paths = figure.get("paths") or ([figure["path"]] if figure.get("path") else [])
            for path in paths:
                etree.SubElement(fig, "graphic", attrib={self.XLINK_HREF: path})
        for index, table_data in enumerate(article.get("tables", []), start=1):
            parent = self._parent_for(table_data, section_elements, fallback)
            table_wrap = self._floating_element(
                parent, "table-wrap", id=table_data.get("id") or f"tab{index}"
            )
            caption_text = table_data.get("caption", "")
            label_match = self.TABLE_LABEL_RE.match(caption_text)
            label_text = label_match.group(1).strip() if label_match else f"Table {index}"
            etree.SubElement(table_wrap, "label").text = label_text
            caption = etree.SubElement(table_wrap, "caption")
            etree.SubElement(caption, "p").text = caption_text
            rows = table_data.get("rows", [])
            if rows:
                table = etree.SubElement(table_wrap, "table")
                thead = etree.SubElement(table, "thead")
                header_row = etree.SubElement(thead, "tr")
                for cell in rows[0]:
                    cell_element = etree.SubElement(header_row, "th")
                    self.xref_resolver.append_mixed_content(
                        cell_element,
                        str(cell),
                        allowed_ids=self._allowed_xref_ids,
                    )
                if len(rows) > 1:
                    tbody = etree.SubElement(table, "tbody")
                    for row in rows[1:]:
                        row_element = etree.SubElement(tbody, "tr")
                        for cell in row:
                            cell_element = etree.SubElement(row_element, "td")
                            self.xref_resolver.append_mixed_content(
                                cell_element,
                                str(cell),
                                allowed_ids=self._allowed_xref_ids,
                            )
            elif table_data.get("path"):
                etree.SubElement(
                    table_wrap,
                    "graphic",
                    attrib={self.XLINK_HREF: table_data["path"]},
                )
        for list_data in article["lists"]:
            parent = self._parent_for(list_data, section_elements, fallback)
            list_element = self._floating_element(parent, "list", id=list_data["id"])
            for item in list_data.get("items", []):
                item_element = etree.SubElement(list_element, "list-item")
                self._append_body_paragraph(item_element, item)
        for index, formula in enumerate(article["formulas"], start=1):
            section_index = formula.get("section_index", -1)
            parent = (
                section_elements[section_index]
                if isinstance(section_index, int) and 0 <= section_index < len(section_elements)
                else body
            )
            disp = self._floating_element(
                parent, "disp-formula", id=formula.get("id") or f"eq{index}"
            )
            alternatives = etree.SubElement(disp, "alternatives")
            if formula.get("mathml"):
                try:
                    alternatives.append(etree.fromstring(formula["mathml"].encode("utf-8")))
                except (etree.XMLSyntaxError, ValueError):
                    pass
            content = (
                formula.get("latex")
                or formula.get("content")
                or formula.get("tex")
                or formula.get("plain_text")
                or ""
            )
            etree.SubElement(alternatives, "tex-math").text = etree.CDATA(content)

        back = etree.SubElement(root, "back")
        if article["references"]:
            ref_list = etree.SubElement(back, "ref-list")
            etree.SubElement(ref_list, "title").text = "References"
            for index, reference in enumerate(article["references"], start=1):
                ref = etree.SubElement(ref_list, "ref", id=reference.get("id") or f"ref{index}")
                etree.SubElement(ref, "label").text = reference.get("label") or f"[{index}]"
                if self._has_structured_reference(reference):
                    self._build_element_citation(ref, reference)
                else:
                    etree.SubElement(ref, "mixed-citation").text = (
                        reference.get("mixed_citation") or reference.get("raw", "")
                    )
        return etree.tostring(
            root,
            encoding="UTF-8",
            pretty_print=True,
            xml_declaration=True,
            doctype=self.DOCTYPE,
        ).decode("utf-8")

    @staticmethod
    def _build_journal_meta(meta: Any, article: dict[str, Any]) -> None:
        journal_id = etree.SubElement(meta, "journal-id", attrib={"journal-id-type": "publisher-id"})
        journal_id.text = article.get("journal_id", "")
        title_group = etree.SubElement(meta, "journal-title-group")
        etree.SubElement(title_group, "journal-title").text = article.get("journal_title", "")
        if article.get("issn"):
            etree.SubElement(
                meta, "issn", attrib={"pub-type": "epub"}
            ).text = article["issn"]
        publisher = etree.SubElement(meta, "publisher")
        etree.SubElement(publisher, "publisher-name").text = article.get("publisher_name", "")

    def _build_article_meta(self, meta: Any, article: dict[str, Any]) -> None:
        if article.get("doi"):
            etree.SubElement(meta, "article-id", attrib={"pub-id-type": "doi"}).text = article["doi"]
        if article.get("subject"):
            categories = etree.SubElement(meta, "article-categories")
            subject_group = etree.SubElement(categories, "subj-group", attrib={"subj-group-type": "heading"})
            etree.SubElement(subject_group, "subject").text = article["subject"]
        title_group = etree.SubElement(meta, "title-group")
        etree.SubElement(title_group, "article-title").text = article["title"]
        if article["authors"]:
            contrib_group = etree.SubElement(meta, "contrib-group")
            for author in article["authors"]:
                contrib = etree.SubElement(contrib_group, "contrib", attrib={"contrib-type": "author"})
                if author.get("orcid"):
                    etree.SubElement(
                        contrib, "contrib-id", attrib={"contrib-id-type": "orcid"}
                    ).text = author["orcid"]
                name = etree.SubElement(contrib, "name")
                surname, given_names = self._split_name(author["name"])
                etree.SubElement(name, "surname").text = surname
                etree.SubElement(name, "given-names").text = given_names
                affiliation_ids = author.get("affiliation_ids") or [
                    f"aff{index}" for index in range(1, len(article["affiliations"]) + 1)
                ]
                for affiliation_id in affiliation_ids:
                    etree.SubElement(
                        contrib,
                        "xref",
                        attrib={"ref-type": "aff", "rid": affiliation_id},
                    )
        for index, affiliation in enumerate(article["affiliations"], start=1):
            etree.SubElement(meta, "aff", id=f"aff{index}").text = affiliation
        if any(article.get(field) for field in ("pub_year", "pub_month", "pub_day")):
            pub_date = etree.SubElement(meta, "pub-date", attrib={"publication-format": "electronic"})
            if article.get("pub_day"):
                etree.SubElement(pub_date, "day").text = article["pub_day"]
            if article.get("pub_month"):
                etree.SubElement(pub_date, "month").text = article["pub_month"]
            if article.get("pub_year"):
                etree.SubElement(pub_date, "year").text = article["pub_year"]
        abstract = etree.SubElement(meta, "abstract")
        etree.SubElement(abstract, "p").text = article["abstract"]
        if article["keywords"]:
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

    @staticmethod
    def _floating_element(parent: Any, tag: str, **attributes: str) -> Any:
        element = etree.Element(tag, **attributes)
        direct_sections = parent.xpath("./*[local-name()='sec']")
        if etree.QName(parent).localname == "sec" and direct_sections:
            parent.insert(parent.index(direct_sections[0]), element)
        else:
            parent.append(element)
        return element

    def _append_body_paragraph(self, parent: Any, text: str) -> Any:
        paragraph = etree.SubElement(parent, "p")
        self.xref_resolver.append_mixed_content(
            paragraph, text, allowed_ids=self._allowed_xref_ids
        )
        return paragraph

    @staticmethod
    def _has_structured_reference(reference: dict[str, Any]) -> bool:
        return bool(reference.get("article_title") or reference.get("source") or reference.get("year"))

    @staticmethod
    def _build_element_citation(parent: Any, reference: dict[str, Any]) -> None:
        citation = etree.SubElement(
            parent,
            "element-citation",
            attrib={"publication-type": reference.get("publication_type") or "journal"},
        )
        if reference.get("authors"):
            person_group = etree.SubElement(citation, "person-group", attrib={"person-group-type": "author"})
            for author in reference["authors"]:
                name = etree.SubElement(person_group, "name")
                surname, given = JatsGenerator._split_name(author)
                etree.SubElement(name, "surname").text = surname
                etree.SubElement(name, "given-names").text = given
        field_map = (
            ("article_title", "article-title"), ("source", "source"), ("year", "year"),
            ("volume", "volume"), ("issue", "issue"), ("fpage", "fpage"), ("lpage", "lpage"),
        )
        for field, tag in field_map:
            if reference.get(field):
                etree.SubElement(citation, tag).text = str(reference[field])
        if reference.get("doi"):
            etree.SubElement(citation, "pub-id", attrib={"pub-id-type": "doi"}).text = reference["doi"]
