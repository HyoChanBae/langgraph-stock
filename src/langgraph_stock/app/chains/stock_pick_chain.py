from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY


class StockPickResult(BaseModel):
    stock_name: str = Field(description="한국 상장 종목의 공식 한글 종목명. 예: 삼성전자. 종목코드는 쓰지 말 것")
    reason: str = Field(description="오늘 개장 시 오를 것으로 보는 이유를 시장 리포트에 근거해 작성")


prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 국내 주식 트레이더다. "
        "주어진 전체 시장 흐름 리포트만 근거로, "
        "오늘 한국 증시 개장 직후 가장 오를 가능성이 높은 "
        "30,000원 이하 종목 딱 1개만 고른다. "
        "종목코드는 절대 쓰지 말고 종목명만 쓴다. "
        "여러 종목을 나열하지 마라. "
        "가능하면 증권사 종목명 그대로 쓰고, 약칭만 있는 종목은 약칭을 써도 된다.",
    ),
    (
        "human",
        "시장 리포트:\n{report_text}\n\n"
        "오늘 개장하면 당장 오를 것 같은 30,000원 이하 종목의 공식 한글 종목명 하나와 이유를 추출해줘.",
    ),
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7).with_structured_output(
    StockPickResult
)

stock_pick_chain = prompt | llm
