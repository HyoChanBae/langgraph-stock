import logging

from app.config import settings  # noqa: F401  dotenv 로드
from app.graphs.trading_buy1_senario import graph


logger = logging.getLogger(__name__)


def execute_trading_buy1_senario_logic():
    logger.info("[TradingBuy1SenarioService] start")

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

    logger.info("[TradingBuy1SenarioService] graph completed")
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    result = execute_trading_buy1_senario_logic()
    print(result)
