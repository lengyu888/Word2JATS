import re
from pathlib import Path

from fastapi import UploadFile


def safe_filename(filename: str | None) -> str:
    name = Path(filename or "document.docx").name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


async def save_upload(upload: UploadFile, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            output.write(chunk)
    return destination


async def save_upload_limited(
    upload: UploadFile, destination: Path, max_bytes: int
) -> Path:
    """Stream an upload to disk and delete partial content when it exceeds the limit."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(
                        f"文件超过 {max_bytes // (1024 * 1024)} MB 上传限制。"
                    )
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination
