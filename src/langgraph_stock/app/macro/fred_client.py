"""FRED(세인트루이스 연준) 시계열 조회. 물가/고용처럼 시장 가격으로 못 얻는 지표를 담당한다."""

import logging

import requests

from app.config import settings


logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
TIMEOUT_SEC = 15

# (조회 개수, 1개월 전 인덱스, 3개월 전 인덱스) - 발표 주기별 관측치 간격
DAILY = (300, 21, 63)
WEEKLY = (60, 4, 13)
MONTHLY = (40, 1, 3)

SERIES_SPEC = {
    "cpi": ("CPIAUCSL", MONTHLY),
    "core_cpi": ("CPILFESL", MONTHLY),
    "breakeven_5y": ("T5YIE", DAILY),
    "breakeven_10y": ("T10YIE", DAILY),
    "unemployment": ("UNRATE", MONTHLY),
    "payrolls": ("PAYEMS", MONTHLY),
    "initial_claims": ("ICSA", WEEKLY),
    "fed_funds": ("DFF", DAILY),
    "real_yield_10y": ("DFII10", DAILY),
}


def fetch_series(series_id: str, limit: int = 60) -> list[dict] | None:
    """관측치를 최신순으로 반환한다. 키가 없거나 조회에 실패하면 None."""
    if not settings.FRED_API_KEY:
        return None

    params = {
        "series_id": series_id,
        "api_key": settings.FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }

    try:
        response = requests.get(FRED_BASE_URL, params=params, timeout=TIMEOUT_SEC)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        logger.warning("[FRED] 조회 실패 series_id=%s", series_id, exc_info=True)
        return None

    observations = []
    for row in payload.get("observations") or []:
        raw = row.get("value")
        if raw in (None, "", "."):
            continue
        try:
            observations.append({"date": row.get("date"), "value": float(raw)})
        except (TypeError, ValueError):
            continue

    if not observations:
        logger.warning("[FRED] 유효한 관측치 없음 series_id=%s", series_id)
        return None

    return observations


def _at(observations: list[dict] | None, index: int) -> float | None:
    if not observations or index < 0 or index >= len(observations):
        return None
    return observations[index]["value"]


def _metric(observations: list[dict] | None, offset_1m: int, offset_3m: int) -> dict | None:
    """최신값과 1/3개월 전 대비 변화량(단위는 원 시계열과 동일)."""
    latest = _at(observations, 0)
    if latest is None:
        return None

    prev_1m = _at(observations, offset_1m)
    prev_3m = _at(observations, offset_3m)
    return {
        "value": latest,
        "chg_1m": None if prev_1m is None else latest - prev_1m,
        "chg_3m": None if prev_3m is None else latest - prev_3m,
        "as_of": observations[0]["date"],
    }


def _yoy_series(observations: list[dict] | None) -> list[dict] | None:
    """월간 지수 시계열을 전년동월비(%) 시계열로 바꾼다."""
    if not observations or len(observations) < 13:
        return None

    series = []
    for i in range(len(observations) - 12):
        base = observations[i + 12]["value"]
        if not base:
            continue
        series.append({
            "date": observations[i]["date"],
            "value": (observations[i]["value"] / base - 1.0) * 100.0,
        })
    return series or None


def _diff_series(observations: list[dict] | None) -> list[dict] | None:
    """레벨 시계열을 전기간 대비 증감 시계열로 바꾼다."""
    if not observations or len(observations) < 2:
        return None

    return [
        {
            "date": observations[i]["date"],
            "value": observations[i]["value"] - observations[i + 1]["value"],
        }
        for i in range(len(observations) - 1)
    ]


def _average(observations: list[dict] | None, count: int) -> float | None:
    if not observations or len(observations) < count:
        return None
    return sum(row["value"] for row in observations[:count]) / count


def _sahm_gap(unemployment: list[dict] | None) -> float | None:
    """실업률 3개월 이동평균에서 지난 12개월 최저치를 뺀 값. 0.5%p 이상이면 침체 진입 신호."""
    if not unemployment or len(unemployment) < 15:
        return None

    moving_average = []
    for i in range(13):
        window = unemployment[i:i + 3]
        if len(window) < 3:
            break
        moving_average.append(sum(row["value"] for row in window) / 3)

    if len(moving_average) < 13:
        return None
    return moving_average[0] - min(moving_average)


def fetch_macro_bundle() -> dict:
    """물가/고용/정책금리 지표 묶음. 실패한 항목은 None으로 남는다."""
    if not settings.FRED_API_KEY:
        logger.warning("[FRED] FRED_API_KEY 가 없어 물가·고용 축을 건너뜁니다")
        return {"available": False}

    raw = {}
    for key, (series_id, (limit, _, _)) in SERIES_SPEC.items():
        raw[key] = fetch_series(series_id, limit)

    cpi_yoy = _yoy_series(raw["cpi"])
    core_cpi_yoy = _yoy_series(raw["core_cpi"])
    payroll_changes = _diff_series(raw["payrolls"])

    bundle = {
        "available": True,
        "cpi_yoy": _metric(cpi_yoy, *MONTHLY[1:]),
        "core_cpi_yoy": _metric(core_cpi_yoy, *MONTHLY[1:]),
        "breakeven_5y": _metric(raw["breakeven_5y"], *DAILY[1:]),
        "breakeven_10y": _metric(raw["breakeven_10y"], *DAILY[1:]),
        "unemployment": _metric(raw["unemployment"], *MONTHLY[1:]),
        "initial_claims": _metric(raw["initial_claims"], *WEEKLY[1:]),
        "fed_funds": _metric(raw["fed_funds"], *DAILY[1:]),
        "real_yield_10y": _metric(raw["real_yield_10y"], *DAILY[1:]),
        "payroll_change": _metric(payroll_changes, *MONTHLY[1:]),
        "payroll_3m_avg": _average(payroll_changes, 3),
        "initial_claims_4w_avg": _average(raw["initial_claims"], 4),
        "sahm_gap": _sahm_gap(raw["unemployment"]),
    }

    loaded = [key for key, value in bundle.items() if key != "available" and value is not None]
    logger.info("[FRED] 지표 %s/%s 로드", len(loaded), len(bundle) - 1)
    return bundle
