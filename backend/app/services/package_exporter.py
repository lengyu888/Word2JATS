import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any


class PackageExporter:
    def __init__(self, temp_root: Path):
        self.temp_root = temp_root.resolve()

    def build(
        self,
        *,
        filename: str,
        article: dict[str, Any],
        xml: str,
        media_paths: list[str],
        validation: dict[str, Any],
        quality_report: dict[str, Any] | None = None,
    ) -> bytes:
        files = ["article.xml", "article.json", "validation_report.md", "media/"]
        if quality_report:
            files.append("quality_report.json")
        media_files = self._resolve_media_files(media_paths)
        files.extend(f"media/{name}" for name, _ in media_files)
        files.append("manifest.json")
        manifest = {
            "source_filename": filename,
            "article_title": article.get("title", ""),
            "files": files,
            "validation": {
                "passed": validation.get("passed", False),
                "error_count": len(validation.get("errors", [])),
                "warning_count": len(validation.get("warnings", [])),
            },
            "quality_score": (quality_report or {}).get("total_score"),
        }

        output = BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("article.xml", xml)
            archive.writestr(
                "article.json", json.dumps(article, ensure_ascii=False, indent=2)
            )
            archive.writestr(
                "validation_report.md", self._validation_report(validation)
            )
            if quality_report:
                archive.writestr(
                    "quality_report.json",
                    json.dumps(quality_report, ensure_ascii=False, indent=2),
                )
            archive.writestr("media/", b"")
            for archive_name, path in media_files:
                archive.write(path, f"media/{archive_name}")
            archive.writestr(
                "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
            )
        return output.getvalue()

    def _resolve_media_files(self, media_paths: list[str]) -> list[tuple[str, Path]]:
        resolved = []
        used_names: set[str] = set()
        for media_path in media_paths:
            path = self._resolve_allowed_path(media_path)
            name = self._unique_name(path.name, used_names)
            used_names.add(name)
            resolved.append((name, path))
        return resolved

    def _resolve_allowed_path(self, media_path: str) -> Path:
        raw = Path(media_path)
        candidates = [raw.resolve()] if raw.is_absolute() else [
            (Path.cwd() / raw).resolve(),
            (self.temp_root.parent / raw).resolve(),
            (self.temp_root.parent.parent / raw).resolve(),
        ]
        for candidate in candidates:
            if candidate.is_relative_to(self.temp_root) and candidate.is_file():
                return candidate
        raise ValueError(f"媒体路径不允许访问或不存在：{media_path}")

    @staticmethod
    def _unique_name(name: str, used_names: set[str]) -> str:
        if name not in used_names:
            return name
        path = Path(name)
        index = 2
        while f"{path.stem}_{index}{path.suffix}" in used_names:
            index += 1
        return f"{path.stem}_{index}{path.suffix}"

    @staticmethod
    def _validation_report(validation: dict[str, Any]) -> str:
        lines = [
            "# Word2JATS Validation Report",
            "",
            f"- Passed: **{'Yes' if validation.get('passed') else 'No'}**",
            f"- Errors: **{len(validation.get('errors', []))}**",
            f"- Warnings: **{len(validation.get('warnings', []))}**",
            f"- XML well formed: **{validation.get('xml_well_formed', 'Unknown')}**",
            f"- JATS schema valid: **{validation.get('jats_schema_valid', 'Not configured')}**",
            "",
            "## Errors",
            "",
        ]
        lines.extend(f"- {item}" for item in validation.get("errors", []))
        if not validation.get("errors"):
            lines.append("- None")
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in validation.get("warnings", []))
        if not validation.get("warnings"):
            lines.append("- None")
        lines.extend(["", "## JATS Schema Errors", ""])
        lines.extend(f"- {item}" for item in validation.get("schema_errors", []))
        if not validation.get("schema_errors"):
            lines.append("- None")
        auto_fix = validation.get("auto_fix", {})
        lines.extend([
            "",
            "## Schema Auto Fix",
            "",
            f"- Attempted: **{auto_fix.get('attempted', False)}**",
            f"- Schema errors: **{auto_fix.get('before_schema_error_count', 0)} -> {auto_fix.get('after_schema_error_count', 0)}**",
        ])
        lines.extend(
            f"- {item.get('code')}: {item.get('message')} ({item.get('location')})"
            for item in auto_fix.get("applied_fixes", [])
        )
        lines.extend(["", "## Cross-reference Checks", ""])
        lines.extend(f"- {item}" for item in validation.get("xref_checks", []))
        if not validation.get("xref_checks"):
            lines.append("- None")
        return "\n".join(lines) + "\n"
