import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import snowflake.connector

from app.config import settings


logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


def kst_now() -> datetime:
    return datetime.now(KST)


def kst_now_naive() -> datetime:
    return kst_now().replace(tzinfo=None)


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
    created_at: datetime | None = None,
) -> int | None:
    conn = _connect()
    created_at = created_at or kst_now_naive()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO MARKET_REPORTS (SYMBOLS, MARKET_CONTEXT, REPORT, CREATED_AT)
            VALUES (%s, %s, %s, %s)
            """,
            (
                ",".join(symbols),
                market_context or None,
                str(report),
                created_at,
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


def fetch_latest_sector_report() -> dict | None:
    conn = _connect()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ID, SYMBOLS, MARKET_CONTEXT, REPORT, CREATED_AT
            FROM MARKET_REPORTS
            WHERE SYMBOLS = 'SECTOR'
            ORDER BY ID DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        logger.warning("[ReportRepository] SECTOR 리포트가 없습니다")
        return None

    report = {
        "id": row[0],
        "symbols": row[1],
        "market_context": row[2],
        "report": row[3],
        "created_at": str(row[4]) if row[4] is not None else None,
    }
    logger.info("[ReportRepository] loaded SECTOR report id=%s", report["id"])
    return report


def fetch_latest_macro_report() -> dict | None:
    conn = _connect()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ID, SYMBOLS, MARKET_CONTEXT, REPORT, CREATED_AT
            FROM MARKET_REPORTS
            WHERE SYMBOLS = 'MACRO'
            ORDER BY ID DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        logger.warning("[ReportRepository] MACRO 리포트가 없습니다")
        return None

    report = {
        "id": row[0],
        "symbols": row[1],
        "market_context": row[2],
        "report": row[3],
        "created_at": str(row[4]) if row[4] is not None else None,
    }
    logger.info("[ReportRepository] loaded MACRO report id=%s", report["id"])
    return report


def _short_code_key(symbol: str) -> str:
    code = str(symbol or "").strip().upper()
    if code.startswith("A") and code[1:].isdigit():
        code = code[1:]
    if code.isdigit():
        return code.lstrip("0") or "0"
    return code


def fetch_stock_master_listings() -> list[dict]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT SHORT_CODE, STOCK_NAME
            FROM STOCK_MASTER
            WHERE STOCK_NAME IS NOT NULL
            """
        )
        rows = cur.fetchall() or []
    finally:
        conn.close()

    listings = []
    for row in rows:
        code = str(row[0] or "").strip()
        name = str(row[1] or "").strip()
        if code and name:
            listings.append({"short_code": code, "stock_name": name})

    logger.info("[ReportRepository] STOCK_MASTER listings=%s", len(listings))
    return listings


def fetch_stock_by_name(stock_name: str) -> dict | None:
    name = str(stock_name or "").strip()
    if not name:
        return None

    key = name.replace(" ", "")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT SHORT_CODE, STOCK_NAME
            FROM STOCK_MASTER
            WHERE REPLACE(TRIM(STOCK_NAME), ' ', '') = %s
            """,
            (key,),
        )
        rows = cur.fetchall() or []
    finally:
        conn.close()

    matches = []
    for row in rows:
        code = str(row[0] or "").strip()
        official = str(row[1] or "").strip()
        if code and official:
            matches.append({"short_code": code, "stock_name": official})

    if not matches:
        logger.warning("[ReportRepository] STOCK_MASTER 종목코드 없음 stock_name=%s", name)
        return None

    if len(matches) > 1:
        logger.warning(
            "[ReportRepository] STOCK_MASTER 동명 종목 %s건 stock_name=%s matches=%s",
            len(matches),
            name,
            [m["short_code"] for m in matches],
        )
        return None

    match = matches[0]
    logger.info(
        "[ReportRepository] STOCK_MASTER stock_name=%s short_code=%s official=%s",
        name,
        match["short_code"],
        match["stock_name"],
    )
    return match


def fetch_stock_name_by_short_code(symbol: str) -> str | None:
    code = str(symbol or "").strip()
    if not code:
        return None

    key = _short_code_key(code)

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT STOCK_NAME
            FROM STOCK_MASTER
            WHERE SHORT_CODE = %s
               OR LTRIM(SHORT_CODE, '0') = %s
               OR LTRIM(LTRIM(SHORT_CODE, 'A'), '0') = %s
            LIMIT 1
            """,
            (code, key, key),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row or not row[0]:
        logger.warning(
            "[ReportRepository] STOCK_MASTER 종목명 없음 short_code=%s",
            code,
        )
        return None

    name = str(row[0]).strip()
    logger.info(
        "[ReportRepository] STOCK_MASTER short_code=%s stock_name=%s",
        code,
        name,
    )
    return name


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


def save_bot_trade(
    bot_id: int,
    symbol: str,
    select_reason: str,
    buy_price: float | None = None,
    symbol_name: str | None = None,
) -> int | None:
    conn = _connect()
    reason = str(select_reason or "")[:1000]
    name = str(symbol_name).strip()[:200] if symbol_name else None
    buy_at = kst_now_naive()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO BOT_TRADE (
                BOT_ID, SYMBOL, SYMBOL_NAME, SELECT_REASON, BUY_PRICE, BUY_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                bot_id,
                symbol,
                name,
                reason,
                buy_price,
                buy_at,
            ),
        )
        cur.execute("SELECT MAX(TRADE_ID) FROM BOT_TRADE")
        trade_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "[ReportRepository] saved BOT_TRADE id=%s bot_id=%s symbol=%s",
        trade_id,
        bot_id,
        symbol,
    )
    return trade_id


def update_bot_trade_price(
    trade_id: int,
    buy_price: float | None,
) -> None:
    conn = _connect()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE BOT_TRADE
            SET BUY_PRICE = %s
            WHERE TRADE_ID = %s
            """,
            (buy_price, trade_id),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "[ReportRepository] updated BOT_TRADE id=%s price=%s",
        trade_id,
        buy_price,
    )


def save_stock_order(
    pick_id: int | None,
    symbol: str,
    buy_price: float | None,
    buy_qty: int | None,
    order_success: bool | None,
    order_raw: dict | None = None,
) -> int | None:
    conn = _connect()
    raw_text = json.dumps(order_raw, ensure_ascii=False, default=str) if order_raw else None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO STOCK_ORDERS (
                PICK_ID, SYMBOL, BUY_PRICE, BUY_QTY, ORDER_SUCCESS, ORDER_RAW
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                pick_id,
                symbol,
                buy_price,
                buy_qty,
                order_success,
                raw_text,
            ),
        )
        cur.execute("SELECT MAX(ID) FROM STOCK_ORDERS")
        order_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "[ReportRepository] saved STOCK_ORDERS id=%s symbol=%s price=%s",
        order_id,
        symbol,
        buy_price,
    )
    return order_id


def save_stock_pick_senario(
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
            INSERT INTO STOCK_PICKS_SENARIO (REPORT_ID, SYMBOL, STOCK_NAME, REASON)
            VALUES (%s, %s, %s, %s)
            """,
            (
                report_id,
                symbol,
                stock_name or None,
                str(reason),
            ),
        )
        cur.execute("SELECT MAX(ID) FROM STOCK_PICKS_SENARIO")
        pick_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "[ReportRepository] saved STOCK_PICKS_SENARIO id=%s symbol=%s",
        pick_id,
        symbol,
    )
    return pick_id


def save_bot_trade_senario(
    bot_id: int,
    symbol: str,
    select_reason: str,
    buy_price: float | None = None,
    symbol_name: str | None = None,
) -> int | None:
    conn = _connect()
    reason = str(select_reason or "")[:1000]
    name = str(symbol_name).strip()[:200] if symbol_name else None
    buy_at = kst_now_naive()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO BOT_TRADE_SENARIO (
                BOT_ID, SYMBOL, SYMBOL_NAME, SELECT_REASON, BUY_PRICE, BUY_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                bot_id,
                symbol,
                name,
                reason,
                buy_price,
                buy_at,
            ),
        )
        cur.execute("SELECT MAX(TRADE_ID) FROM BOT_TRADE_SENARIO")
        trade_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "[ReportRepository] saved BOT_TRADE_SENARIO id=%s bot_id=%s symbol=%s",
        trade_id,
        bot_id,
        symbol,
    )
    return trade_id


def update_bot_trade_price_senario(
    trade_id: int,
    buy_price: float | None,
) -> None:
    conn = _connect()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE BOT_TRADE_SENARIO
            SET BUY_PRICE = %s
            WHERE TRADE_ID = %s
            """,
            (buy_price, trade_id),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "[ReportRepository] updated BOT_TRADE_SENARIO id=%s price=%s",
        trade_id,
        buy_price,
    )


def save_stock_order_senario(
    pick_id: int | None,
    symbol: str,
    buy_price: float | None,
    buy_qty: int | None,
    order_success: bool | None,
    order_raw: dict | None = None,
) -> int | None:
    conn = _connect()
    raw_text = json.dumps(order_raw, ensure_ascii=False, default=str) if order_raw else None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO STOCK_ORDERS_SENARIO (
                PICK_ID, SYMBOL, BUY_PRICE, BUY_QTY, ORDER_SUCCESS, ORDER_RAW
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                pick_id,
                symbol,
                buy_price,
                buy_qty,
                order_success,
                raw_text,
            ),
        )
        cur.execute("SELECT MAX(ID) FROM STOCK_ORDERS_SENARIO")
        order_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "[ReportRepository] saved STOCK_ORDERS_SENARIO id=%s symbol=%s price=%s",
        order_id,
        symbol,
        buy_price,
    )
    return order_id
