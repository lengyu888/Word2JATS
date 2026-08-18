import os
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class DocumentSecurityError(ValueError):
    """Raised when an uploaded document violates a resource or format boundary."""


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


@dataclass(frozen=True)
class DocumentSecurityPolicy:
    """Centralized upload and OOXML limits used before any document parsing."""

    max_upload_bytes: int = 50 * 1024 * 1024
    max_request_bytes: int = 220 * 1024 * 1024
    max_batch_files: int = 20
    max_zip_entries: int = 5000
    max_uncompressed_bytes: int = 250 * 1024 * 1024
    max_zip_entry_bytes: int = 64 * 1024 * 1024
    max_xml_entry_bytes: int = 24 * 1024 * 1024
    max_compression_ratio: int = 200
    max_concurrent_conversions: int = 2

    @classmethod
    def from_env(cls) -> "DocumentSecurityPolicy":
        mib = 1024 * 1024
        return cls(
            max_upload_bytes=_env_int("WORD2JATS_MAX_UPLOAD_MB", 50) * mib,
            max_request_bytes=_env_int("WORD2JATS_MAX_REQUEST_MB", 220) * mib,
            max_batch_files=_env_int("WORD2JATS_MAX_BATCH_FILES", 20),
            max_zip_entries=_env_int("WORD2JATS_MAX_ZIP_ENTRIES", 5000),
            max_uncompressed_bytes=_env_int(
                "WORD2JATS_MAX_UNCOMPRESSED_MB", 250
            ) * mib,
            max_zip_entry_bytes=_env_int("WORD2JATS_MAX_ZIP_ENTRY_MB", 64) * mib,
            max_xml_entry_bytes=_env_int("WORD2JATS_MAX_XML_ENTRY_MB", 24) * mib,
            max_compression_ratio=_env_int(
                "WORD2JATS_MAX_COMPRESSION_RATIO", 200
            ),
            max_concurrent_conversions=_env_int(
                "WORD2JATS_MAX_CONCURRENT_CONVERSIONS", 2
            ),
        )

    def inspect(self, path: str | Path, suffix: str) -> None:
        document = Path(path)
        size = document.stat().st_size if document.is_file() else 0
        if not size:
            raise DocumentSecurityError("上传文件为空或不存在。")
        if size > self.max_upload_bytes:
            raise DocumentSecurityError(
                f"文件超过 {self.max_upload_bytes // (1024 * 1024)} MB 上传限制。"
            )
        if suffix.casefold() == ".docx":
            self.inspect_docx(document)
        elif suffix.casefold() == ".doc":
            self.inspect_legacy_doc(document)
        else:
            raise DocumentSecurityError("仅支持 .doc 或 .docx 文件。")

    def inspect_legacy_doc(self, path: str | Path) -> None:
        with Path(path).open("rb") as source:
            header = source.read(8)
        is_ole = header == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        is_rtf = header.startswith(b"{\\rtf")
        if not (is_ole or is_rtf):
            raise DocumentSecurityError(
                "文件扩展名为 .doc，但内容不是受支持的 Word 二进制或 RTF 文档。"
            )

    def inspect_docx(self, path: str | Path) -> None:
        try:
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) > self.max_zip_entries:
                    raise DocumentSecurityError(
                        f"DOCX ZIP 条目超过 {self.max_zip_entries} 个安全限制。"
                    )
                names: set[str] = set()
                total_size = 0
                for info in entries:
                    normalized = info.filename.replace("\\", "/")
                    parts = PurePosixPath(normalized).parts
                    if normalized.startswith("/") or ".." in parts:
                        raise DocumentSecurityError("DOCX 包含不安全的 ZIP 路径。")
                    if info.flag_bits & 0x1:
                        raise DocumentSecurityError("不支持包含加密条目的 DOCX。")
                    if info.file_size > self.max_zip_entry_bytes:
                        raise DocumentSecurityError(
                            f"DOCX 内单个文件超过 {self.max_zip_entry_bytes // (1024 * 1024)} MB。"
                        )
                    if normalized.endswith(".xml") and info.file_size > self.max_xml_entry_bytes:
                        raise DocumentSecurityError(
                            f"DOCX XML 条目超过 {self.max_xml_entry_bytes // (1024 * 1024)} MB。"
                        )
                    total_size += info.file_size
                    if total_size > self.max_uncompressed_bytes:
                        raise DocumentSecurityError(
                            f"DOCX 解压后超过 {self.max_uncompressed_bytes // (1024 * 1024)} MB。"
                        )
                    if info.file_size >= 1024 * 1024:
                        ratio = info.file_size / max(1, info.compress_size)
                        if ratio > self.max_compression_ratio:
                            raise DocumentSecurityError(
                                "DOCX ZIP 压缩比异常，已拒绝可能的压缩炸弹。"
                            )
                    names.add(normalized)
                required = {"[Content_Types].xml", "word/document.xml"}
                if not required.issubset(names):
                    raise DocumentSecurityError("文件不是完整的 DOCX 文档。")
        except zipfile.BadZipFile as exc:
            raise DocumentSecurityError("文件扩展名为 .docx，但内容不是有效的 OOXML ZIP。") from exc

