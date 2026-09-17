from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY


SECTOR_BLOCK_TEMPLATE = """### {sector_name} ({sector_etf}) - {macro_score}/30

유리한 이유

- {drivers}

부담 요인

- {headwinds}

확인 지표

- {watch}
"""

MACRO_REPORT_TEMPLATE = """## 핵심 결론

- 현재 경제 환경: {regime_line}
- 유리한 섹터: {favored}
- 불리한 섹터: {unfavored}
- 한 줄 요약: {headline}

## 5대 지표 판정

{indicator_table_slot}

- 금리: {rates_comment}
- 물가: {inflation_comment}
- 달러: {dollar_comment}
- 유가: {oil_comment}
- 고용: {employment_comment}

## 레짐 판정 근거

- 성장 축: {growth_comment}
- 물가 축: {inflation_axis_comment}
- 유동성 보정: {liquidity_comment}
- 판정 신뢰도: {confidence_comment}

## 섹터별 매크로 점수

{sector_table_slot}

## 상위 섹터 해석

{sector_block_slot}

## 레짐 전환 신호

- 상방 전환 트리거: {upside_trigger}
- 하방 전환 트리거: {downside_trigger}
- 판정 무효화 조건: {invalidation}

## 리스크

- {risks}
"""

_FILLED_TEMPLATE = MACRO_REPORT_TEMPLATE.format(
    regime_line="입력에 주어진 레짐 이름과 성장·물가 점수를 그대로 쓰세요.",
    favored="상위 섹터를 점수와 함께 3개까지 쓰세요.",
    unfavored="하위 섹터를 점수와 함께 2개까지 쓰세요.",
    headline="지금 어떤 경제환경이고 그래서 어느 쪽에 서야 하는지 한 문장으로 쓰세요.",
    indicator_table_slot="(입력으로 제공된 5대 지표 표를 그대로 복사해 넣으세요.)",
    rates_comment="레벨·방향·커브 모양을 근거로 2~3문장.",
    inflation_comment="헤드라인과 근원, 시장 기대인플레의 방향 차이를 2~3문장.",
    dollar_comment="달러 방향이 어떤 섹터로 자금을 밀어내는지 2~3문장.",
    oil_comment="유가 변동이 수요 때문인지 공급 때문인지 구분해 2~3문장.",
    employment_comment="고용 둔화 속도와 침체 신호 여부를 2~3문장.",
    growth_comment="성장 점수가 왜 그 값인지 구성 지표로 설명하세요.",
    inflation_axis_comment="물가 점수가 왜 그 값인지 구성 지표로 설명하세요.",
    liquidity_comment="입력에 주어진 보정 조건을 근거로 설명하세요. 없으면 없다고 쓰세요.",
    confidence_comment="신뢰도 수치와 평가 불가 축을 언급하고, 판정을 얼마나 믿을지 서술하세요.",
    sector_table_slot="(입력으로 제공된 섹터 점수 표를 그대로 복사해 넣으세요.)",
    sector_block_slot="(아래 섹터 블록을 상위 섹터 수만큼 반복하세요.)",
    upside_trigger="어떤 실제 지표가 어느 수준까지 가면 성장 축이 위로 뒤집히는지 쓰세요.",
    downside_trigger="어떤 실제 지표가 어느 수준까지 가면 성장 축이 아래로 뒤집히는지 쓰세요.",
    invalidation="현재 레짐 판정이 틀렸다고 인정해야 할 실제 지표 조건을 쓰세요.",
    risks="의미 있는 리스크 2~4개를 세미콜론으로 구분해 나열하세요.",
)

_FILLED_SECTOR_BLOCK = SECTOR_BLOCK_TEMPLATE.format(
    sector_name="섹터명",
    sector_etf="ETF 티커",
    macro_score="입력에 주어진 점수",
    drivers="어떤 매크로 축이 이 섹터를 밀어올리는지 설명하세요.",
    headwinds="어떤 축이 부담인지 설명하세요. 부담이 없으면 없다고 쓰세요.",
    watch="이 섹터 판단이 바뀌려면 무엇을 봐야 하는지 쓰세요.",
)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 매크로 전략가다. "
        "핵심 질문은 '지금 어떤 섹터에 유리한 경제환경인가'이고, "
        "금리·물가·달러·유가·고용 다섯 축으로 답한다.\n\n"
        "점수와 레짐 판정은 외부 정량 모델이 이미 계산했고, "
        "너의 역할은 그 결과가 왜 그렇게 나왔는지 해석하는 것이다.\n\n"
        "반드시 지킬 규칙:\n"
        "1. 점수를 새로 만들거나 추정하거나 수정하지 마라. 주어진 점수와 지표 값은 확정된 입력이다.\n"
        "2. 5대 지표 표와 섹터 점수 표는 입력으로 주어진 표를 그대로 복사해라. 숫자나 순서를 바꾸지 마라.\n"
        "3. 값이 'N/A (평가 불가)'인 축은 값을 지어내지 말고 평가할 수 없다고 명시하라.\n"
        "4. 레짐 판정은 입력에 주어진 것을 따르고, 네 판단으로 바꾸지 마라.\n"
        "5. '확실히', '반드시', '보장', '오를 것이다' 같은 단정적 표현을 쓰지 마라.\n"
        "6. 절대적 지수 예측 대신 섹터 간 상대적 매력도에 집중하라.\n"
        "7. 신뢰도가 낮거나 원점 거리가 짧으면 레짐 경계에 걸쳐 있다는 점을 분명히 밝혀라.\n"
        "8. 레짐 전환 신호에는 성장 점수·물가 점수·신뢰도 같은 모델 내부 수치를 쓰지 마라. "
        "이 값들은 시장에서 직접 관측할 수 없다. "
        "10년물 금리, WTI 가격, 달러인덱스, CPI 전년동월비, 실업률, 비농업 고용처럼 "
        "발표되거나 호가되는 지표만 쓰고, 현재 수준에서 어느 방향으로 얼마나 가야 하는지 "
        "단위를 붙인 임계값으로 제시하라.\n\n"
        "아래 형식을 한 글자도 바꾸지 말고, 각 항목의 하이픈(-) 아래에만 본문을 한국어로 채워라. "
        "제목을 추가하거나 순서를 바꾸지 마라.\n\n"
        + _FILLED_TEMPLATE
        + "\n상위 섹터 해석에 쓸 블록 형식:\n\n"
        + _FILLED_SECTOR_BLOCK,
    ),
    (
        "human",
        "기준 시각: {as_of} (한국 시각 KST, UTC로 바꾸지 말 것)\n\n"
        "레짐 판정:\n{regime_brief}\n\n"
        "5대 지표 표 (그대로 복사해 사용할 것):\n{indicator_table}\n\n"
        "지표 특이 신호:\n{raw_notes}\n\n"
        "섹터 점수 표 (그대로 복사해 사용할 것):\n{sector_table}\n\n"
        "섹터별 상세 데이터:\n{sector_detail}\n\n"
        "위 템플릿 형식의 매크로 리포트를 작성해줘. "
        "시각을 언급할 때는 위 한국 시각을 그대로 쓰고 UTC로 변환하지 마라.",
    ),
])

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
)

macro_report_chain = prompt | llm | StrOutputParser()
