from app.services.float_candidate_matcher import FloatCandidateMatcher


def test_same_number_adjacent_caption_is_selected():
    result = FloatCandidateMatcher().match(
        captions=[{
            "flow_index": 11,
            "section_index": 0,
            "kind": "figure",
            "number": "1",
        }],
        objects=[{
            "flow_index": 10,
            "section_index": 0,
            "kind": "image",
            "id": "fig1",
        }],
    )

    assert result[0]["object_id"] == "fig1"
    assert result[0]["status"] == "ok"
    assert result[0]["confidence"] >= 0.80
    assert "编号一致" in result[0]["evidence"]


def test_table_caption_prefers_native_table_over_nearer_image():
    result = FloatCandidateMatcher().match(
        captions=[{
            "flow_index": 20,
            "section_index": 1,
            "kind": "table",
            "number": "2",
        }],
        objects=[
            {
                "flow_index": 19,
                "section_index": 1,
                "kind": "image",
                "id": "fig2",
            },
            {
                "flow_index": 18,
                "section_index": 1,
                "kind": "table",
                "id": "tab2",
            },
        ],
    )

    assert result[0]["object_id"] == "tab2"
    assert "对象类型与题注一致" in result[0]["evidence"]


def test_cross_section_candidate_is_not_forced():
    result = FloatCandidateMatcher().match(
        captions=[{
            "flow_index": 8,
            "section_index": 1,
            "kind": "figure",
            "number": "1",
        }],
        objects=[{
            "flow_index": 7,
            "section_index": 0,
            "kind": "image",
            "id": "fig1",
        }],
    )

    assert result[0]["object_id"] is None
    assert result[0]["status"] == "need_review"
    assert result[0]["issues"][0]["level"] == "warning"


def test_tied_candidates_are_left_for_review():
    result = FloatCandidateMatcher().match(
        captions=[{
            "flow_index": 10,
            "section_index": 0,
            "kind": "figure",
            "number": "",
        }],
        objects=[
            {"flow_index": 9, "section_index": 0, "kind": "image", "id": "fig1"},
            {"flow_index": 11, "section_index": 0, "kind": "image", "id": "fig2"},
        ],
    )

    assert result[0]["object_id"] is None
    assert result[0]["status"] == "need_review"
