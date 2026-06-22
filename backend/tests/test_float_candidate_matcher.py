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


def test_adjacent_image_can_be_a_table_screenshot_without_matching_global_id():
    result = FloatCandidateMatcher().match(
        captions=[{
            "flow_index": 148,
            "section_index": 5,
            "kind": "table",
            "number": "7",
        }],
        objects=[{
            "flow_index": 149,
            "section_index": 5,
            "kind": "image",
            "id": "fig10",
        }],
    )

    assert result[0]["object_id"] == "fig10"
    assert result[0]["status"] == "ok"
    assert any("表格截图" in item for item in result[0]["evidence"])


def test_unique_nearby_image_can_be_a_table_screenshot():
    result = FloatCandidateMatcher().match(
        captions=[{
            "flow_index": 30,
            "section_index": 2,
            "kind": "table",
            "number": "3",
        }],
        objects=[{
            "flow_index": 33,
            "section_index": 2,
            "kind": "image",
            "id": "fig6",
        }],
    )

    assert result[0]["object_id"] == "fig6"
    assert result[0]["status"] == "ok"


def test_ordered_table_screenshots_prefer_the_closest_unused_image():
    result = FloatCandidateMatcher().match(
        captions=[
            {"flow_index": 40, "section_index": 3, "kind": "table", "number": "4"},
            {"flow_index": 43, "section_index": 3, "kind": "table", "number": "5"},
            {"flow_index": 46, "section_index": 3, "kind": "table", "number": "6"},
            {"flow_index": 48, "section_index": 3, "kind": "table", "number": "7"},
        ],
        objects=[
            {"flow_index": 41, "section_index": 3, "kind": "image", "id": "fig7"},
            {"flow_index": 44, "section_index": 3, "kind": "image", "id": "fig8"},
            {"flow_index": 47, "section_index": 3, "kind": "image", "id": "fig9"},
            {"flow_index": 49, "section_index": 3, "kind": "image", "id": "fig10"},
        ],
    )

    assert [item["object_id"] for item in result] == [
        "fig7", "fig8", "fig9", "fig10"
    ]
