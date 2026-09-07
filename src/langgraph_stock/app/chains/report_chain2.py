from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY


MARKET_REPORT_TEMPLATE = """현재 기준 전체 시장 흐름

- {market_flow}

연준 인사 발언 및 통화정책 방향

- {fed_policy}

국채 시장 흐름

- {treasury}

환율 시장

- {fx}

주요 인사 및 국가 발언

- {officials}

주요 글로벌 매크로 환경

- {macro}

인플레이션 및 원자재 시장

- {inflation_commodities}

고용 및 소비 지표

- {employment_consumption}

글로벌 금융시장 영향

- {global_markets}

주요 이벤트 및 리스크

- {events_risks}
"""

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 글로벌 매크로/금융시장 리포트 작성자다. "
        "아래 목차와 형식을 한 글자도 바꾸지 말고, 각 항목의 하이픈(-) 아래에만 본문을 채워라. "
        "제목을 추가하거나 순서를 바꾸지 마라. "
        "각 항목은 2~4문장으로 핵심만 한국어로 작성하라. "
        "참고 데이터가 부족하면 일반적인 시장 컨센서스를 쓰되, 단정적인 예측은 피하라.\n\n"
        "반드시 아래 형식 그대로 출력하라:\n\n"
        + MARKET_REPORT_TEMPLATE.format(
            market_flow="여기에 내용을 입력하세요",
            fed_policy="여기에 내용을 입력하세요.",
            treasury="여기에 내용을 입력하세요.",
            fx="여기에 내용을 입력하세요.",
            officials="여기에 내용을 입력하세요.",
            macro="여기에 내용을 입력하세요.",
            inflation_commodities="여기에 내용을 입력하세요.",
            employment_consumption="여기에 내용을 입력하세요.",
            global_markets="여기에 내용을 입력하세요.",
            events_risks="여기에 내용을 입력하세요.",
        ),
    ),
    (
        "human",
        "기준 시각: {as_of} (한국 시각 KST, UTC로 바꾸지 말 것)\n"
        "참고 데이터: {market_context}\n"
        "위 템플릿 형식의 전체 시장 흐름 리포트를 작성해줘. "
        "시각을 언급할 때는 위 한국 시각을 그대로 쓰고 UTC로 변환하지 마라.",
    ),
])

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
)

market_flow_chain = prompt | llm | StrOutputParser()
