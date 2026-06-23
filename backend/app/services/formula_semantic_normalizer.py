import re
from difflib import SequenceMatcher
from typing import Any


class FormulaSemanticNormalizer:
    """Normalize formula labels and duplicated fallback representations."""

    LEADING_LABEL_RE = re.compile(r"^\s*(?P<label>\(\s*\d+\s*\))\s*")
    TRAILING_LABEL_RE = re.compile(r"\s*(?P<label>\(\s*\d+\s*\))\s*$")
    SPACE_RE = re.compile(r"\s+")
    TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)

    def normalize(self, formula: dict[str, Any]) -> dict[str, Any]:
        result = dict(formula)
        original = str(result.get("content", ""))
        content = original.strip()
        label = str(result.get("label", "")).strip()
        changed = False

        if not label:
            leading = self.LEADING_LABEL_RE.match(content)
            trailing = self.TRAILING_LABEL_RE.search(content)
            match = leading or trailing
            if match:
                label = self.SPACE_RE.sub("", match.group("label"))
                content = (content[:match.start()] + content[match.end():]).strip()
                changed = True

        latex = str(result.get("latex", "")).strip()
        deduplicated = self._strip_duplicate_suffix(content, latex)
        if deduplicated != content:
            content = deduplicated
            changed = True

        result["label"] = label
        result["content"] = self.SPACE_RE.sub(" ", content).strip()
        result["original_content"] = original if changed else ""
        result["normalization_status"] = "normalized" if changed else "unchanged"

        if content and latex and self._similarity(content, latex) < 0.25:
            result["conversion_status"] = "partial"
            issues = list(result.get("issues", []))
            issues.append({
                "code": "formula_representation_conflict",
                "level": "warning",
                "message": "公式可见文本与 LaTeX 回退内容差异较大，需要人工复核。",
                "suggestion": "核对 MathML、LaTeX 与原始 Word 公式后再交付。",
            })
            result["issues"] = issues
        return result

    @classmethod
    def _strip_duplicate_suffix(cls, content: str, suffix: str) -> str:
        if not suffix:
            return content
        if content.endswith(suffix):
            prefix = content[:-len(suffix)].rstrip()
            return prefix or content

        content_index = len(content) - 1
        suffix_index = len(suffix) - 1
        while suffix_index >= 0:
            while suffix_index >= 0 and suffix[suffix_index].isspace():
                suffix_index -= 1
            while content_index >= 0 and content[content_index].isspace():
                content_index -= 1
            if suffix_index < 0:
                break
            if content_index < 0 or content[content_index] != suffix[suffix_index]:
                return content
            content_index -= 1
            suffix_index -= 1
        prefix = content[:content_index + 1].rstrip()
        return prefix or content

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        left_key = "".join(cls.TOKEN_RE.findall(left.casefold()))
        right_key = "".join(cls.TOKEN_RE.findall(right.casefold()))
        if not left_key or not right_key:
            return 0.0
        return SequenceMatcher(None, left_key, right_key).ratio()
