import logging

from langgraph.graph import END, START, StateGraph

from app.chains.stock_pick_chain2 import overseas_stock_pick_chain
from app.graphs.trading_buy2 import (
    TRADING_BUY2_BOT_ID,
    TradingBuy2State,
    _normalize_ticker,
    load_report,
    should_buy,
)
from app.repositories.report_repository import (
    save_bot_trade_senario,
    save_stock_order_senario,
    save_stock_pick_senario,
    update_bot_trade_price_senario,
)
from app.stock_order.buy_overseas import (
    ORDER_QUANTITY,
    fetch_exchange_code,
    fetch_yahoo_price,
    fetch_yahoo_stock_name,
)


logger = logging.getLogger(__name__)


def pick_stock(state: TradingBuy2State):
    report_text = state.get("report_text") or ""
    if not report_text:
        logger.warning("[node2] 리포트 본문이 없어 종목을 뽑지 않습니다")
        return {
            "pick_id": None,
            "trade_id": None,
            "symbol": "",
            "stock_name": "",
            "reason": "",
        }

    pick = overseas_stock_pick_chain.invoke({"report_text": report_text})
    symbol = _normalize_ticker(pick.symbol)
    stock_name = (pick.stock_name or "").strip()
    reason = (pick.reason or "").strip()

    yahoo_name = fetch_yahoo_stock_name(symbol)
    if yahoo_name:
        if stock_name and stock_name != yahoo_name:
            logger.warning(
                "[node2] 종목명 불일치 ticker=%s LLM=%s yfinance=%s",
                symbol,
                stock_name,
                yahoo_name,
            )
        stock_name = yahoo_name
    else:
        logger.warning("[node2] yfinance 종목명 없음 ticker=%s", symbol)

    buy_price = fetch_yahoo_price(symbol)
    if buy_price is None:
        logger.warning("[node2] 현재가 조회 실패 ticker=%s", symbol)
    else:
        logger.info("[node2] 현재가 %s ticker=%s", buy_price, symbol)

    pick_id = save_stock_pick_senario(
        report_id=state.get("report_id"),
        symbol=symbol,
        stock_name=stock_name,
        reason=reason,
    )
    trade_id = save_bot_trade_senario(
        bot_id=TRADING_BUY2_BOT_ID,
        symbol=symbol,
        symbol_name=stock_name,
        select_reason=reason,
        buy_price=buy_price,
    )

    logger.info(
        "[node2] 시나리오 추천 종목 %s (%s) pick_id=%s trade_id=%s price=%s",
        symbol,
        stock_name,
        pick_id,
        trade_id,
        buy_price,
    )
    return {
        "pick_id": pick_id,
        "trade_id": trade_id,
        "symbol": symbol,
        "stock_name": stock_name,
        "reason": reason,
    }


def place_order(state: TradingBuy2State):
    symbol = state["symbol"]
    logger.info("[buy] 시나리오 기록 %s (실주문 없음)", symbol)

    buy_price = fetch_yahoo_price(symbol)
    exchange = fetch_exchange_code(symbol)
    order = {
        "symbol": symbol,
        "quantity": ORDER_QUANTITY,
        "buy_price": buy_price,
        "exchange": exchange,
        "success": True,
        "simulated": True,
        "message": "시나리오 기록 (실주문 없음)",
    }

    save_stock_order_senario(
        pick_id=state.get("pick_id"),
        symbol=symbol,
        buy_price=buy_price,
        buy_qty=ORDER_QUANTITY,
        order_success=True,
        order_raw=order,
    )
    trade_id = state.get("trade_id")
    if trade_id and buy_price is not None:
        update_bot_trade_price_senario(trade_id, buy_price)

    return {
        "orders": [order],
    }


builder = StateGraph(TradingBuy2State)

builder.add_node("load_report", load_report)
builder.add_node("pick_stock", pick_stock)
builder.add_node("place_order", place_order)

builder.add_edge(START, "load_report")
builder.add_edge("load_report", "pick_stock")
builder.add_conditional_edges(
    "pick_stock",
    should_buy,
    {
        "place_order": "place_order",
        "end": END,
    },
)
builder.add_edge("place_order", END)

graph = builder.compile()
