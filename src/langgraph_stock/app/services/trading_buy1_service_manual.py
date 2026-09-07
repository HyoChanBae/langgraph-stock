import logging

from app.config import settings  # noqa: F401  dotenv 로드
from app.graphs.trading_buy1 import load_report, pick_stock, place_order, should_buy
from app.stock_order.buy import ORDER_QUANTITY, _fetch_buy_price, ka


logger = logging.getLogger(__name__)


def _empty_state():
    return {
        "report_id": None,
        "report_text": "",
        "pick_id": None,
        "trade_id": None,
        "symbol": "",
        "stock_name": "",
        "reason": "",
        "orders": [],
    }


def ask_confirm(symbol: str, stock_name: str, reason: str, price: float | None) -> bool:
    price_text = f"{price:,.0f}원" if price is not None else "조회 실패"
    print("\n===== 매수 확인 =====")
    print(f"종목코드 : {symbol}")
    print(f"종목명   : {stock_name or '-'}")
    print(f"현재가   : {price_text}")
    print(f"수량     : {ORDER_QUANTITY}주 (시장가)")
    print(f"선정이유 : {reason or '-'}")
    answer = input("매수할까요? (예/아니오): ").strip().lower()
    return answer in ("y", "yes", "예", "ㅛ")


def execute_trading_buy1_manual_logic():
    logger.info("[TradingBuy1Manual] start")
    state = _empty_state()
    state.update(load_report(state))
    state.update(pick_stock(state))

    if should_buy(state) != "place_order":
        logger.info("[TradingBuy1Manual] 유효한 종목코드가 없어 매수를 건너뜁니다")
        return state

    symbol = state["symbol"]
    stock_name = state.get("stock_name") or ""
    reason = state.get("reason") or ""

    ka.auth(svr="prod", product="01")
    price = _fetch_buy_price(symbol)

    if not ask_confirm(symbol, stock_name, reason, price):
        logger.info("[TradingBuy1Manual] 사용자가 매수를 취소했습니다")
        print("매수를 취소했습니다.")
        return state

    state.update(place_order(state))
    logger.info("[TradingBuy1Manual] completed")
    return state


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    result = execute_trading_buy1_manual_logic()
    print(result)
