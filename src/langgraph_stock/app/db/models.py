from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MarketReport(Base):
    __tablename__ = "MARKET_REPORTS"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbols: Mapped[str] = mapped_column(String(255), nullable=False)
    market_context: Mapped[str | None] = mapped_column(String, nullable=True)
    report: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class StockPick(Base):
    __tablename__ = "STOCK_PICKS"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class StockOrder(Base):
    __tablename__ = "STOCK_ORDERS"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pick_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    buy_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    order_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    ordered_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class StockMaster(Base):
    __tablename__ = "STOCK_MASTER"

    short_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    standard_code: Mapped[str] = mapped_column(String(30), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(200), nullable=False)
    market_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    create_date: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
    )


class BotTrade(Base):
    __tablename__ = "BOT_TRADE"

    trade_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    select_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    buy_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_at: Mapped[object] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
    )
