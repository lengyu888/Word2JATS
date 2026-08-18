from lxml import etree


def parse_untrusted_xml(content: bytes | str) -> etree._Element:
    """Parse an uploaded XML fragment without DTD, entity, or network access."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    parser = etree.XMLParser(
        no_network=True,
        resolve_entities=False,
        load_dtd=False,
        huge_tree=False,
        recover=False,
    )
    root = etree.fromstring(data, parser)
    if root.getroottree().docinfo.doctype:
        raise ValueError("不允许在文档片段中使用 DOCTYPE。")
    return root

