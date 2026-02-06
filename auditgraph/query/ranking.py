from __future__ import annotations

from typing import Iterable


def round_score(score: float, rounding: float) -> float:
    if rounding <= 0:
        return score
    return round(score / rounding) * rounding


def _tie_break_key(item: dict[str, object]) -> tuple:
    explanation = item.get("explanation", {})
    tie_break = explanation.get("tie_break", []) if isinstance(explanation, dict) else []
    if isinstance(tie_break, list) and tie_break:
        return tuple(str(entry) for entry in tie_break)
    return (str(item.get("id", "")),)


def apply_ranking(results: Iterable[dict[str, object]], rounding: float) -> list[dict[str, object]]:
    ranked = []
    for item in results:
        score = float(item.get("score", 0.0))
        item = dict(item)
        item["score"] = round_score(score, rounding)
        ranked.append(item)
    return sorted(
        ranked,
        key=lambda r: (-float(r.get("score", 0.0)), _tie_break_key(r)),
    )
