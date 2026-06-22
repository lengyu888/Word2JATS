import re
from typing import Any


class FloatCandidateMatcher:
    """Match float captions to existing flow objects using local evidence."""

    ACCEPT_THRESHOLD = 0.80
    UNIQUE_MARGIN = 0.15

    def match(
        self,
        captions: list[dict[str, Any]],
        objects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results = []
        used_ids: set[str] = set()
        for caption in captions:
            candidates = [
                self._score(caption, obj)
                for obj in objects
                if obj.get("id") not in used_ids
                and obj.get("section_index") == caption.get("section_index")
            ]
            candidates.sort(key=lambda item: item["confidence"], reverse=True)
            best = candidates[0] if candidates else None
            second_score = candidates[1]["confidence"] if len(candidates) > 1 else 0.0
            if (
                best
                and best["confidence"] >= self.ACCEPT_THRESHOLD
                and best["confidence"] - second_score >= self.UNIQUE_MARGIN - 1e-9
            ):
                used_ids.add(best["object_id"])
                results.append(best)
            else:
                results.append(self._review_result(caption, best))
        return results

    def _score(
        self, caption: dict[str, Any], obj: dict[str, Any]
    ) -> dict[str, Any]:
        score = 0.35
        evidence = ["位于同一章节"]
        number = str(caption.get("number", "")).casefold()
        object_number = self._object_number(str(obj.get("id", "")))
        if number and number == object_number:
            score += 0.35
            evidence.append("编号一致")

        distance = abs(
            int(caption.get("flow_index", 0)) - int(obj.get("flow_index", 0))
        )
        if distance <= 1:
            score += 0.20
            evidence.append("文档流距离不超过 1 个节点")
        elif distance <= 3:
            score += 0.10
            evidence.append("文档流距离不超过 3 个节点")

        table_screenshot = (
            caption.get("kind") == "table"
            and obj.get("kind") == "image"
            and distance <= 3
            and number != object_number
        )
        compatible = (
            caption.get("kind") == "figure" and obj.get("kind") == "image"
        ) or (
            caption.get("kind") == "table" and obj.get("kind") == "table"
        )
        if table_screenshot:
            score += 0.40 if distance <= 1 else 0.35
            evidence.append("紧邻表题的表格截图候选")
        elif compatible:
            score += 0.15
            evidence.append("对象类型与题注一致")
        else:
            score -= 0.10

        confidence = round(max(0.0, min(score, 1.0)), 2)
        return {
            "caption_flow_index": caption.get("flow_index"),
            "object_id": obj.get("id"),
            "confidence": confidence,
            "status": "ok" if confidence >= self.ACCEPT_THRESHOLD else "need_review",
            "evidence": evidence,
            "issues": [],
        }

    @staticmethod
    def _object_number(object_id: str) -> str:
        match = re.search(r"(\d+(?:[-.]\d+)?[a-z]?)$", object_id, re.I)
        return match.group(1).casefold() if match else ""

    @staticmethod
    def _review_result(
        caption: dict[str, Any], best: dict[str, Any] | None
    ) -> dict[str, Any]:
        return {
            "caption_flow_index": caption.get("flow_index"),
            "object_id": None,
            "confidence": best["confidence"] if best else 0.0,
            "status": "need_review",
            "evidence": best["evidence"] if best else [],
            "issues": [{
                "level": "warning",
                "message": "题注缺少唯一且高置信的绑定对象。",
                "suggestion": "请在人工校正页面确认题注对应的图片或表格。",
            }],
        }
