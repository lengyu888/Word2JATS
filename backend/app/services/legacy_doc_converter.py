import os
import shutil
import subprocess
import zipfile
from pathlib import Path


class LegacyDocConversionError(ValueError):
    """Raised when a legacy binary Word document cannot be converted safely."""


class LegacyDocConverter:
    """Convert OLE ``.doc`` files to OOXML with a local LibreOffice process."""

    WINDOWS_CANDIDATES = (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    )

    def __init__(self, executable: str | Path | None = None, timeout: int = 120):
        self.executable = Path(executable) if executable else self._find_executable()
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.executable and self.executable.is_file())

    def convert(self, source: str | Path, output_dir: str | Path) -> Path:
        source_path = Path(source).resolve()
        destination = Path(output_dir).resolve()
        if source_path.suffix.casefold() != ".doc" or not source_path.is_file():
            raise LegacyDocConversionError("待转换文件不是有效的 .doc 文档。")
        if not self.available:
            raise LegacyDocConversionError(
                "服务器未安装 LibreOffice，暂时无法转换 .doc；"
                "请使用 Docker 版本或配置 WORD2JATS_SOFFICE。"
            )

        destination.mkdir(parents=True, exist_ok=True)
        profile_dir = destination / ".libreoffice-profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        command = [
            str(self.executable),
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            "--nolockcheck",
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--convert-to",
            "docx:Office Open XML Text",
            "--outdir",
            str(destination),
            str(source_path),
        ]
        environment = os.environ.copy()
        environment.setdefault("HOME", str(destination))
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=self.timeout,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise LegacyDocConversionError(
                f".doc 预转换超过 {self.timeout} 秒，已终止。"
            ) from exc
        except OSError as exc:
            raise LegacyDocConversionError(f"无法启动 LibreOffice：{exc}") from exc

        output = destination / f"{source_path.stem}.docx"
        if completed.returncode != 0 or not output.is_file():
            details = (completed.stderr or completed.stdout or "未知转换错误").strip()
            raise LegacyDocConversionError(
                f"LibreOffice 无法转换该 .doc 文档：{details[:500]}"
            )
        try:
            with zipfile.ZipFile(output) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise LegacyDocConversionError("转换结果缺少 word/document.xml。")
        except zipfile.BadZipFile as exc:
            raise LegacyDocConversionError("LibreOffice 输出不是有效的 DOCX 文件。") from exc
        return output

    @classmethod
    def _find_executable(cls) -> Path | None:
        configured = os.getenv("WORD2JATS_SOFFICE", "").strip()
        candidates = [Path(configured)] if configured else []
        for command in ("soffice", "libreoffice"):
            discovered = shutil.which(command)
            if discovered:
                candidates.append(Path(discovered))
        if os.name == "nt":
            candidates.extend(cls.WINDOWS_CANDIDATES)
        return next((path.resolve() for path in candidates if path.is_file()), None)
