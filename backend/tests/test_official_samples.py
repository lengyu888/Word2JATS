from app.services.official_sample_evaluator import acceptance_passed, aggregate_results


def test_aggregate_official_results_reports_average_minimum_and_schema_rate():
    summary = aggregate_results([
        {"similarity_score": 90, "schema_valid": True},
        {"similarity_score": 80, "schema_valid": False},
    ])

    assert summary == {
        "sample_count": 2,
        "average_similarity": 85.0,
        "minimum_similarity": 80,
        "schema_valid_rate": 0.5,
    }


def test_aggregate_official_results_handles_empty_input():
    assert aggregate_results([]) == {
        "sample_count": 0,
        "average_similarity": 0.0,
        "minimum_similarity": 0,
        "schema_valid_rate": 0.0,
    }


def test_official_gate_requires_no_regression():
    summary = aggregate_results([
        {"similarity_score": 92, "schema_valid": True},
        {"similarity_score": 90, "schema_valid": True},
    ])

    assert acceptance_passed(
        summary, average_floor=91.0, minimum_floor=90, schema_floor=1.0
    ) is True
    assert acceptance_passed(
        summary, average_floor=91.4, minimum_floor=90, schema_floor=1.0
    ) is False
