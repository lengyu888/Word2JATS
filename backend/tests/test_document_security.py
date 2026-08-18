import asyncio
from io import BytesIO
import os
import time
import zipfile
from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from app.services.document_security import (
    DocumentSecurityError,
    DocumentSecurityPolicy,
)
from app.services.temp_storage import TempStorageManager, TempStoragePolicy
from app.utils.file_utils import save_upload_limited
from app.utils.xml_utils import parse_untrusted_xml


def _write_minimal_docx(path: Path, extra: dict[str, bytes] | None = None) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
        for name, content in (extra or {}).items():
            archive.writestr(name, content)


def test_security_policy_accepts_minimal_docx(tmp_path):
    path = tmp_path / "paper.docx"
    _write_minimal_docx(path)

    DocumentSecurityPolicy().inspect(path, ".docx")


def test_security_policy_rejects_extension_spoofing(tmp_path):
    path = tmp_path / "paper.docx"
    path.write_bytes(b"MZ executable content")

    with pytest.raises(DocumentSecurityError, match="不是有效的 OOXML ZIP"):
        DocumentSecurityPolicy().inspect(path, ".docx")


def test_security_policy_rejects_zip_path_traversal(tmp_path):
    path = tmp_path / "traversal.docx"
    _write_minimal_docx(path, {"../outside.txt": b"secret"})

    with pytest.raises(DocumentSecurityError, match="不安全的 ZIP 路径"):
        DocumentSecurityPolicy().inspect(path, ".docx")


def test_security_policy_rejects_abnormal_compression_ratio(tmp_path):
    path = tmp_path / "bomb.docx"
    _write_minimal_docx(path, {"word/media/huge.bin": b"0" * (2 * 1024 * 1024)})
    policy = DocumentSecurityPolicy(max_compression_ratio=5)

    with pytest.raises(DocumentSecurityError, match="压缩比异常"):
        policy.inspect(path, ".docx")


def test_security_policy_rejects_non_word_legacy_doc(tmp_path):
    path = tmp_path / "paper.doc"
    path.write_bytes(b"MZ executable content")

    with pytest.raises(DocumentSecurityError, match="不是受支持的 Word"):
        DocumentSecurityPolicy().inspect(path, ".doc")


def test_limited_upload_removes_partial_file(tmp_path):
    destination = tmp_path / "oversized.docx"
    upload = UploadFile(BytesIO(b"x" * 2048), filename="oversized.docx")

    with pytest.raises(ValueError, match="上传限制"):
        asyncio.run(save_upload_limited(upload, destination, 1024))
    assert not destination.exists()


def test_untrusted_xml_rejects_doctype_and_external_entity():
    payload = (
        b'<!DOCTYPE root [<!ENTITY secret SYSTEM "file:///etc/passwd">]>'
        b"<root>&secret;</root>"
    )

    with pytest.raises(ValueError, match="DOCTYPE"):
        parse_untrusted_xml(payload)


def test_temp_storage_removes_only_expired_conversion_directories(tmp_path):
    expired = tmp_path / ("a" * 32)
    current = tmp_path / ("b" * 32)
    unrelated = tmp_path / "manual-files"
    for path in (expired, current, unrelated):
        path.mkdir()
        (path / "data.bin").write_bytes(b"data")
    old = time.time() - 7200
    os.utime(expired, (old, old))
    manager = TempStorageManager(
        tmp_path,
        TempStoragePolicy(
            retention_seconds=3600,
            max_conversion_directories=10,
            max_total_bytes=1024,
        ),
    )

    assert manager.cleanup() == 1
    assert not expired.exists()
    assert current.exists()
    assert unrelated.exists()


def test_temp_storage_enforces_directory_count(tmp_path):
    older = tmp_path / ("c" * 32)
    newer = tmp_path / ("d" * 32)
    older.mkdir()
    newer.mkdir()
    (older / "data.bin").write_bytes(b"old")
    (newer / "data.bin").write_bytes(b"new")
    old = time.time() - 60
    os.utime(older, (old, old))
    manager = TempStorageManager(
        tmp_path,
        TempStoragePolicy(
            retention_seconds=3600,
            max_conversion_directories=1,
            max_total_bytes=1024,
        ),
    )

    assert manager.cleanup() == 1
    assert not older.exists()
    assert newer.exists()
