import logging
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
_STOCK_ORDER_DIR = Path(__file__).resolve().parent
for _path in (_APP_DIR, _STOCK_ORDER_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import yfinance as yf

import kis_auth as ka
from overseas_stock_functions import order


logger = logging.getLogger(__name__)

ORDER_QUANTITY = 1

EXCHANGE_MAP = {
    "NMS": "NASD",
    "NASDAQ": "NASD",
    "NGM": "NASD",
    "NCM": "NASD",
    "NYQ": "NYSE",
    "NYSE": "NYSE",
    "PCX": "NYSE",
    "ASE": "AMEX",
    "AMEX": "AMEX",
}


def _fast_info_value(fast, *keys):
    for key in keys:
        try:
            if hasattr(fast, "get"):
                value = fast.get(key)
            else:
                value = getattr(fast, key, None)
        except Exception:
            value = None
        if value not in (None, ""):
            return value
    return None


def round_limit_price(price: float) -> float:
    return round(float(price), 2)


def fetch_yahoo_price(symbol: str) -> float | None:
    ticker = yf.Ticker(symbol)
    try:
        price = _fast_info_value(
            ticker.fast_info,
            "last_price",
            "lastPrice",
            "regular_market_price",
            "regularMarketPrice",
        )
        if price not in (None, ""):
            return round_limit_price(price)
    except Exception:
        logger.warning("yfinance fast_info 실패 symbol=%s", symbol, exc_info=True)

    try:
        info = ticker.info or {}
        for key in ("regularMarketPrice", "currentPrice", "previousClose"):
            if info.get(key) not in (None, ""):
                return round_limit_price(info[key])
    except Exception:
        logger.warning("yfinance info 가격 실패 symbol=%s", symbol, exc_info=True)

    try:
        hist = ticker.history(period="1d")
        if hist is not None and not hist.empty:
            return round_limit_price(hist["Close"].iloc[-1])
    except Exception:
        logger.warning("yfinance history 실패 symbol=%s", symbol, exc_info=True)

    return None


def fetch_yahoo_stock_name(symbol: str) -> str | None:
    try:
        info = yf.Ticker(symbol).info or {}
        name = info.get("shortName") or info.get("longName")
        if name:
            return str(name).strip()
    except Exception:
        logger.warning("yfinance 종목명 실패 symbol=%s", symbol, exc_info=True)
    return None


def fetch_exchange_code(symbol: str) -> str:
    try:
        exchange = (yf.Ticker(symbol).info or {}).get("exchange") or "NMS"
        return EXCHANGE_MAP.get(str(exchange).upper(), "NASD")
    except Exception:
        logger.warning("yfinance 거래소 실패 symbol=%s", symbol, exc_info=True)
        return "NASD"


def place_overseas_buy_order(symbol: str) -> dict:
    ka.auth(svr="prod", product="01")
    trenv = ka.getTREnv()
    limit_price = fetch_yahoo_price(symbol)
    if limit_price is None:
        return {
            "symbol": symbol,
            "quantity": ORDER_QUANTITY,
            "buy_price": None,
            "success": False,
            "message": "yfinance 현재가를 가져오지 못해 지정가 주문을 건너뜁니다.",
        }

    ovrs_excg_cd = fetch_exchange_code(symbol)
    ord_unpr = f"{limit_price:.2f}"

    result = order(
        env_dv="real",
        ord_dv="buy",
        cano=trenv.my_acct,
        acnt_prdt_cd=trenv.my_prod,
        ovrs_excg_cd=ovrs_excg_cd,
        pdno=symbol,
        ord_qty=str(ORDER_QUANTITY),
        ovrs_ord_unpr=ord_unpr,
        ctac_tlno="",
        mgco_aptm_odno="",
        ord_svr_dvsn_cd="0",
        ord_dvsn="00",
    )

    if result is None or result.empty:
        return {
            "symbol": symbol,
            "quantity": ORDER_QUANTITY,
            "buy_price": limit_price,
            "exchange": ovrs_excg_cd,
            "success": False,
            "message": "주문 결과가 없습니다. API 오류 메시지를 확인하세요.",
        }

    return {
        "symbol": symbol,
        "quantity": ORDER_QUANTITY,
        "buy_price": limit_price,
        "exchange": ovrs_excg_cd,
        "success": True,
        "result": result.to_dict(orient="records"),
    }
