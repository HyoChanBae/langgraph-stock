import logging
from datetime import datetime

from app.config import settings  # noqa: F401  dotenv 로드
from app.chains.report_chain2 import market_flow_chain
from app.repositories.report_repository import save_market_report


logger = logging.getLogger(__name__)

MARKET_FLOW_SYMBOL = "MARKET"


def execute_report_logic(
    market_context: str = "",
    as_of: str | None = None,
):
    as_of = as_of or datetime.now().strftime("%Y-%m-%d %H:%M")

    logger.info("[ReportService2] market flow report as_of=%s", as_of)

    report_text = market_flow_chain.invoke({
        "as_of": as_of,
        "market_context": market_context or "데이터 없음 (테스트)",
    })

    logger.info("[ReportService2] report generated")

    report_id = save_market_report(
        symbols=[MARKET_FLOW_SYMBOL],
        report=report_text,
        market_context=market_context,
    )

    logger.info("[ReportService2] saved to snowflake id=%s", report_id)

    return {
        "id": report_id,
        "symbols": [MARKET_FLOW_SYMBOL],
        "report": report_text,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = execute_report_logic(
        market_context="전체 시장 흐름 리포트 테스트 입력",
    )

    print("\n===== MARKET FLOW REPORT =====\n")
    print(result["report"])
    print("\n===== SNOWFLAKE INSERT =====\n")
    print(result["id"])
