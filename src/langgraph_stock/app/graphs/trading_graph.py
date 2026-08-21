import logging
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


logger = logging.getLogger(__name__)


class TradingState(TypedDict):
    symbols: list[str]


def test_node(state: TradingState):
    logger.info(
        "[LangGraph] received symbols: %s",
        state["symbols"]
    )

    return {
        "symbols": state["symbols"]
    }


builder = StateGraph(TradingState)

builder.add_node(
    "test",
    test_node
)

builder.add_edge(
    START,
    "test"
)

builder.add_edge(
    "test",
    END
)

graph = builder.compile()

