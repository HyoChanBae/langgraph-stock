import logging

from app.config import settings  # noqa: F401  dotenv 로드
from app.graphs.trading_buy2 import load_report, should_buy
from app.graphs.trading_buy2_senario import pick_stock, place_order
from app.repositories.report_repository import update_bot_trade_price_senario
from app.stock_order.buy_overseas import (
    ORDER_QUANTITY,
    fetch_exchange_code,
    fetch_yahoo_price,
)


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


def ask_confirm(
    symbol: str,
    stock_name: str,
    reason: str,
    price: float | None,
    exchange: str,
) -> bool:
    price_text = f"${price:.2f}" if price is not None else "조회 실패"
    print("\n===== 해외주식 시나리오 기록 확인 =====")
    print(f"티커     : {symbol}")
    print(f"종목명   : {stock_name or '-'}")
    print(f"거래소   : {exchange}")
    print(f"지정가   : {price_text} (yfinance 현재가)")
    print(f"수량     : {ORDER_QUANTITY}주 (기록만, 실주문 없음)")
    print(f"선정이유 : {reason or '-'}")
    answer = input("시나리오에 기록할까요? (예/아니오): ").strip().lower()
    return answer in ("y", "yes", "예", "ㅛ")


def execute_trading_buy2_manual_senario_logic():
    logger.info("[TradingBuy2ManualSenario] start")
    state = _empty_state()
    state.update(load_report(state))
    state.update(pick_stock(state))

    if should_buy(state) != "place_order":
        logger.info("[TradingBuy2ManualSenario] 유효한 티커가 없어 기록을 건너뜁니다")
        return state

    symbol = state["symbol"]
    stock_name = state.get("stock_name") or ""
    reason = state.get("reason") or ""
    price = fetch_yahoo_price(symbol)
    exchange = fetch_exchange_code(symbol)
    trade_id = state.get("trade_id")
    if trade_id:
        update_bot_trade_price_senario(trade_id, price)

    if not ask_confirm(symbol, stock_name, reason, price, exchange):
        logger.info("[TradingBuy2ManualSenario] 사용자가 시나리오 기록을 취소했습니다")
        print("시나리오 기록을 취소했습니다.")
        return state

    state.update(place_order(state))
    logger.info("[TradingBuy2ManualSenario] completed")
    return state


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    result = execute_trading_buy2_manual_senario_logic()
    print(result)
