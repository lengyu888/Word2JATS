from lxml import etree

from app.services.jats_auto_fixer import JatsAutoFixer


XLINK_NS = "http://www.w3.org/1999/xlink"


class RecordingSchemaValidator:
    def validate(self, xml: str) -> dict:
        root = etree.fromstring(xml.encode("utf-8"))
        graphics = root.xpath("//*[local-name()='graphic']")
        duplicate_ids = len(root.xpath("//@id")) != len(set(root.xpath("//@id")))
        journal_tags = [
            etree.QName(child).localname
            for child in root.xpath("//*[local-name()='journal-meta']")[0]
        ]
        errors = []
        if any(graphic.get(f"{{{XLINK_NS}}}href") is None for graphic in graphics):
            errors.append("Element graphic required attribute xlink:href has no prefix")
        if journal_tags != ["journal-id", "journal-title-group", "publisher"]:
            errors.append("Element journal-meta content does not follow the DTD")
        if duplicate_ids:
            errors.append("ID fig1 already defined")
        return {
            "xml_well_formed": True,
            "jats_schema_valid": not errors,
            "schema_errors": errors,
            "schema_file": "test.dtd",
        }


def test_auto_fixer_repairs_whitelisted_schema_errors():
    xml = """<article>
      <front><journal-meta>
        <publisher><publisher-name>Publisher</publisher-name></publisher>
        <journal-id journal-id-type="publisher-id">DEMO</journal-id>
        <journal-title-group><journal-title>Journal</journal-title></journal-title-group>
      </journal-meta></front>
      <body><fig id="fig1"><graphic href="media/a.png"/></fig><fig id="fig1"/></body>
    </article>"""
    validator = RecordingSchemaValidator()
    initial = validator.validate(xml)

    fixed_xml, report, final = JatsAutoFixer(validator).fix(xml, initial)

    root = etree.fromstring(fixed_xml.encode("utf-8"))
    graphic = root.xpath("//*[local-name()='graphic']")[0]
    assert graphic.get(f"{{{XLINK_NS}}}href") == "media/a.png"
    assert graphic.get("href") is None
    assert root.xpath("//@id") == ["fig1", "fig1-auto2"]
    assert final["jats_schema_valid"] is True
    assert report["attempted"] is True
    assert {item["code"] for item in report["applied_fixes"]} == {
        "GRAPHIC_XLINK_HREF",
        "JOURNAL_META_ORDER",
        "DUPLICATE_ID",
    }


def test_auto_fixer_does_not_invent_missing_publishing_metadata():
    xml = """<article><front><journal-meta>
      <journal-id journal-id-type="publisher-id">DEMO</journal-id>
      <journal-title-group><journal-title>Journal</journal-title></journal-title-group>
      <publisher><publisher-name>Publisher</publisher-name></publisher>
    </journal-meta></front><body/></article>"""
    initial = {
        "xml_well_formed": True,
        "jats_schema_valid": False,
        "schema_errors": ["Element journal-meta requires issn"],
        "schema_file": "test.dtd",
    }

    fixed_xml, report, final = JatsAutoFixer(RecordingSchemaValidator()).fix(xml, initial)

    assert "<issn" not in fixed_xml
    assert report["applied_fixes"] == []
    assert report["remaining_schema_errors"] == final["schema_errors"]


class IdrefValidator:
    def validate(self, xml: str) -> dict:
        root = etree.fromstring(xml.encode("utf-8"))
        ids = set(root.xpath("//@id"))
        unknown = [
            rid
            for value in root.xpath("//*[local-name()='xref']/@rid")
            for rid in value.split()
            if rid not in ids
        ]
        return {
            "xml_well_formed": True,
            "jats_schema_valid": not unknown,
            "schema_errors": [
                f'DTD_UNKNOWN_ID: IDREFS attribute rid references an unknown ID "{rid}"'
                for rid in unknown
            ],
            "schema_file": "test.dtd",
        }


def test_auto_fixer_removes_unknown_idrefs_but_preserves_text():
    xml = """<article><body><sec id="sec1"><p>
      Known <xref ref-type="bibr" rid="ref1 ref2">[1,2]</xref> and
      <xref ref-type="bibr" rid="ref3">[3]</xref>.
    </p></sec></body><back><ref-list><ref id="ref1"/></ref-list></back></article>"""
    validator = IdrefValidator()

    fixed_xml, report, final = JatsAutoFixer(validator).fix(
        xml, validator.validate(xml)
    )
    root = etree.fromstring(fixed_xml.encode("utf-8"))

    assert root.xpath("string(//xref/@rid)") == "ref1"
    assert "[3]" in "".join(root.xpath("//body//text()"))
    assert final["jats_schema_valid"] is True
    assert {item["code"] for item in report["applied_fixes"]} == {"UNKNOWN_IDREF"}

