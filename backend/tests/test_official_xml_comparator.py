from pathlib import Path

from app.services.official_xml_comparator import OfficialXmlComparator


def write_official(tmp_path: Path, xml: str) -> Path:
    path = tmp_path / "official.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def test_reference_article_titles_do_not_count_as_primary_titles(tmp_path):
    generated = """
    <article><front><article-meta><title-group><article-title>Main title</article-title>
    </title-group><abstract><p>Abstract text</p></abstract></article-meta></front>
    <body/><back/></article>
    """
    official = write_official(tmp_path, """
    <article><front><article-meta><title-group><article-title>Main title</article-title>
    </title-group><abstract><p>Abstract text</p></abstract></article-meta></front>
    <body/><back><ref-list><ref><element-citation>
      <article-title>Reference title</article-title>
    </element-citation></ref></ref-list></back></article>
    """)

    result = OfficialXmlComparator().compare(generated, official)

    assert result["metric_version"] == "2.0"
    assert result["facts"]["generated"]["title"] == "Main title"
    assert result["facts"]["official"]["title"] == "Main title"
    assert result["dimensions"]["metadata"]["score"] == 100


def test_semantic_comparison_preserves_section_order_and_keyword_sets(tmp_path):
    generated = """
    <article><front><article-meta><title-group><article-title>A</article-title></title-group>
      <abstract><p>Summary</p></abstract><kwd-group><kwd>JATS</kwd><kwd>XML</kwd></kwd-group>
    </article-meta></front><body>
      <sec><title>Methods</title><sec><title>Dataset</title></sec></sec>
      <sec><title>Results</title></sec>
    </body><back/></article>
    """
    official = write_official(tmp_path, """
    <article><front><article-meta><title-group><article-title>A</article-title></title-group>
      <abstract><p>Summary</p></abstract><kwd-group><kwd>JATS</kwd><kwd>Publishing</kwd></kwd-group>
    </article-meta></front><body>
      <sec><title>Methods</title><sec><title>Dataset</title></sec></sec>
      <sec><title>Discussion</title></sec>
    </body><back/></article>
    """)

    result = OfficialXmlComparator().compare(generated, official)

    assert result["facts"]["generated"]["section_titles"] == [
        "Methods", "Dataset", "Results"
    ]
    assert result["facts"]["generated"]["section_levels"] == [1, 2, 1]
    assert result["dimensions"]["metadata"]["score"] < 100
    assert result["dimensions"]["structure"]["score"] < 100
    assert any(
        item["metric"] == "keywords"
        for item in result["recoverable_differences"]
    )


def test_publisher_enriched_metadata_is_reported_separately(tmp_path):
    generated = """
    <article><front><journal-meta/><article-meta><title-group>
      <article-title>A</article-title></title-group><abstract><p>B</p></abstract>
    </article-meta></front><body/><back/></article>
    """
    official = write_official(tmp_path, """
    <article><front><journal-meta><journal-id journal-id-type="publisher-id">J1</journal-id>
      </journal-meta><article-meta><article-id pub-id-type="doi">10.1/example</article-id>
      <title-group><article-title>A</article-title></title-group><abstract><p>B</p></abstract>
    </article-meta></front><body/><back/></article>
    """)

    result = OfficialXmlComparator().compare(generated, official)

    metrics = {item["metric"] for item in result["publisher_enriched_differences"]}
    assert metrics == {"doi", "journal_id"}
    assert not any(
        item["metric"] in metrics for item in result["recoverable_differences"]
    )


def test_equivalent_section_numbers_and_internal_ids_compare_semantically(tmp_path):
    generated = """
    <article><front><article-meta><title-group><article-title>A</article-title></title-group>
      <abstract><p>B</p></abstract></article-meta></front><body>
      <sec><title>Introduction</title><p>See <xref ref-type="bibr" rid="ref1">[1]</xref>.</p></sec>
    </body><back><ref-list><ref id="ref1"><label>[1]</label>
      <mixed-citation>Smith J. Example study. Journal. 2025.</mixed-citation>
    </ref></ref-list></back></article>
    """
    official = write_official(tmp_path, """
    <article><front><article-meta><title-group><article-title>A</article-title></title-group>
      <abstract><p>B</p></abstract></article-meta></front><body>
      <sec><title>1. Introduction</title><p>See <xref ref-type="bibr" rid="B1">[1]</xref>.</p></sec>
    </body><back><ref-list><ref id="B1"><label>1</label><element-citation>
      <person-group><name><surname>Smith</surname><given-names>J</given-names></name></person-group>
      <article-title>Example study</article-title><source>Journal</source><year>2025</year>
    </element-citation></ref></ref-list></back></article>
    """)

    result = OfficialXmlComparator().compare(generated, official)

    assert result["dimensions"]["structure"]["metrics"]["section_titles"] == 100
    assert result["dimensions"]["references"]["score"] >= 80
    assert result["dimensions"]["xrefs"]["score"] == 100


def test_multi_target_rid_is_equivalent_to_split_xrefs(tmp_path):
    generated = """
    <article><front><article-meta><title-group><article-title>A</article-title></title-group>
    <abstract><p>B</p></abstract></article-meta></front><body><sec><title>Results</title>
    <p><xref ref-type="bibr" rid="ref1 ref2">[1,2]</xref></p></sec></body><back/></article>
    """
    official = write_official(tmp_path, """
    <article><front><article-meta><title-group><article-title>A</article-title></title-group>
    <abstract><p>B</p></abstract></article-meta></front><body><sec><title>1. Results</title>
    <p>[<xref ref-type="bibr" rid="b1">1</xref>,<xref ref-type="bibr" rid="b2">2</xref>]</p>
    </sec></body><back/></article>
    """)

    result = OfficialXmlComparator().compare(generated, official)

    assert result["dimensions"]["xrefs"]["score"] == 100
