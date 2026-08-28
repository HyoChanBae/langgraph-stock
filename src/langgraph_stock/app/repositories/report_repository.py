import logging

import snowflake.connector

from app.config import settings


logger = logging.getLogger(__name__)


def _connect():
    return snowflake.connector.connect(
        account=settings.SNOWFLAKE_ACCOUNT,
        user=settings.SNOWFLAKE_USER,
        password=settings.SNOWFLAKE_PASSWORD,
        database=settings.SNOWFLAKE_DATABASE,
        schema=settings.SNOWFLAKE_SCHEMA,
        warehouse=settings.SNOWFLAKE_WAREHOUSE,
        role=settings.SNOWFLAKE_ROLE,
        authenticator=settings.SNOWFLAKE_AUTHENTICATOR,
    )


def save_market_report(
    symbols: list[str],
    report: str,
    market_context: str = "",
) -> int | None:
    conn = _connect()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO MARKET_REPORTS (SYMBOLS, MARKET_CONTEXT, REPORT)
            VALUES (%s, %s, %s)
            """,
            (
                ",".join(symbols),
                market_context or None,
                str(report),
            ),
        )
        cur.execute("SELECT MAX(ID) FROM MARKET_REPORTS")
        report_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    logger.info("[ReportRepository] saved MARKET_REPORTS id=%s", report_id)
    return report_id


def fetch_latest_market_report() -> dict | None:
    conn = _connect()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ID, SYMBOLS, MARKET_CONTEXT, REPORT, CREATED_AT
            FROM MARKET_REPORTS
            WHERE SYMBOLS = 'MARKET'
            ORDER BY ID DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                SELECT ID, SYMBOLS, MARKET_CONTEXT, REPORT, CREATED_AT
                FROM MARKET_REPORTS
                ORDER BY ID DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        logger.warning("[ReportRepository] MARKET_REPORTS 가 비어 있습니다")
        return None

    report = {
        "id": row[0],
        "symbols": row[1],
        "market_context": row[2],
        "report": row[3],
        "created_at": str(row[4]) if row[4] is not None else None,
    }
    logger.info("[ReportRepository] loaded MARKET_REPORTS id=%s", report["id"])
    return report


def save_stock_pick(
    report_id: int | None,
    symbol: str,
    stock_name: str,
    reason: str,
) -> int | None:
    conn = _connect()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO STOCK_PICKS (REPORT_ID, SYMBOL, STOCK_NAME, REASON)
            VALUES (%s, %s, %s, %s)
            """,
            (
                report_id,
                symbol,
                stock_name or None,
                str(reason),
            ),
        )
        cur.execute("SELECT MAX(ID) FROM STOCK_PICKS")
        pick_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    logger.info("[ReportRepository] saved STOCK_PICKS id=%s symbol=%s", pick_id, symbol)
    return pick_id
