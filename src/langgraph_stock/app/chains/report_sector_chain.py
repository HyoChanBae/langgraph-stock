from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings  # noqa: F401  dotenv → OPENAI_API_KEY


SECTOR_BLOCK_TEMPLATE = """### {sector_name} - {total_score}/100

분류

- {classification}

주요 동인

- {drivers}

모멘텀

- {momentum}

펀더멘털

- {fundamentals}

센티먼트

- {sentiment}

테마

- {theme}

주요 리스크

- {risks}

투자 해석

- {interpretation}
"""

SECTOR_REPORT_TEMPLATE = """## 시장 국면

- {market_regime_summary}

## 섹터 랭킹

{ranking_table_slot}

## 섹터별 분석

{sector_block_slot}

## 섹터 로테이션 시그널

- 주도 섹터: {leading}
- 개선 섹터: {improving}
- 약화 섹터: {weakening}
- 초기 로테이션 후보: {early_candidate}

## 최종 요약

- 최선호 섹터: {top_sector}
- 최선호 근거: {top_reason}
- 차선호 섹터: {second_sector}
- 차선호 근거: {second_reason}
- 관찰 섹터: {watch_sector}
- 관찰 근거: {watch_reason}
- 회피/최약 섹터: {avoid_sector}
- 회피 근거: {avoid_reason}
"""

_FILLED_TEMPLATE = SECTOR_REPORT_TEMPLATE.format(
    market_regime_summary="여기에 내용을 입력하세요.",
    ranking_table_slot="(입력으로 제공된 섹터 랭킹 표를 그대로 복사해 넣으세요.)",
    sector_block_slot="(아래 섹터 블록을 섹터 수만큼 반복하세요.)",
    leading="여기에 내용을 입력하세요.",
    improving="여기에 내용을 입력하세요.",
    weakening="여기에 내용을 입력하세요.",
    early_candidate="여기에 내용을 입력하세요.",
    top_sector="여기에 내용을 입력하세요.",
    top_reason="여기에 내용을 입력하세요.",
    second_sector="여기에 내용을 입력하세요.",
    second_reason="여기에 내용을 입력하세요.",
    watch_sector="여기에 내용을 입력하세요.",
    watch_reason="여기에 내용을 입력하세요.",
    avoid_sector="여기에 내용을 입력하세요.",
    avoid_reason="여기에 내용을 입력하세요.",
)

_FILLED_SECTOR_BLOCK = SECTOR_BLOCK_TEMPLATE.format(
    sector_name="섹터명",
    total_score="총점",
    classification="입력에 주어진 분류를 그대로 쓰세요.",
    drivers="가장 강한 정량 동인부터 2~3개를 각각 한 문장으로 설명하세요.",
    momentum="ETF 추세, S&P 500 대비 상대강도, 모멘텀 가속/둔화 여부를 서술하세요.",
    fundamentals="매출 성장, 이익 추세, 마진 흐름, 재무 건전성을 서술하세요.",
    sentiment="뉴스 센티먼트 방향과 포지셔닝 과열 여부를 서술하세요.",
    theme="정책·구조적 지지 요인을 서술하세요.",
    risks="의미 있는 리스크 2~4개를 세미콜론으로 구분해 나열하세요.",
    interpretation="숫자를 되풀이하지 말고 왜 이 점수가 나왔는지 설명하세요.",
)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 섹터 로테이션 시스템의 퀀트 투자 분석가다. "
        "점수는 외부 정량 모델이 이미 계산했고, 너의 역할은 그 점수가 왜 그렇게 나왔는지 해석하는 것이다.\n\n"
        "반드시 지킬 규칙:\n"
        "1. 점수를 새로 만들거나 추정하거나 수정하지 마라. 주어진 점수와 팩터 값은 확정된 입력이다.\n"
        "2. 섹터 랭킹 표는 입력으로 주어진 표를 그대로 복사해라. 숫자나 순서를 바꾸지 마라.\n"
        "3. 값이 'N/A (평가 불가)'인 팩터는 값을 지어내지 말고 평가할 수 없다고 명시하라.\n"
        "4. 모든 섹터에 대해 긍정 요인과 주요 리스크를 함께 서술하라.\n"
        "5. '확실히', '반드시', '보장', '오를 것이다' 같은 단정적 표현을 쓰지 마라.\n"
        "6. 절대적 가격 예측 대신 섹터 간 상대적 매력도에 집중하라.\n"
        "7. 언론 노출이나 화제성이 크다는 이유만으로 섹터를 추천하지 마라. "
        "높은 센티먼트가 과열 신호일 수 있음을 함께 고려하라.\n"
        "8. 정량적 근거와 정성적 해석을 구분해서 서술하라.\n\n"
        "아래 형식을 한 글자도 바꾸지 말고, 각 항목의 하이픈(-) 아래에만 본문을 한국어로 채워라. "
        "제목을 추가하거나 순서를 바꾸지 마라.\n\n"
        + _FILLED_TEMPLATE
        + "\n섹터별 분석에 쓸 블록 형식:\n\n"
        + _FILLED_SECTOR_BLOCK,
    ),
    (
        "human",
        "기준 시각: {as_of} (한국 시각 KST, UTC로 바꾸지 말 것)\n\n"
        "시장 국면:\n{market_regime}\n\n"
        "매크로 지표:\n{macro_data}\n\n"
        "섹터 랭킹 표 (그대로 복사해 사용할 것):\n{ranking_table}\n\n"
        "섹터별 상세 데이터:\n{sector_detail}\n\n"
        "위 템플릿 형식의 섹터 로테이션 리포트를 작성해줘. "
        "시각을 언급할 때는 위 한국 시각을 그대로 쓰고 UTC로 변환하지 마라.",
    ),
])

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
)

sector_report_chain = prompt | llm | StrOutputParser()
