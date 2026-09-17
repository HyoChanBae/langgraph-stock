"""yfinance 기반 시장 가격 수집. 금리/달러/유가와 성장·리스크 프록시를 담당한다."""

import logging

import yfinance as yf


logger = logging.getLogger(__name__)

TICKERS = {
    "ust_10y": "^TNX",
    "ust_5y": "^FVX",
    "ust_3m": "^IRX",
    "dollar_index": "DX-Y.NYB",
    "wti": "CL=F",
    "brent": "BZ=F",
    "copper": "HG=F",
    "gold": "GC=F",
    "vix": "^VIX",
    "hy_credit": "HYG",
    "treasury_etf": "IEF",
}

# 국채 금리 티커는 소수 자리 규약이 바뀐 적이 있어 퍼센트 단위로 통일한다.
YIELD_KEYS = {"ust_10y", "ust_5y", "ust_3m"}

LOOKBACK_1M = 21
LOOKBACK_3M = 63


def _normalize_yield(value: float) -> float:
    return value / 10.0 if value > 20.0 else value


def fetch_close_series(ticker: str, period: str = "1y"):
    try:
        history = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    except Exception:
        logger.warning("[Market] yfinance 조회 실패 ticker=%s", ticker, exc_info=True)
        return None

    if history is None or history.empty or "Close" not in history:
        logger.warning("[Market] 종가 데이터 없음 ticker=%s", ticker)
        return None

    closes = history["Close"].dropna()
    return closes if not closes.empty else None


def _quote(closes, is_yield: bool = False) -> dict | None:
    if closes is None or len(closes) == 0:
        return None

    def at(offset: int) -> float | None:
        if len(closes) <= offset:
            return None
        value = float(closes.iloc[-1 - offset])
        return _normalize_yield(value) if is_yield else value

    latest = at(0)
    if latest is None:
        return None

    prev_1m = at(LOOKBACK_1M)
    prev_3m = at(LOOKBACK_3M)
    return {
        "value": latest,
        "diff_1m": None if prev_1m is None else latest - prev_1m,
        "diff_3m": None if prev_3m is None else latest - prev_3m,
        "pct_1m": None if not prev_1m else latest / prev_1m - 1.0,
        "pct_3m": None if not prev_3m else latest / prev_3m - 1.0,
        "as_of": str(closes.index[-1].date()),
    }


def _spread(long_end: dict | None, short_end: dict | None) -> dict | None:
    """두 금리의 차이와 그 변화를 퍼센트포인트로 계산한다."""
    if not long_end or not short_end:
        return None

    def diff(key: str) -> float | None:
        a, b = long_end.get(key), short_end.get(key)
        return None if a is None or b is None else a - b

    return {
        "value": long_end["value"] - short_end["value"],
        "diff_1m": diff("diff_1m"),
        "diff_3m": diff("diff_3m"),
        "as_of": long_end.get("as_of"),
    }


def _ratio(numerator: dict | None, denominator: dict | None) -> dict | None:
    """두 자산의 비율과 그 변화율. 성장·리스크 선호 프록시로 쓴다."""
    if not numerator or not denominator or not denominator.get("value"):
        return None

    def relative(key: str) -> float | None:
        a, b = numerator.get(key), denominator.get(key)
        if a is None or b is None or b == -1.0:
            return None
        return (1.0 + a) / (1.0 + b) - 1.0

    return {
        "value": numerator["value"] / denominator["value"],
        "pct_1m": relative("pct_1m"),
        "pct_3m": relative("pct_3m"),
        "as_of": numerator.get("as_of"),
    }


def fetch_market_bundle() -> dict:
    """시장 가격 지표 묶음. 개별 티커 실패는 None으로 남기고 나머지를 살린다."""
    quotes = {}
    for key, ticker in TICKERS.items():
        quotes[key] = _quote(fetch_close_series(ticker), is_yield=key in YIELD_KEYS)

    bundle = dict(quotes)
    bundle["curve_10y_3m"] = _spread(quotes["ust_10y"], quotes["ust_3m"])
    bundle["copper_gold"] = _ratio(quotes["copper"], quotes["gold"])
    bundle["credit_proxy"] = _ratio(quotes["hy_credit"], quotes["treasury_etf"])

    loaded = [key for key, value in bundle.items() if value is not None]
    logger.info("[Market] 지표 %s/%s 로드", len(loaded), len(bundle))
    return bundle
