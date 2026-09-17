import logging

from app.celery_app import celery_app
from app.services.macro_service import execute_macro_logic
from app.services.report_service2 import execute_report_logic as execute_report2_logic
from app.services.trading_buy1_service import execute_trading_buy1_logic
from app.services.trading_buy1_service_senario import execute_trading_buy1_senario_logic
from app.services.trading_buy2_service_senario import execute_trading_buy2_senario_logic
from app.services.trading_service import execute_trading_logic


logger = logging.getLogger(__name__)


# @celery_app.task(name="trading.execute")
# def execute_trading(symbols: list[str]):
#     logger.info(
#         "[Celery Task] received symbols: %s",
#         symbols
#     )

#     result = execute_trading_logic(symbols)

#     return result


# @celery_app.task(name="trading.buy1.execute")
# def execute_trading_buy1():
#     logger.info("[Celery Task] trading.buy1.execute")
#     return execute_trading_buy1_logic()


@celery_app.task(name="trading.buy1.senario.execute")
def execute_trading_buy1_senario():
    logger.info("[Celery Task] trading.buy1.senario.execute")
    return execute_trading_buy1_senario_logic()


@celery_app.task(name="trading.buy2.senario.execute")
def execute_trading_buy2_senario():
    logger.info("[Celery Task] trading.buy2.senario.execute")
    return execute_trading_buy2_senario_logic()


@celery_app.task(name="report.execute2")
def execute_report2(market_context: str = "", as_of: str | None = None):
    logger.info("[Celery Task] report.execute2 as_of=%s", as_of)
    return execute_report2_logic(market_context=market_context, as_of=as_of)


@celery_app.task(name="macro.execute")
def execute_macro(as_of: str | None = None):
    logger.info("[Celery Task] macro.execute as_of=%s", as_of)
    return execute_macro_logic(as_of=as_of)
