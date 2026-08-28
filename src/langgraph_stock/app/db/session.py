import snowflake.sqlalchemy  # noqa: F401  snowflake dialect 등록

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import DATABASE_URL


if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL이 없습니다. .env Snowflake 설정을 확인하세요.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
