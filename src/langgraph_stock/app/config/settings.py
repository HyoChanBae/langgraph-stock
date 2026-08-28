import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


_PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_PROJECT_ROOT / ".env")


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379"
)

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip() or None
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD") or ""
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
SNOWFLAKE_AUTHENTICATOR = os.getenv("SNOWFLAKE_AUTHENTICATOR", "snowflake")

DATABASE_URL = None
if SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER and SNOWFLAKE_DATABASE:
    DATABASE_URL = (
        f"snowflake://{SNOWFLAKE_USER}:{quote_plus(SNOWFLAKE_PASSWORD)}"
        f"@{SNOWFLAKE_ACCOUNT}/{SNOWFLAKE_DATABASE}/{SNOWFLAKE_SCHEMA}"
        f"?warehouse={SNOWFLAKE_WAREHOUSE}"
        f"&role={SNOWFLAKE_ROLE}"
        f"&authenticator={SNOWFLAKE_AUTHENTICATOR}"
    )
