import re
from typing import Any


class ContributorNormalizer:
    """Remove conservative trailing affiliation markers from contributor names."""

    MARKER_RE = re.compile(r"(?P<markers>[⁰¹²³⁴⁵⁶⁷⁸⁹*†‡]+)$")

    def normalize(self, author: dict[str, Any]) -> dict[str, Any]:
        result = dict(author)
        original = str(result.get("name", "")).strip()
        match = self.MARKER_RE.search(original)
        if not match:
            result.setdefault("original_name", "")
            result.setdefault("markers", [])
            result.setdefault("normalization_status", "unchanged")
            return result

        marker_text = match.group("markers")
        result["name"] = original[:match.start()].rstrip()
        result["original_name"] = original
        result["markers"] = list(marker_text)
        result["normalization_status"] = "normalized"
        return result
