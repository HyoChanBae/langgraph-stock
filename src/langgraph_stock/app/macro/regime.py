"""5대 축 신호를 성장×물가 2축으로 압축해 경제 레짐을 판정한다."""

import logging
import math


logger = logging.getLogger(__name__)

# 성장 축 구성: 고용이 주도하고 시장 내부 지표가 선행 신호를 보강한다.
GROWTH_WEIGHTS = {
    "employment": 0.40,
    "copper_gold": 0.30,
    "curve_steepening": 0.15,
    "credit": 0.15,
}

REGIMES = {
    "GOLDILOCKS": {
        "name": "골디락스",
        "summary": "성장은 버티고 물가는 내려가는, 위험자산에 가장 우호적인 조합",
    },
    "REFLATION": {
        "name": "리플레이션",
        "summary": "성장과 물가가 함께 올라가는, 실물·경기민감 자산이 앞서는 조합",
    },
    "STAGFLATION": {
        "name": "스태그플레이션",
        "summary": "성장은 꺾이는데 물가는 버티는, 방어와 실물자산이 동시에 필요한 조합",
    },
    "SLOWDOWN": {
        "name": "둔화·디스인플레",
        "summary": "성장과 물가가 함께 내려가는, 금리 민감 방어주와 채권이 앞서는 조합",
    },
    "UNRESOLVED": {
        "name": "판정 보류",
        "summary": "성장 또는 물가 축을 산출할 수 없어 4분면 중 어디인지 특정하지 못하는 상태",
    },
}

# 원점에서 이만큼 떨어져야 판정을 온전히 신뢰한다.
FULL_CONFIDENCE_DISTANCE = 0.5

# 축 커버리지가 이보다 낮으면 판정에 쓰되 경고를 남긴다.
MIN_AXIS_COVERAGE = 0.5

MODIFIER_THRESHOLD = 0.3


def _growth_score(signals: dict) -> tuple[float | None, float]:
    internals = signals.get("internals") or {}
    employment = signals.get("employment") or {}
    employment_score = employment.get("score") if employment.get("available") else None

    parts = [
        (GROWTH_WEIGHTS["employment"], employment_score),
        (GROWTH_WEIGHTS["copper_gold"], (internals.get("copper_gold") or {}).get("score")),
        (GROWTH_WEIGHTS["curve_steepening"], (internals.get("curve_steepening") or {}).get("score")),
        (GROWTH_WEIGHTS["credit"], (internals.get("credit") or {}).get("score")),
    ]

    total_weight = sum(weight for weight, _ in parts)
    used = [(weight, score) for weight, score in parts if score is not None]
    if not used:
        return None, 0.0

    used_weight = sum(weight for weight, _ in used)
    score = sum(weight * score for weight, score in used) / used_weight
    return score, used_weight / total_weight


def _quadrant(growth: float, inflation: float) -> str:
    if growth >= 0:
        return "REFLATION" if inflation >= 0 else "GOLDILOCKS"
    return "STAGFLATION" if inflation >= 0 else "SLOWDOWN"


def _modifiers(signals: dict) -> list[dict]:
    """섹터 점수를 보정하는 유동성·가격 조건."""
    found = []

    def score_of(key: str) -> float | None:
        axis = signals.get(key) or {}
        return axis.get("score") if axis.get("available") else None

    dollar = score_of("dollar")
    if dollar is not None and dollar > MODIFIER_THRESHOLD:
        found.append({"key": "dollar_strong", "label": "달러 강세 — 원자재·수출 섹터에 부담"})
    elif dollar is not None and dollar < -MODIFIER_THRESHOLD:
        found.append({"key": "dollar_weak", "label": "달러 약세 — 원자재·소재 섹터에 우호적"})

    rates = score_of("rates")
    if rates is not None and rates > MODIFIER_THRESHOLD:
        found.append({"key": "real_rate_rising", "label": "실질금리 상승 — 듀레이션 긴 성장주·리츠에 부담"})
    elif rates is not None and rates < -MODIFIER_THRESHOLD:
        found.append({"key": "real_rate_falling", "label": "실질금리 하락 — 성장주·리츠·금에 우호적"})

    oil = score_of("oil")
    if oil is not None and oil > 0.6:
        found.append({"key": "oil_shock", "label": "유가 급등 — 에너지 수혜, 운송·소비재 마진 압박"})

    curve = ((signals.get("internals") or {}).get("curve_steepening") or {}).get("score")
    if curve is not None and curve > MODIFIER_THRESHOLD:
        found.append({"key": "curve_steepening", "label": "수익률곡선 스티프닝 — 은행 순이자마진에 우호적"})

    return found


def classify_regime(signals: dict) -> dict:
    """성장/물가 점수와 신뢰도, 보정 조건을 담은 레짐 판정을 반환한다."""
    growth, growth_coverage = _growth_score(signals)

    # 물가는 커버리지가 낮아도 있는 만큼 쓴다. 0으로 채우면 두 분면의 경계에 억지로 세우게 된다.
    inflation_axis = signals.get("inflation") or {}
    inflation = inflation_axis.get("score")
    inflation_coverage = inflation_axis.get("coverage") or 0.0

    available_axes = sum(
        1 for name in ("rates", "inflation", "dollar", "oil", "employment")
        if (signals.get(name) or {}).get("available")
    )

    caveats = []
    if inflation_coverage and inflation_coverage < MIN_AXIS_COVERAGE:
        caveats.append(
            f"물가 축이 구성 지표의 {inflation_coverage:.0%}만으로 산출됨 — 분면 판정이 뒤집힐 수 있음"
        )
    if growth_coverage and growth_coverage < MIN_AXIS_COVERAGE:
        caveats.append(
            f"성장 축이 구성 지표의 {growth_coverage:.0%}만으로 산출됨 — 분면 판정이 뒤집힐 수 있음"
        )

    if growth is None or inflation is None:
        missing_axis = "성장" if growth is None else "물가"
        logger.warning("[Regime] %s 축을 산출하지 못해 레짐을 보류합니다", missing_axis)
        caveats.append(f"{missing_axis} 축을 전혀 산출하지 못해 섹터 선호도 보정을 적용하지 않음")

        key = "UNRESOLVED"
        growth_value = growth if growth is not None else 0.0
        inflation_value = inflation if inflation is not None else 0.0
        confidence = 0.0
    else:
        growth_value = growth
        inflation_value = inflation
        key = _quadrant(growth_value, inflation_value)
        distance = math.hypot(growth_value, inflation_value)
        confidence = min(1.0, distance / FULL_CONFIDENCE_DISTANCE) * (available_axes / 5.0)

    regime = {
        "key": key,
        "name": REGIMES[key]["name"],
        "summary": REGIMES[key]["summary"],
        "growth_score": round(growth_value, 3),
        "inflation_score": round(inflation_value, 3),
        "growth_coverage": round(growth_coverage, 2),
        "inflation_coverage": round(inflation_coverage, 2),
        "available_axes": available_axes,
        "distance": round(math.hypot(growth_value, inflation_value), 3),
        "confidence": round(confidence, 2),
        "modifiers": _modifiers(signals),
        "caveats": caveats,
    }

    logger.info(
        "[Regime] %s (성장 %+.2f, 물가 %+.2f, 신뢰도 %.2f)",
        regime["name"],
        regime["growth_score"],
        regime["inflation_score"],
        regime["confidence"],
    )
    return regime
