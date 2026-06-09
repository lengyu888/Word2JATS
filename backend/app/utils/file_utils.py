import re
from pathlib import Path

from fastapi import UploadFile


def safe_filename(filename: str | None) -> str:
    name = Path(filename or "document.docx").name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


async def save_upload(upload: UploadFile, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = await upload.read()
    destination.write_bytes(content)
    return destination
