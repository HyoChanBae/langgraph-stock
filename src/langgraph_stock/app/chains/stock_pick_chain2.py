from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY


class OverseasStockPickResult(BaseModel):
    symbol: str = Field(description="미국 주식 티커. 예: AAPL, TSLA")
    stock_name: str = Field(description="영문 종목명. 예: Apple Inc.")
    reason: str = Field(description="오늘 미국 증시 개장 시 오를 것으로 보는 이유를 시장 리포트에 근거해 작성")


prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 미국 주식 트레이더다. "
        "주어진 전체 시장 흐름 리포트만 근거로, "
        "오늘 미국 증시 개장 직후 가장 오를 가능성이 높은 종목 딱 1개만 고른다. "
        "반드시 실제 미국 상장 종목의 티커(예: AAPL)를 쓰고, 한국 6자리 종목코드는 쓰지 마라. "
        "여러 종목을 나열하지 마라. "
        "종목명(stock_name)은 그 티커의 공식 영문 종목명과 반드시 일치해야 한다.",
    ),
    (
        "human",
        "시장 리포트:\n{report_text}\n\n"
        "오늘 개장하면 당장 오를 것 같은 미국 주식 하나와 이유를 추출해줘.",
    ),
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7).with_structured_output(
    OverseasStockPickResult
)

overseas_stock_pick_chain = prompt | llm
