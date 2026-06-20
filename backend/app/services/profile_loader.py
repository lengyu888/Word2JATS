from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class ProfileLoader:
    def __init__(self, profiles_dir: str | Path | None = None):
        self.profiles_dir = Path(profiles_dir or Path(__file__).resolve().parents[2] / "profiles")

    def list_profiles(self) -> list[dict[str, Any]]:
        profiles = []
        for path in sorted(self.profiles_dir.glob("*.yaml")):
            profile = self.load(path.stem)
            profiles.append({
                "id": path.stem,
                "label": profile.get("profile_name") or path.stem,
                "journal_title": profile.get("journal_title", ""),
                "lang": profile.get("lang", ""),
            })
        return profiles

    def load(self, name: str = "default") -> dict[str, Any]:
        safe_name = Path(name or "default").stem
        path = self.profiles_dir / f"{safe_name}.yaml"
        if not path.exists():
            raise ValueError(f"Unknown journal profile: {safe_name}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Invalid journal profile: {safe_name}")
        data["id"] = safe_name
        return data

    @staticmethod
    def apply_metadata(article: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(article)
        for field in (
            "journal_title", "journal_id", "issn", "publisher_name", "article_type", "lang", "subject"
        ):
            if not result.get(field) and profile.get(field):
                result[field] = profile[field]
        result["profile"] = profile.get("id", "default")
        return result
