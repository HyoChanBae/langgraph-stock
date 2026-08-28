import logging

from app.config import settings  # noqa: F401  dotenv 로드
from app.chains.report_chain import report_chain
from app.repositories.report_repository import save_market_report


logger = logging.getLogger(__name__)


def execute_report_logic(
    symbols: list[str],
    market_context: str = "",
):
    logger.info(
        "[ReportService] received symbols: %s",
        symbols,
    )
    
    report_text = report_chain.invoke({
        "symbols": ", ".join(symbols),
        "market_context": market_context or "데이터 없음 (테스트)",
    })

    logger.info("[ReportService] report generated")

    report_id = save_market_report(
        symbols=symbols,
        report=report_text,
        market_context=market_context,
    )

    logger.info("[ReportService] saved to snowflake id=%s", report_id)

    return {
        "id": report_id,
        "symbols": symbols,
        "report": report_text,
    }


if __name__ == "__main__":
    print("\n===== DB연결 =====\n")
    print(bool(settings.DATABASE_URL))
    print("\n===== DB Split1 =====\n")
    print(settings.DATABASE_URL.split("@")[-1] if settings.DATABASE_URL else None)
    print("\n===== DB Split2 =====\n")
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = execute_report_logic(
        symbols=["005930", "000660"],
        market_context="삼성전자/SK하이닉스 반도체 업황 테스트 입력",
    )

    print("\n===== MARKET REPORT =====\n")
    print(result["report"])
    print("\n===== SNOWFLAKE INSERT =====\n")
    print(result["id"])
