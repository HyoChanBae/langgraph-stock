from sqlalchemy import DateTime, Integer, String, func
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
