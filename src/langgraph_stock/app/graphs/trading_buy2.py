import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.chains.stock_pick_chain2 import overseas_stock_pick_chain
from app.repositories.report_repository import (
    fetch_latest_market_report,
    save_bot_trade,
    save_stock_order,
    save_stock_pick,
    update_bot_trade_price,
)
from app.stock_order.buy_overseas import (
    fetch_yahoo_stock_name,
    place_overseas_buy_order,
)


logger = logging.getLogger(__name__)

TRADING_BUY2_BOT_ID = 501


class TradingBuy2State(TypedDict):
    report_id: int | None
    report_text: str
    pick_id: int | None
    trade_id: int | None
    symbol: str
    stock_name: str
    reason: str
    orders: list[dict]


def _normalize_ticker(symbol: str) -> str:
    code = str(symbol or "").strip().upper()
    if code.startswith("$"):
        code = code[1:]
    if ":" in code:
        code = code.split(":")[-1]
    return code.strip()


def load_report(state: TradingBuy2State):
    report = fetch_latest_market_report()

    if not report:
        logger.warning("[node1] 읽을 시장 리포트가 없습니다")
        return {
            "report_id": None,
            "report_text": "",
        }

    logger.info("[node1] MARKET_REPORTS id=%s 로드", report["id"])
    return {
        "report_id": report["id"],
        "report_text": report["report"] or "",
    }


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

    pick_id = save_stock_pick(
        report_id=state.get("report_id"),
        symbol=symbol,
        stock_name=stock_name,
        reason=reason,
    )
    trade_id = save_bot_trade(
        bot_id=TRADING_BUY2_BOT_ID,
        symbol=symbol,
        symbol_name=stock_name,
        select_reason=reason,
    )

    logger.info(
        "[node2] 추천 종목 %s (%s) pick_id=%s trade_id=%s",
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


def should_buy(state: TradingBuy2State) -> Literal["place_order", "end"]:
    symbol = (state.get("symbol") or "").strip().upper()
    if 1 <= len(symbol) <= 10 and not symbol.isdigit():
        return "place_order"
    logger.info("[route] 해외 티커가 유효하지 않아 매수 생략: %s", symbol)
    return "end"


def place_order(state: TradingBuy2State):
    symbol = state["symbol"]
    logger.info("[buy] 추천 종목 %s 지정가 매수", symbol)
    order_result = place_overseas_buy_order(symbol)

    save_stock_order(
        pick_id=state.get("pick_id"),
        symbol=symbol,
        buy_price=order_result.get("buy_price"),
        buy_qty=order_result.get("quantity"),
        order_success=order_result.get("success"),
        order_raw=order_result,
    )
    trade_id = state.get("trade_id")
    if trade_id:
        update_bot_trade_price(trade_id, order_result.get("buy_price"))

    return {
        "orders": [order_result],
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
