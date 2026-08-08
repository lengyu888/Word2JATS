import subprocess
import sys
from pathlib import Path


def test_release_check_passes_for_current_repository():
    backend_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/release_check.py"],
        cwd=backend_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_processing_stats_are_additive_on_convert():
    from fastapi.testclient import TestClient
    from app.main import app
    from tests.test_services import build_sample_docx

    response = TestClient(app).post(
        "/api/convert",
        files={
            "file": (
                "stats.docx",
                build_sample_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    stats = response.json()["processing_stats"]
    assert stats["elapsed_seconds"] >= 0
    assert stats["source_node_count"] > 0
    assert stats["section_count"] > 0
    assert stats["schema_error_count"] == 0
    assert stats["auto_fix_rounds"] == response.json()["validation"]["auto_fix"]["rounds"]
