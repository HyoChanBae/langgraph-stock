import logging

from app.celery_app import celery_app
from app.services.trading_service import execute_trading_logic


logger = logging.getLogger(__name__)


@celery_app.task(name="trading.execute")
def execute_trading(symbols: list[str]):
    logger.info(
        "[Celery Task] received symbols: %s",
        symbols
    )

    result = execute_trading_logic(symbols)

    return result
