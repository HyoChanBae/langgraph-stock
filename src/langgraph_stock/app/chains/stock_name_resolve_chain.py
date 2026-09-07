from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY


class OfficialStockNameResult(BaseModel):
    found: bool = Field(description="목록에서 같은 회사 공식 종목명을 찾았으면 true")
    stock_name: str = Field(
        description="목록에 있는 공식 종목명을 그대로 복사. 없으면 빈 문자열"
    )


prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 한국 상장 종목명 매칭기다. "
        "사용자가 말한 종목과 같은 회사의 공식 종목명을 목록에서 딱 1개 고른다. "
        "반드시 목록 문자열을 그대로 복사하고, 새 이름을 만들지 마라. "
        "엔씨소프트는 NC처럼 약칭으로 들어 있을 수 있다. "
        "다른 회사이거나 확정할 수 없으면 found=false 로 둔다.",
    ),
    (
        "human",
        "사용자가 말한 종목명: {query_name}\n\n"
        "STOCK_MASTER 종목명 목록:\n{catalog}\n\n"
        "같은 회사의 공식 종목명 1개를 목록에서 고르거나, 없으면 found=false.",
    ),
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
    OfficialStockNameResult
)

stock_name_resolve_chain = prompt | llm


class CurrentStockNameResult(BaseModel):
    found: bool = Field(description="현재 한국 상장사의 공식 종목명을 알면 true")
    renamed: bool = Field(description="사명 변경·약칭이면 true, 같은 이름 그대로면 false")
    stock_name: str = Field(
        description="현재 증권사에 등록된 공식 한글 종목명. 모르면 빈 문자열"
    )


rename_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 한국 상장사 상호 확인기다. "
        "주어진 이름이 옛 사명, 약칭, 영문명이면 현재 공식 한글 종목명을 말한다. "
        "예: 세틀뱅크 → 헥토파이낸셜, 엔씨소프트 → NC. "
        "글자만 비슷한 다른 회사(인포뱅크, 케이뱅크 등)로 바꾸지 마라. "
        "상장사가 아니거나 현재 공식명을 모르면 found=false.",
    ),
    (
        "human",
        "종목명: {query_name}\n\n"
        "이 회사가 사명 변경 또는 약칭인지 확인하고, "
        "현재 한국 상장 공식 종목명 1개를 말해라.",
    ),
])

rename_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
    CurrentStockNameResult
)

stock_name_rename_chain = rename_prompt | rename_llm
