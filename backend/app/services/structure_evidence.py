from typing import Any


class StructureEvidence:
    """Score structural relationships without reparsing the source document."""

    OK_THRESHOLD = 0.80
    REVIEW_THRESHOLD = 0.50

    @classmethod
    def status_for(cls, confidence: float) -> str:
        if confidence >= cls.OK_THRESHOLD:
            return "ok"
        if confidence >= cls.REVIEW_THRESHOLD:
            return "need_review"
        return "warning"

    def score_binding(
        self,
        *,
        object_type: str,
        same_section: bool,
        distance: int | None,
        number_match: bool,
        explicit_caption: bool,
    ) -> dict[str, Any]:
        if not same_section:
            return {
                "confidence": 0.0,
                "status": "error",
                "evidence": [],
                "issues": [{
                    "level": "error",
                    "message": f"{object_type} 候选对象与题注跨章节，已拒绝自动绑定。",
                    "suggestion": "请在人工校正页面确认对象归属。",
                }],
            }

        score = 0.30
        evidence = ["位于同一章节"]
        if explicit_caption:
            score += 0.20
            evidence.append("识别到显式题注")
        if number_match:
            score += 0.35
            evidence.append("编号一致")
        if distance is not None and distance <= 1:
            score += 0.15
            evidence.append("文档流距离不超过 1 个节点")
        elif distance is not None and distance <= 3:
            score += 0.05
            evidence.append("文档流距离不超过 3 个节点")

        confidence = round(min(score, 1.0), 2)
        return {
            "confidence": confidence,
            "status": self.status_for(confidence),
            "evidence": evidence,
            "issues": [],
        }

    def review_result(
        self, message: str, suggestion: str, confidence: float = 0.60
    ) -> dict[str, Any]:
        return {
            "confidence": confidence,
            "status": "need_review",
            "evidence": [],
            "issues": [{
                "level": "warning",
                "message": message,
                "suggestion": suggestion,
            }],
        }
