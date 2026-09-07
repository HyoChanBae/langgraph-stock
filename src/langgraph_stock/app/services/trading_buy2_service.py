import logging

from app.config import settings  # noqa: F401  dotenv 로드
from app.graphs.trading_buy2 import graph


logger = logging.getLogger(__name__)


def execute_trading_buy2_logic():
    logger.info("[TradingBuy2Service] start")

    result = graph.invoke({
        "report_id": None,
        "report_text": "",
        "pick_id": None,
        "trade_id": None,
        "symbol": "",
        "stock_name": "",
        "reason": "",
        "orders": [],
    })

    logger.info("[TradingBuy2Service] graph completed")
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    result = execute_trading_buy2_logic()
    print(result)
