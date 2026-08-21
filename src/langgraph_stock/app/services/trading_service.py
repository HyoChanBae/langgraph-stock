import logging

from app.graphs.trading_graph import graph


logger = logging.getLogger(__name__)


def execute_trading_logic(
    symbols: list[str]
):
    logger.info(
        "[TradingService] received symbols: %s",
        symbols
    )

    result = graph.invoke({
        "symbols": symbols,
        "approved_symbols": [],
        "orders": [],
    })

    logger.info(
        "[TradingService] graph completed"
    )

    return result
