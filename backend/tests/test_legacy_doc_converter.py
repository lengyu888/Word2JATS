from pathlib import Path

import pytest

from app.services.legacy_doc_converter import (
    LegacyDocConversionError,
    LegacyDocConverter,
)
from tests.test_services import build_sample_docx


def test_legacy_doc_converter_requires_local_libreoffice(tmp_path):
    converter = LegacyDocConverter(executable=tmp_path / "missing-soffice")
    source = tmp_path / "paper.doc"
    source.write_bytes(b"legacy-word")

    with pytest.raises(LegacyDocConversionError, match="未安装 LibreOffice"):
        converter.convert(source, tmp_path / "output")


def test_legacy_doc_converter_validates_generated_docx(tmp_path, monkeypatch):
    executable = tmp_path / "soffice"
    executable.write_bytes(b"stub")
    source = tmp_path / "paper.doc"
    source.write_bytes(b"legacy-word")

    def fake_run(command, **kwargs):
        output_dir = Path(command[command.index("--outdir") + 1])
        (output_dir / "paper.docx").write_bytes(build_sample_docx())

        class Result:
            returncode = 0
            stdout = "converted"
            stderr = ""

        return Result()

    monkeypatch.setattr(
        "app.services.legacy_doc_converter.subprocess.run", fake_run
    )
    converted = LegacyDocConverter(executable=executable).convert(
        source, tmp_path / "output"
    )

    assert converted.name == "paper.docx"
    assert converted.read_bytes().startswith(b"PK")
