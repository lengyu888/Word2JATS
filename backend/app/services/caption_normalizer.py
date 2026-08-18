import re


class CaptionNormalizer:
    """Split supported float labels from editable caption prose."""

    FIGURE_RE = re.compile(
        r"^\s*((?:fig(?:ure)?\.?|scheme)\s*\d+(?:[-.]\d+)?|图\s*\d+(?:[-－.]\d+)?)"
        r"\s*[:：.．-]?\s*",
        re.I,
    )
    TABLE_RE = re.compile(
        r"^\s*(table\s*\d+(?:[-.]\d+)?|表\s*\d+(?:[-－.]\d+)?)"
        r"\s*[:：.．-]?\s*",
        re.I,
    )

    def split(self, text: str, object_type: str) -> dict[str, str]:
        original = str(text or "").strip()
        pattern = self.FIGURE_RE if object_type == "figure" else self.TABLE_RE
        match = pattern.match(original)
        if not match:
            return {"label": "", "caption": original, "status": "unchanged"}

        body = original[match.end():].strip()
        return {
            "label": match.group(1).strip().rstrip(".:：．-"),
            "caption": body,
            "status": "normalized" if body else "need_review",
        }
