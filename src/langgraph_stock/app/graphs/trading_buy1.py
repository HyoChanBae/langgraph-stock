import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.chains.stock_pick_chain import stock_pick_chain
from app.repositories.report_repository import (
    fetch_latest_market_report,
    save_stock_pick,
)
from app.stock_order.buy import place_buy_order


logger = logging.getLogger(__name__)


class TradingBuy1State(TypedDict):
    report_id: int | None
    report_text: str
    pick_id: int | None
    symbol: str
    stock_name: str
    reason: str
    orders: list[dict]


def load_report(state: TradingBuy1State):
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


def pick_stock(state: TradingBuy1State):
    report_text = state.get("report_text") or ""
    if not report_text:
        logger.warning("[node2] 리포트 본문이 없어 종목을 뽑지 않습니다")
        return {
            "pick_id": None,
            "symbol": "",
            "stock_name": "",
            "reason": "",
        }

    pick = stock_pick_chain.invoke({"report_text": report_text})
    symbol = (pick.symbol or "").strip()
    stock_name = (pick.stock_name or "").strip()
    reason = (pick.reason or "").strip()

    pick_id = save_stock_pick(
        report_id=state.get("report_id"),
        symbol=symbol,
        stock_name=stock_name,
        reason=reason,
    )

    logger.info("[node2] 추천 종목 %s (%s) pick_id=%s", symbol, stock_name, pick_id)
    return {
        "pick_id": pick_id,
        "symbol": symbol,
        "stock_name": stock_name,
        "reason": reason,
    }


def should_buy(state: TradingBuy1State) -> Literal["place_order", "end"]:
    symbol = (state.get("symbol") or "").strip()
    if len(symbol) == 6 and symbol.isdigit():
        return "place_order"
    logger.info("[route] 종목코드가 유효하지 않아 매수 생략: %s", symbol)
    return "end"


def place_order(state: TradingBuy1State):
    symbol = state["symbol"]
    logger.info("[buy] 추천 종목 %s 시장가 매수", symbol)
    return {
        "orders": [place_buy_order(symbol)],
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
