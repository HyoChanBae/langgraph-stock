import logging
from typing import Literal, TypedDict

from langgraph.graph import StateGraph, START, END

from app.stock_order.buy import STOCK_CODE, place_buy_order


logger = logging.getLogger(__name__)

TARGET_STOCK_CODE = STOCK_CODE


class TradingState(TypedDict):
    symbols: list[str]
    approved_symbols: list[str]
    orders: list[dict]


def validate_symbol(state: TradingState):
    approved_symbols = []

    for symbol in state["symbols"]:
        if symbol == TARGET_STOCK_CODE:
            logger.info("[validate] %s 통과", symbol)
            approved_symbols.append(symbol)
        else:
            logger.info(
                "[validate] %s 거부 (대상 코드 %s 아님)",
                symbol,
                TARGET_STOCK_CODE,
            )

    return {
        "approved_symbols": approved_symbols,
    }


def should_buy(state: TradingState) -> Literal["place_order", "end"]:
    if state["approved_symbols"]:
        return "place_order"
    return "end"


def place_order(state: TradingState):
    orders = []

    for symbol in state["approved_symbols"]:
        logger.info("[buy] %s 시장가 매수", symbol)
        orders.append(place_buy_order(symbol))

    return {
        "orders": orders,
    }


builder = StateGraph(TradingState)

builder.add_node("validate", validate_symbol)
builder.add_node("place_order", place_order)

builder.add_edge(START, "validate")
builder.add_conditional_edges(
    "validate",
    should_buy,
    {
        "place_order": "place_order",
        "end": END,
    },
)
builder.add_edge("place_order", END)

graph = builder.compile()
