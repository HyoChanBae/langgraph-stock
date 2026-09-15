import logging

from langgraph.graph import END, START, StateGraph

from app.chains.stock_pick_chain import stock_pick_chain
from app.graphs.trading_buy1 import (
    TRADING_BUY1_BOT_ID,
    TradingBuy1State,
    _normalize_symbol,
    load_report,
    should_buy,
)
from app.repositories.report_repository import (
    save_bot_trade_senario,
    save_stock_order_senario,
    save_stock_pick_senario,
    update_bot_trade_price_senario,
)
from app.stocks.name_resolve import resolve_stock_by_name
from app.stock_order.buy import ORDER_QUANTITY, _fetch_buy_price, ka


logger = logging.getLogger(__name__)


def pick_stock(state: TradingBuy1State):
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
    pick = stock_pick_chain.invoke({"report_text": report_text})
    stock_name = (pick.stock_name or "").strip()
    reason = (pick.reason or "").strip()

    master = resolve_stock_by_name(stock_name)
    if not master:
        logger.warning("[node2] STOCK_MASTER에서 종목코드를 찾지 못함 name=%s", stock_name)
        return {
            "pick_id": None,
            "trade_id": None,
            "symbol": "",
            "stock_name": stock_name,
            "reason": reason,
        }

    symbol = _normalize_symbol(master["short_code"])
    stock_name = master["stock_name"]
    logger.info(
        "[node2] LLM name=%s → code=%s official=%s match=%s",
        pick.stock_name,
        symbol,
        stock_name,
        master.get("match_type"),
    )

    pick_id = save_stock_pick_senario(
        report_id=state.get("report_id"),
        symbol=symbol,
        stock_name=stock_name,
        reason=reason,
    )
    trade_id = save_bot_trade_senario(
        bot_id=TRADING_BUY1_BOT_ID,
        symbol=symbol,
        symbol_name=stock_name,
        select_reason=reason,
    )

    logger.info(
        "[node2] 시나리오 추천 종목 %s (%s) pick_id=%s trade_id=%s",
        symbol,
        stock_name,
        pick_id,
        trade_id,
    )
    return {
        "pick_id": pick_id,
        "trade_id": trade_id,
        "symbol": symbol,
        "stock_name": stock_name,
        "reason": reason,
    }


def place_order(state: TradingBuy1State):
    symbol = state["symbol"]
    logger.info("[buy] 시나리오 기록 %s (실주문 없음)", symbol)

    ka.auth(svr="prod", product="01")
    buy_price = _fetch_buy_price(symbol)
    order = {
        "symbol": symbol,
        "quantity": ORDER_QUANTITY,
        "buy_price": buy_price,
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
    if trade_id:
        update_bot_trade_price_senario(trade_id, buy_price)

    return {
        "orders": [order],
    }


builder = StateGraph(TradingBuy1State)

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
