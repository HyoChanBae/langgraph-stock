from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY


class StockPickResult(BaseModel):
    symbol: str = Field(description="한국 주식 6자리 종목코드. 예: 005930")
    stock_name: str = Field(description="종목명. 예: 삼성전자")
    reason: str = Field(description="오늘 개장 시 오를 것으로 보는 이유를 시장 리포트에 근거해 작성")


prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 국내 주식 트레이더다. "
        "주어진 전체 시장 흐름 리포트만 근거로, "
        "오늘 한국 증시 개장 직후 가장 오를 가능성이 높은 만원이하 종목 딱 1개만 고른다. "
        "반드시 실제 상장 종목의 6자리 종목코드를 쓰고, 여러 종목을 나열하지 마라.",
    ),
    (
        "human",
        "시장 리포트:\n{report_text}\n\n"
        "오늘 개장하면 당장 오를 것 같은 종목 하나와 이유를 추출해줘.",
    ),
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
    StockPickResult
)

stock_pick_chain = prompt | llm
