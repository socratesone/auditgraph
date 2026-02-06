from __future__ import annotations

from typing import Iterable


def round_score(score: float, rounding: float) -> float:
    if rounding <= 0:
        return score
    return round(score / rounding) * rounding


def apply_ranking(results: Iterable[dict[str, object]], rounding: float) -> list[dict[str, object]]:
    ranked = []
    for item in results:
        score = float(item.get("score", 0.0))
        item = dict(item)
        item["score"] = round_score(score, rounding)
        ranked.append(item)
    return sorted(ranked, key=lambda r: (-float(r.get("score", 0.0)), str(r.get("id", ""))))
