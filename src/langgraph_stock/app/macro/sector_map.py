"""매크로 신호와 레짐을 SPDR 11개 섹터의 macro_score(0~30)로 변환한다."""

import logging


logger = logging.getLogger(__name__)

SECTORS = [
    {"etf": "XLK", "name": "기술"},
    {"etf": "XLC", "name": "커뮤니케이션"},
    {"etf": "XLY", "name": "경기소비재"},
    {"etf": "XLF", "name": "금융"},
    {"etf": "XLI", "name": "산업재"},
    {"etf": "XLE", "name": "에너지"},
    {"etf": "XLB", "name": "소재"},
    {"etf": "XLP", "name": "필수소비재"},
    {"etf": "XLV", "name": "헬스케어"},
    {"etf": "XLU", "name": "유틸리티"},
    {"etf": "XLRE", "name": "리츠"},
]

# 각 축이 +1(상승/강세/개선) 방향으로 움직일 때 해당 섹터가 받는 영향.
SECTOR_SENSITIVITY = {
    "XLK": {"rates": -0.8, "dollar": +0.1, "oil": -0.2, "growth": +0.9, "inflation": -0.4},
    "XLC": {"rates": -0.5, "dollar": +0.1, "oil": -0.1, "growth": +0.7, "inflation": -0.3},
    "XLY": {"rates": -0.6, "dollar": +0.2, "oil": -0.5, "growth": +0.9, "inflation": -0.5},
    "XLF": {"rates": +0.6, "dollar": +0.1, "oil": +0.0, "growth": +0.6, "inflation": +0.1},
    "XLI": {"rates": -0.2, "dollar": -0.3, "oil": -0.4, "growth": +0.8, "inflation": +0.2},
    "XLE": {"rates": +0.2, "dollar": -0.6, "oil": +1.0, "growth": +0.5, "inflation": +0.8},
    "XLB": {"rates": -0.1, "dollar": -0.7, "oil": +0.3, "growth": +0.7, "inflation": +0.6},
    "XLP": {"rates": -0.3, "dollar": +0.3, "oil": -0.3, "growth": -0.4, "inflation": +0.1},
    "XLV": {"rates": -0.3, "dollar": +0.2, "oil": -0.1, "growth": -0.2, "inflation": +0.0},
    "XLU": {"rates": -0.9, "dollar": +0.2, "oil": -0.2, "growth": -0.5, "inflation": -0.1},
    "XLRE": {"rates": -1.0, "dollar": +0.1, "oil": -0.2, "growth": +0.3, "inflation": +0.2},
}

# 4분면 레짐별 선호도. 민감도 내적만으로는 안 잡히는 역사적 로테이션 패턴을 반영한다.
REGIME_TILT = {
    "GOLDILOCKS": {
        "XLK": +1.0, "XLY": +0.9, "XLC": +0.7, "XLI": +0.3, "XLRE": +0.2, "XLF": +0.1,
        "XLB": +0.0, "XLE": -0.3, "XLV": -0.4, "XLU": -0.6, "XLP": -0.7,
    },
    "REFLATION": {
        "XLE": +1.0, "XLB": +0.9, "XLF": +0.8, "XLI": +0.7, "XLY": +0.1, "XLC": +0.0,
        "XLK": -0.1, "XLRE": -0.2, "XLV": -0.4, "XLP": -0.6, "XLU": -0.7,
    },
    "STAGFLATION": {
        "XLE": +1.0, "XLP": +0.6, "XLV": +0.5, "XLU": +0.2, "XLB": +0.1, "XLF": -0.3,
        "XLC": -0.4, "XLRE": -0.5, "XLI": -0.5, "XLK": -0.6, "XLY": -0.9,
    },
    "SLOWDOWN": {
        "XLU": +0.9, "XLP": +0.9, "XLV": +0.7, "XLRE": +0.3, "XLK": +0.0, "XLC": -0.1,
        "XLY": -0.4, "XLF": -0.5, "XLI": -0.6, "XLB": -0.8, "XLE": -0.9,
    },
}

SENSITIVITY_WEIGHT = 0.65
TILT_WEIGHT = 0.35

MAX_MACRO_SCORE = 30

# 성장 축은 여러 지표를 섞어 만들다 보니 절댓값이 작게 나온다. 5대 축보다 좁은 밴드를 쓴다.
GROWTH_PHRASE_BAND = 0.15

AXIS_NAMES = {
    "rates": "금리",
    "inflation": "물가",
    "dollar": "달러",
    "oil": "유가",
    "growth": "성장",
}


def _axis_scores(signals: dict, regime: dict) -> dict[str, float]:
    """민감도 내적에 쓸 축별 점수. 평가 불가 축은 아예 뺀다."""
    scores = {}
    for key in ("rates", "inflation", "dollar", "oil"):
        axis = signals.get(key) or {}
        if axis.get("available") and axis.get("score") is not None:
            scores[key] = axis["score"]

    if regime.get("growth_coverage"):
        scores["growth"] = regime["growth_score"]

    return scores


def _state_phrase(axis_key: str, signals: dict, regime: dict) -> str:
    if axis_key == "growth":
        score = regime.get("growth_score") or 0.0
        if score > GROWTH_PHRASE_BAND:
            return "성장 개선"
        if score < -GROWTH_PHRASE_BAND:
            return "성장 둔화"
        return "성장 보합"

    axis = signals.get(axis_key) or {}
    return f"{AXIS_NAMES[axis_key]} {axis.get('direction') or '중립'}"


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_sectors(signals: dict, regime: dict) -> list[dict]:
    """섹터별 macro_score와 유리/부담 요인을 점수 내림차순으로 반환한다."""
    axis_scores = _axis_scores(signals, regime)
    tilts = REGIME_TILT.get(regime.get("key"), {})

    if not axis_scores:
        logger.warning("[SectorMap] 사용할 수 있는 축이 없어 레짐 선호도만으로 점수를 냅니다")

    results = []
    for sector in SECTORS:
        etf = sector["etf"]
        sensitivity = SECTOR_SENSITIVITY[etf]

        contributions = {
            axis: sensitivity[axis] * score
            for axis, score in axis_scores.items()
        }
        weight_sum = sum(abs(sensitivity[axis]) for axis in axis_scores)
        raw = sum(contributions.values()) / weight_sum if weight_sum else 0.0

        tilt = tilts.get(etf, 0.0)
        combined = _clamp(SENSITIVITY_WEIGHT * raw + TILT_WEIGHT * tilt)
        macro_score = round((MAX_MACRO_SCORE / 2) * (1.0 + combined))

        ranked = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
        drivers = [_state_phrase(axis, signals, regime) for axis, value in ranked if value > 0.05][:2]
        headwinds = [_state_phrase(axis, signals, regime) for axis, value in reversed(ranked) if value < -0.05][:2]
        watch = max(sensitivity, key=lambda axis: abs(sensitivity[axis]))

        results.append({
            "sector": sector["name"],
            "sector_etf": etf,
            "macro_score": macro_score,
            "combined": round(combined, 3),
            "sensitivity_score": round(raw, 3),
            "regime_tilt": tilt,
            "drivers": drivers,
            "headwinds": headwinds,
            "watch": AXIS_NAMES[watch],
            "contributions": {axis: round(value, 3) for axis, value in contributions.items()},
        })

    results.sort(key=lambda item: item["macro_score"], reverse=True)
    logger.info(
        "[SectorMap] %s개 섹터 점수 산출, 최상위 %s(%s)",
        len(results),
        results[0]["sector"],
        results[0]["macro_score"],
    )
    return results
