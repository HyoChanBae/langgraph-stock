"""원시 지표를 5대 축(금리·물가·달러·유가·고용) 신호로 정규화한다. LLM 없이 결정론적으로 계산한다."""

import logging
import math


logger = logging.getLogger(__name__)

NA = "N/A (평가 불가)"

# 축이 유효하다고 보려면 가중치 기준 이만큼은 채워져야 한다.
MIN_COVERAGE = 0.5

# 점수 절댓값이 이보다 작으면 방향을 중립으로 본다.
NEUTRAL_BAND = 0.25

AXIS_LABELS = {
    "rates": "금리",
    "inflation": "물가",
    "dollar": "달러",
    "oil": "유가",
    "employment": "고용",
}

DIRECTION_LABELS = {
    "rates": ("상승", "하락", "횡보"),
    "inflation": ("가속", "둔화", "안정"),
    "dollar": ("강세", "약세", "횡보"),
    "oil": ("상승", "하락", "횡보"),
    "employment": ("개선", "둔화", "보합"),
}


def _squash(value: float | None, scale: float) -> float | None:
    """변화량을 -1~+1로 압축한다. scale은 '1 표준적 움직임'에 해당하는 크기."""
    if value is None or not scale:
        return None
    return math.tanh(value / scale)


def _weighted(parts: list[tuple[float, float | None]]) -> tuple[float | None, float]:
    """(가중치, 점수) 목록에서 결측을 빼고 가중평균과 커버리지를 구한다."""
    total_weight = sum(weight for weight, _ in parts)
    used = [(weight, score) for weight, score in parts if score is not None]
    if not used or not total_weight:
        return None, 0.0

    used_weight = sum(weight for weight, _ in used)
    score = sum(weight * score for weight, score in used) / used_weight
    return score, used_weight / total_weight


def _get(source: dict | None, key: str, field: str = "value"):
    entry = (source or {}).get(key)
    if not isinstance(entry, dict):
        return None
    return entry.get(field)


def _pp(value: float | None, digits: int = 2) -> str:
    return NA if value is None else f"{value:+.{digits}f}%p"


def _bp(value: float | None) -> str:
    return NA if value is None else f"{value * 100:+.0f}bp"


def _pct(value: float | None) -> str:
    return NA if value is None else f"{value * 100:+.1f}%"


def _level(value: float | None, unit: str = "", digits: int = 2) -> str:
    return NA if value is None else f"{value:.{digits}f}{unit}"


def _direction(key: str, score: float | None) -> str:
    if score is None:
        return NA
    up, down, flat = DIRECTION_LABELS[key]
    if score > NEUTRAL_BAND:
        return up
    if score < -NEUTRAL_BAND:
        return down
    return flat


def _axis(key: str, score: float | None, coverage: float, level: str,
          chg_1m: str, chg_3m: str, components: dict, notes: list[str] | None = None) -> dict:
    available = score is not None and coverage >= MIN_COVERAGE
    # 커버리지 미달이어도 점수는 남긴다. 쓸지 말지는 available 을 보고 소비처가 정한다.
    return {
        "key": key,
        "label": AXIS_LABELS[key],
        "available": available,
        "score": None if score is None else round(score, 3),
        "coverage": round(coverage, 2),
        "direction": _direction(key, score) if available else NA,
        "level": level,
        "chg_1m": chg_1m,
        "chg_3m": chg_3m,
        "components": components,
        "notes": notes or [],
    }


def _rates_axis(market: dict, fred: dict) -> dict:
    nominal = market.get("ust_10y") or {}
    curve = market.get("curve_10y_3m") or {}
    real_3m = _get(fred, "real_yield_10y", "chg_3m")
    nominal_3m = nominal.get("diff_3m")

    # 실질금리 우선. 명목 상승이 성장 기대 때문인지 물가 때문인지 구분해야 듀레이션 민감 섹터를 제대로 본다.
    score, coverage = _weighted([
        (0.5, _squash(None if real_3m is None else real_3m * 100, 50.0)),
        (0.5, _squash(None if nominal_3m is None else nominal_3m * 100, 50.0)),
    ])

    notes = []
    curve_value = curve.get("value")
    if curve_value is not None and curve_value < 0:
        notes.append("장단기 금리 역전 지속")
    curve_3m = curve.get("diff_3m")
    if curve_3m is not None and curve_3m * 100 > 20:
        notes.append("커브 스티프닝 진행")

    return _axis(
        "rates",
        score,
        coverage,
        level=(
            f"10Y {_level(nominal.get('value'), '%')} / "
            f"실질 {_level(_get(fred, 'real_yield_10y'), '%')} / "
            f"10Y-3M {_level(curve_value, '%p')}"
        ),
        chg_1m=_bp(nominal.get("diff_1m")),
        chg_3m=_bp(nominal_3m),
        components={
            "nominal_10y": nominal.get("value"),
            "real_yield_10y": _get(fred, "real_yield_10y"),
            "curve_10y_3m": curve_value,
            "fed_funds": _get(fred, "fed_funds"),
            "fed_funds_chg_3m": _get(fred, "fed_funds", "chg_3m"),
        },
        notes=notes,
    )


def _inflation_axis(market: dict, fred: dict) -> dict:
    cpi_yoy = _get(fred, "cpi_yoy")
    core_yoy = _get(fred, "core_cpi_yoy")
    breakeven = _get(fred, "breakeven_10y")
    wti = market.get("wti") or {}

    score, coverage = _weighted([
        (0.4, _squash(_get(fred, "cpi_yoy", "chg_3m"), 0.5)),
        (0.3, _squash(_get(fred, "breakeven_10y", "chg_3m"), 0.25)),
        (0.3, _squash(wti.get("pct_3m"), 0.15)),
    ])

    notes = []
    if cpi_yoy is not None and cpi_yoy > 3.0:
        notes.append("헤드라인 CPI가 연준 목표를 크게 상회")
    if core_yoy is not None and cpi_yoy is not None and core_yoy > cpi_yoy + 0.3:
        notes.append("근원 물가가 헤드라인보다 경직적")

    return _axis(
        "inflation",
        score,
        coverage,
        level=(
            f"CPI {_level(cpi_yoy, '%', 1)} / "
            f"근원 {_level(core_yoy, '%', 1)} / "
            f"기대인플레 {_level(breakeven, '%')}"
        ),
        chg_1m=_pp(_get(fred, "cpi_yoy", "chg_1m")),
        chg_3m=_pp(_get(fred, "cpi_yoy", "chg_3m")),
        components={
            "cpi_yoy": cpi_yoy,
            "core_cpi_yoy": core_yoy,
            "breakeven_10y": breakeven,
            "breakeven_5y": _get(fred, "breakeven_5y"),
            "wti_pct_3m": wti.get("pct_3m"),
        },
        notes=notes,
    )


def _dollar_axis(market: dict) -> dict:
    dxy = market.get("dollar_index") or {}
    score, coverage = _weighted([
        (1.0, _squash(dxy.get("pct_3m"), 0.04)),
    ])

    return _axis(
        "dollar",
        score,
        coverage,
        level=f"달러인덱스 {_level(dxy.get('value'), '', 2)}",
        chg_1m=_pct(dxy.get("pct_1m")),
        chg_3m=_pct(dxy.get("pct_3m")),
        components={
            "dollar_index": dxy.get("value"),
            "pct_3m": dxy.get("pct_3m"),
        },
    )


def _oil_axis(market: dict) -> dict:
    wti = market.get("wti") or {}
    brent = market.get("brent") or {}
    score, coverage = _weighted([
        (1.0, _squash(wti.get("pct_3m"), 0.15)),
    ])

    notes = []
    pct_3m = wti.get("pct_3m")
    if pct_3m is not None and pct_3m > 0.15:
        notes.append("3개월 15% 이상 급등 — 공급 충격 경계")
    if pct_3m is not None and pct_3m < -0.15:
        notes.append("3개월 15% 이상 급락 — 수요 둔화 신호 가능")

    return _axis(
        "oil",
        score,
        coverage,
        level=f"WTI {_level(wti.get('value'), '달러')} / 브렌트 {_level(brent.get('value'), '달러')}",
        chg_1m=_pct(wti.get("pct_1m")),
        chg_3m=_pct(pct_3m),
        components={
            "wti": wti.get("value"),
            "brent": brent.get("value"),
            "pct_3m": pct_3m,
        },
        notes=notes,
    )


def _employment_axis(fred: dict) -> dict:
    unemployment = _get(fred, "unemployment")
    unemployment_3m = _get(fred, "unemployment", "chg_3m")
    payroll_avg = (fred or {}).get("payroll_3m_avg")
    claims_3m = _get(fred, "initial_claims", "chg_3m")
    claims_level = _get(fred, "initial_claims")
    sahm_gap = (fred or {}).get("sahm_gap")

    claims_pct = None
    if claims_3m is not None and claims_level:
        base = claims_level - claims_3m
        claims_pct = claims_3m / base if base else None

    # 실업률 상승과 청구건수 증가는 악재이므로 부호를 뒤집는다.
    score, coverage = _weighted([
        (0.3, None if unemployment_3m is None else -(_squash(unemployment_3m, 0.3) or 0.0)),
        (0.4, None if payroll_avg is None else _squash(payroll_avg - 150.0, 120.0)),
        (0.3, None if claims_pct is None else -(_squash(claims_pct, 0.10) or 0.0)),
    ])

    notes = []
    if sahm_gap is not None and sahm_gap >= 0.5:
        notes.append(f"Sahm rule 발동 (갭 {sahm_gap:+.2f}%p) — 침체 진입 신호")
        if score is not None:
            score = min(score, -0.6)
    elif sahm_gap is not None and sahm_gap >= 0.3:
        notes.append(f"Sahm rule 임계치 접근 (갭 {sahm_gap:+.2f}%p)")

    return _axis(
        "employment",
        score,
        coverage,
        level=(
            f"실업률 {_level(unemployment, '%', 1)} / "
            f"비농업 3개월 평균 {NA if payroll_avg is None else f'{payroll_avg:+.0f}천명'}"
        ),
        chg_1m=_pp(_get(fred, "unemployment", "chg_1m"), 1),
        chg_3m=_pp(unemployment_3m, 1),
        components={
            "unemployment": unemployment,
            "payroll_3m_avg": payroll_avg,
            "initial_claims_4w_avg": (fred or {}).get("initial_claims_4w_avg"),
            "claims_pct_3m": claims_pct,
            "sahm_gap": sahm_gap,
        },
        notes=notes,
    )


def _internals(market: dict) -> dict:
    """레짐 판정의 성장 축을 보강하는 시장 내부 지표. 5대 축과 달리 리포트 전면에는 쓰지 않는다."""
    copper_gold = market.get("copper_gold") or {}
    curve = market.get("curve_10y_3m") or {}
    credit = market.get("credit_proxy") or {}
    vix = market.get("vix") or {}

    curve_3m = curve.get("diff_3m")
    return {
        "copper_gold": {
            "value": copper_gold.get("value"),
            "pct_3m": copper_gold.get("pct_3m"),
            "score": _squash(copper_gold.get("pct_3m"), 0.08),
        },
        "curve_steepening": {
            "value": curve.get("value"),
            "diff_3m": curve_3m,
            "score": _squash(None if curve_3m is None else curve_3m * 100, 40.0),
        },
        "credit": {
            "value": credit.get("value"),
            "pct_3m": credit.get("pct_3m"),
            "score": _squash(credit.get("pct_3m"), 0.03),
        },
        "vix": {
            "value": vix.get("value"),
            "score": _squash(None if vix.get("value") is None else 20.0 - vix["value"], 10.0),
        },
    }


def compute_signals(market: dict, fred: dict) -> tuple[dict, list[str]]:
    """5대 축 신호와, 평가 불가로 빠진 축 목록을 반환한다."""
    signals = {
        "rates": _rates_axis(market, fred),
        "inflation": _inflation_axis(market, fred),
        "dollar": _dollar_axis(market),
        "oil": _oil_axis(market),
        "employment": _employment_axis(fred),
        "internals": _internals(market),
    }

    missing = [key for key in AXIS_LABELS if not signals[key]["available"]]
    if missing:
        logger.warning("[Signals] 평가 불가 축: %s", ", ".join(AXIS_LABELS[key] for key in missing))

    logger.info("[Signals] %s개 축 산출 완료", len(AXIS_LABELS) - len(missing))
    return signals, missing
