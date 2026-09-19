"""매크로 신호와 레짐을 섹터 macro_score(0~30)로 변환한다.

채점 유니버스는 2층이다. 1층은 SPDR 11개 부모, 2층은 부모와 축 노출이
갈리는 오버레이 19개다. 식별자는 ETF 티커와 분리된 key를 쓴다.
"""

import logging


logger = logging.getLogger(__name__)

_AXES = ("rates", "dollar", "oil", "growth", "inflation")
_REGIME_KEYS = ("GOLDILOCKS", "REFLATION", "STAGFLATION", "SLOWDOWN")

# parent가 None이면 1층(광의 섹터), 있으면 2층 오버레이.
SECTORS = [
    {"key": "XLK", "etf": "XLK", "name": "기술", "parent": None},
    {"key": "XLC", "etf": "XLC", "name": "커뮤니케이션", "parent": None},
    {"key": "XLY", "etf": "XLY", "name": "경기소비재", "parent": None},
    {"key": "XLF", "etf": "XLF", "name": "금융", "parent": None},
    {"key": "XLI", "etf": "XLI", "name": "산업재", "parent": None},
    {"key": "XLE", "etf": "XLE", "name": "에너지", "parent": None},
    {"key": "XLB", "etf": "XLB", "name": "소재", "parent": None},
    {"key": "XLP", "etf": "XLP", "name": "필수소비재", "parent": None},
    {"key": "XLV", "etf": "XLV", "name": "헬스케어", "parent": None},
    {"key": "XLU", "etf": "XLU", "name": "유틸리티", "parent": None},
    {"key": "XLRE", "etf": "XLRE", "name": "리츠", "parent": None},
    {"key": "AIHW", "etf": "SMH", "name": "AI 하드웨어", "parent": "XLK"},
    {"key": "DCPW", "etf": "GRID", "name": "데이터센터 전력·냉각", "parent": "XLK"},
    {"key": "CYBR", "etf": "CIBR", "name": "사이버보안", "parent": "XLK"},
    {"key": "TELC", "etf": "IYZ", "name": "통신", "parent": "XLC"},
    {"key": "AUTO", "etf": "DRIV", "name": "자동차·EV", "parent": "XLY"},
    {"key": "ECOM", "etf": "ONLN", "name": "전자상거래", "parent": "XLY"},
    {"key": "BANK", "etf": "KBE", "name": "은행", "parent": "XLF"},
    {"key": "PAY", "etf": "FINX", "name": "결제·핀테크", "parent": "XLF"},
    {"key": "BIOT", "etf": "XBI", "name": "바이오텍", "parent": "XLV"},
    {"key": "DEF", "etf": "ITA", "name": "방산", "parent": "XLI"},
    {"key": "ROBO", "etf": "BOTZ", "name": "자동화·로봇", "parent": "XLI"},
    {"key": "URAN", "etf": "URA", "name": "우라늄·원전", "parent": "XLE"},
    {"key": "RNEW", "etf": "ICLN", "name": "재생에너지·그리드", "parent": "XLU"},
    {"key": "COPP", "etf": "COPX", "name": "구리", "parent": "XLB"},
    {"key": "LITH", "etf": "LIT", "name": "리튬·배터리 금속", "parent": "XLB"},
    {"key": "DCRE", "etf": "SRVR", "name": "데이터센터 리츠", "parent": "XLRE"},
    {"key": "INRE", "etf": "INDS", "name": "산업 리츠", "parent": "XLRE"},
    {"key": "AIRL", "etf": "JETS", "name": "항공", "parent": "XLI"},
    {"key": "SHIP", "etf": "SEA", "name": "해운", "parent": "XLI"},
]

# 각 축이 +1(상승/강세/개선) 방향으로 움직일 때 해당 섹터가 받는 영향. 키는 ETF가 아니라 sector key.
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
    "AIHW": {"rates": -0.9, "dollar": +0.2, "oil": -0.1, "growth": +1.0, "inflation": -0.5},
    "DCPW": {"rates": -0.7, "dollar": +0.0, "oil": +0.2, "growth": +0.6, "inflation": +0.2},
    "CYBR": {"rates": -0.5, "dollar": +0.1, "oil": -0.1, "growth": +0.5, "inflation": -0.2},
    "TELC": {"rates": -0.6, "dollar": +0.2, "oil": -0.1, "growth": -0.2, "inflation": +0.1},
    "AUTO": {"rates": -0.5, "dollar": +0.1, "oil": -0.7, "growth": +0.8, "inflation": -0.3},
    "ECOM": {"rates": -0.7, "dollar": +0.2, "oil": -0.4, "growth": +0.9, "inflation": -0.4},
    "BANK": {"rates": +0.9, "dollar": +0.1, "oil": +0.0, "growth": +0.7, "inflation": +0.2},
    "PAY": {"rates": -0.6, "dollar": +0.2, "oil": -0.1, "growth": +0.8, "inflation": -0.3},
    "BIOT": {"rates": -0.8, "dollar": +0.2, "oil": -0.1, "growth": +0.4, "inflation": -0.2},
    "DEF": {"rates": -0.1, "dollar": +0.2, "oil": +0.1, "growth": +0.2, "inflation": +0.2},
    "ROBO": {"rates": -0.5, "dollar": -0.2, "oil": -0.3, "growth": +0.9, "inflation": +0.1},
    "URAN": {"rates": -0.2, "dollar": -0.3, "oil": +0.2, "growth": +0.4, "inflation": +0.4},
    "RNEW": {"rates": -0.8, "dollar": +0.0, "oil": -0.3, "growth": +0.3, "inflation": -0.1},
    "COPP": {"rates": -0.1, "dollar": -0.9, "oil": +0.2, "growth": +0.9, "inflation": +0.5},
    "LITH": {"rates": -0.2, "dollar": -0.6, "oil": -0.3, "growth": +0.8, "inflation": +0.3},
    "DCRE": {"rates": -1.0, "dollar": +0.1, "oil": -0.1, "growth": +0.6, "inflation": +0.1},
    "INRE": {"rates": -0.8, "dollar": -0.1, "oil": -0.2, "growth": +0.5, "inflation": +0.2},
    "AIRL": {"rates": -0.3, "dollar": +0.2, "oil": -1.0, "growth": +0.8, "inflation": -0.3},
    "SHIP": {"rates": -0.1, "dollar": -0.5, "oil": -0.4, "growth": +0.8, "inflation": +0.2},
}

# 4분면 레짐별 선호도. 민감도 내적만으로는 안 잡히는 역사적 로테이션 패턴을 반영한다.
REGIME_TILT = {
    "GOLDILOCKS": {
        "XLK": +1.0, "XLY": +0.9, "XLC": +0.7, "XLI": +0.3, "XLRE": +0.2, "XLF": +0.1,
        "XLB": +0.0, "XLE": -0.3, "XLV": -0.4, "XLU": -0.6, "XLP": -0.7,
        "AIHW": +1.0, "ECOM": +0.9, "PAY": +0.8, "ROBO": +0.8, "AUTO": +0.7, "AIRL": +0.7,
        "DCRE": +0.6, "DCPW": +0.5, "CYBR": +0.4, "INRE": +0.4, "BIOT": +0.3, "SHIP": +0.3,
        "LITH": +0.3, "BANK": +0.2, "RNEW": +0.2, "COPP": +0.1, "DEF": +0.0, "URAN": -0.2,
        "TELC": -0.5,
    },
    "REFLATION": {
        "XLE": +1.0, "XLB": +0.9, "XLF": +0.8, "XLI": +0.7, "XLY": +0.1, "XLC": +0.0,
        "XLK": -0.1, "XLRE": -0.2, "XLV": -0.4, "XLP": -0.6, "XLU": -0.7,
        "COPP": +1.0, "BANK": +0.9, "LITH": +0.8, "SHIP": +0.8, "ROBO": +0.6, "URAN": +0.5,
        "DCPW": +0.4, "AUTO": +0.4, "INRE": +0.3, "RNEW": +0.3, "AIHW": +0.2, "PAY": +0.2,
        "AIRL": +0.2, "ECOM": +0.1, "DEF": +0.1, "DCRE": -0.1, "CYBR": -0.2, "BIOT": -0.3,
        "TELC": -0.5,
    },
    "STAGFLATION": {
        "XLE": +1.0, "XLP": +0.6, "XLV": +0.5, "XLU": +0.2, "XLB": +0.1, "XLF": -0.3,
        "XLC": -0.4, "XLRE": -0.5, "XLI": -0.5, "XLK": -0.6, "XLY": -0.9,
        "URAN": +0.8, "DEF": +0.6, "TELC": +0.4, "COPP": +0.4, "CYBR": +0.2, "BIOT": +0.2,
        "DCPW": +0.1, "SHIP": -0.2, "RNEW": -0.2, "LITH": -0.2, "BANK": -0.3, "INRE": -0.4,
        "DCRE": -0.5, "ROBO": -0.5, "AIHW": -0.6, "AUTO": -0.7, "PAY": -0.7, "ECOM": -0.8,
        "AIRL": -1.0,
    },
    "SLOWDOWN": {
        "XLU": +0.9, "XLP": +0.9, "XLV": +0.7, "XLRE": +0.3, "XLK": +0.0, "XLC": -0.1,
        "XLY": -0.4, "XLF": -0.5, "XLI": -0.6, "XLB": -0.8, "XLE": -0.9,
        "TELC": +0.8, "CYBR": +0.6, "BIOT": +0.5, "RNEW": +0.5, "DEF": +0.4, "DCPW": +0.3,
        "DCRE": +0.2, "INRE": +0.1, "URAN": +0.1, "AIHW": -0.2, "ECOM": -0.4, "PAY": -0.5,
        "ROBO": -0.5, "BANK": -0.6, "AUTO": -0.7, "LITH": -0.7, "SHIP": -0.7, "COPP": -0.8,
        "AIRL": -0.8,
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

SECTOR_NAMES = {sector["key"]: sector["name"] for sector in SECTORS}


def _validate_universe() -> None:
    keys = [sector["key"] for sector in SECTORS]
    if len(keys) != len(set(keys)):
        raise ValueError("SECTORS key가 중복입니다")

    key_set = set(keys)
    if set(SECTOR_SENSITIVITY) != key_set:
        raise ValueError(
            "SECTOR_SENSITIVITY 키가 SECTORS와 다릅니다 "
            f"missing={key_set - set(SECTOR_SENSITIVITY)} extra={set(SECTOR_SENSITIVITY) - key_set}"
        )

    for sector in SECTORS:
        parent = sector["parent"]
        if parent is not None and parent not in key_set:
            raise ValueError(f"{sector['key']} parent={parent} 가 유니버스에 없습니다")
        sensitivity = SECTOR_SENSITIVITY[sector["key"]]
        if tuple(sensitivity) != _AXES and set(sensitivity) != set(_AXES):
            missing = set(_AXES) - set(sensitivity)
            extra = set(sensitivity) - set(_AXES)
            raise ValueError(f"{sector['key']} 민감도 축 오류 missing={missing} extra={extra}")

    if set(REGIME_TILT) != set(_REGIME_KEYS):
        raise ValueError("REGIME_TILT 레짐 키가 4분면과 다릅니다")

    for regime_key, tilts in REGIME_TILT.items():
        if set(tilts) != key_set:
            raise ValueError(
                f"{regime_key} tilt 키가 SECTORS와 다릅니다 "
                f"missing={key_set - set(tilts)} extra={set(tilts) - key_set}"
            )


_validate_universe()


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
        key = sector["key"]
        sensitivity = SECTOR_SENSITIVITY[key]
        parent_key = sector["parent"]

        contributions = {
            axis: sensitivity[axis] * score
            for axis, score in axis_scores.items()
        }
        weight_sum = sum(abs(sensitivity[axis]) for axis in axis_scores)
        raw = sum(contributions.values()) / weight_sum if weight_sum else 0.0

        tilt = tilts.get(key, 0.0)
        combined = _clamp(SENSITIVITY_WEIGHT * raw + TILT_WEIGHT * tilt)
        macro_score = round((MAX_MACRO_SCORE / 2) * (1.0 + combined))

        ranked = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
        drivers = [_state_phrase(axis, signals, regime) for axis, value in ranked if value > 0.05][:2]
        headwinds = [_state_phrase(axis, signals, regime) for axis, value in reversed(ranked) if value < -0.05][:2]
        watch = max(sensitivity, key=lambda axis: abs(sensitivity[axis]))

        results.append({
            "sector_key": key,
            "sector": sector["name"],
            "sector_etf": sector["etf"],
            "layer": "overlay" if parent_key else "parent",
            "parent_key": parent_key,
            "parent": SECTOR_NAMES.get(parent_key) if parent_key else None,
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
