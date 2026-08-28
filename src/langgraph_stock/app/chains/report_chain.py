from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 국내 주식 시장 리포트 작성자다. "
        "주어진 종목들에 대해 시황, 리스크, 한 줄 요약을 한국어로 작성하라.",
    ),
    (
        "human",
        "종목 코드: {symbols}\n"
        "참고 데이터: {market_context}\n"
        "리포트를 작성해줘.",
    ),
])

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
)

report_chain = prompt | llm | StrOutputParser()
