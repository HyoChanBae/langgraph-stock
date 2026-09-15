import json
import logging

from app.config import settings  # noqa: F401  dotenv 로드
from app.chains.report_sector_chain import sector_report_chain
from app.repositories.report_repository import kst_now, save_market_report


logger = logging.getLogger(__name__)

SECTOR_SYMBOL = "SECTOR"

NA = "N/A (평가 불가)"

FACTOR_KEYS = [
    ("macro_score", "매크로"),
    ("momentum_score", "모멘텀"),
    ("fundamental_score", "펀더멘털"),
    ("sentiment_score", "센티먼트"),
    ("theme_score", "테마"),
]

DETAIL_KEYS = [
    ("momentum_data", "모멘텀 데이터"),
    ("fundamental_data", "펀더멘털 데이터"),
    ("sentiment_data", "센티먼트 데이터"),
    ("theme_data", "테마 데이터"),
]


def classify(total_score) -> str:
    """정량 모델 점수를 투자 등급 문구로 매핑한다. 점수 자체는 바꾸지 않는다."""
    if not isinstance(total_score, (int, float)):
        return NA
    if total_score >= 85:
        return "Strong Sector Leadership (강한 섹터 주도)"
    if total_score >= 75:
        return "Attractive (긍정적)"
    if total_score >= 60:
        return "Neutral / Selective (중립·선별적)"
    if total_score >= 40:
        return "Weak (약세)"
    return "Risk-Off / Avoid (회피)"


def _format_value(value) -> str:
    if value is None or value == "" or value == {} or value == []:
        return NA
    if isinstance(value, dict):
        return ", ".join(f"{k}={_format_value(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(_format_value(v) for v in value)
    return str(value)


def _sort_key(sector: dict):
    score = sector.get("total_score")
    return score if isinstance(score, (int, float)) else float("-inf")


def build_ranking_table(ranked: list[dict]) -> str:
    header = (
        "| 순위 | 섹터 | ETF | 총점 | 매크로 | 모멘텀 | 펀더멘털 | 센티먼트 | 테마 | 투자 판단 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    rows = []
    for rank, sector in enumerate(ranked, start=1):
        cells = [
            str(rank),
            _format_value(sector.get("sector")),
            _format_value(sector.get("sector_etf")),
            _format_value(sector.get("total_score")),
        ]
        cells += [_format_value(sector.get(key)) for key, _ in FACTOR_KEYS]
        cells.append(classify(sector.get("total_score")))
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header] + rows)


def build_sector_detail(ranked: list[dict]) -> str:
    blocks = []
    for rank, sector in enumerate(ranked, start=1):
        lines = [
            f"[{rank}] {_format_value(sector.get('sector'))} "
            f"(ETF: {_format_value(sector.get('sector_etf'))})",
            f"- 총점: {_format_value(sector.get('total_score'))}/100",
            f"- 분류: {classify(sector.get('total_score'))}",
        ]
        for key, label in FACTOR_KEYS:
            lines.append(f"- {label} 점수: {_format_value(sector.get(key))}")
        for key, label in DETAIL_KEYS:
            lines.append(f"- {label}: {_format_value(sector.get(key))}")
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def execute_sector_report_logic(
    sectors: list[dict],
    market_regime: str = "",
    macro_data: str = "",
    as_of: str | None = None,
):
    if not sectors:
        raise ValueError("섹터 점수 데이터가 비어 있습니다")

    created_at = kst_now()
    as_of = as_of or created_at.strftime("%Y-%m-%d %H:%M KST")

    logger.info(
        "[ReportSector] sector rotation report as_of=%s sectors=%s",
        as_of,
        len(sectors),
    )

    ranked = sorted(sectors, key=_sort_key, reverse=True)
    ranking_table = build_ranking_table(ranked)
    sector_detail = build_sector_detail(ranked)

    report_text = sector_report_chain.invoke({
        "as_of": as_of,
        "market_regime": market_regime or "데이터 없음 (테스트)",
        "macro_data": macro_data or "데이터 없음 (테스트)",
        "ranking_table": ranking_table,
        "sector_detail": sector_detail,
    })
    report_text = f"기준 시각: {as_of}\n\n{report_text}"

    logger.info("[ReportSector] report generated")

    market_context = json.dumps(
        {
            "market_regime": market_regime,
            "macro_data": macro_data,
            "sectors": sectors,
        },
        ensure_ascii=False,
        default=str,
    )

    report_id = save_market_report(
        symbols=[SECTOR_SYMBOL],
        report=report_text,
        market_context=market_context,
        created_at=created_at.replace(tzinfo=None),
    )

    logger.info("[ReportSector] saved to snowflake id=%s", report_id)

    return {
        "id": report_id,
        "symbols": [SECTOR_SYMBOL],
        "report": report_text,
        "ranking_table": ranking_table,
    }


SAMPLE_SECTORS = [
    {
        "sector": "AI Semiconductor",
        "sector_etf": "SMH",
        "macro_score": 28,
        "momentum_score": 24,
        "fundamental_score": 22,
        "sentiment_score": 9,
        "theme_score": 9,
        "total_score": 92,
        "momentum_data": {
            "return_1m": "+7.2%",
            "return_3m": "+18.4%",
            "return_6m": "+31.0%",
            "relative_strength_vs_spx_3m": "+10.4%",
        },
        "fundamental_data": {
            "revenue_growth_yoy": "+38%",
            "eps_growth_yoy": "+52%",
            "operating_margin": "41%",
            "representative": "NVDA, AMD, AVGO, TSM, ASML",
        },
        "sentiment_data": {
            "news_sentiment": "강한 긍정",
            "positioning": "혼잡(crowded) 신호",
        },
        "theme_data": "데이터센터 증설, AI 가속기 수요, 전력 인프라 투자",
    },
    {
        "sector": "Nuclear Energy",
        "sector_etf": "NLR",
        "macro_score": 22,
        "momentum_score": 18,
        "fundamental_score": 15,
        "sentiment_score": 8,
        "theme_score": 10,
        "total_score": 73,
        "momentum_data": {
            "return_1m": "+3.1%",
            "return_3m": "+9.6%",
            "relative_strength_vs_spx_3m": "+1.6%",
        },
        "fundamental_data": {
            "revenue_growth_yoy": "+12%",
            "eps_growth_yoy": "흑자 전환 구간",
            "representative": "CCJ, CEG, SMR, OKLO",
        },
        "sentiment_data": None,
        "theme_data": "에너지 안보 정책, SMR 배치, 전력망 신뢰성 수요",
    },
    {
        "sector": "Defense",
        "sector_etf": "ITA",
        "macro_score": 20,
        "momentum_score": 14,
        "fundamental_score": 17,
        "sentiment_score": 6,
        "theme_score": 9,
        "total_score": 66,
        "momentum_data": {
            "return_1m": "-1.4%",
            "return_3m": "+4.2%",
            "relative_strength_vs_spx_3m": "-3.8%",
        },
        "fundamental_data": {
            "revenue_growth_yoy": "+8%",
            "eps_growth_yoy": "+6%",
            "operating_margin": "11%",
            "representative": "LMT, RTX, NOC, GD",
        },
        "sentiment_data": {"news_sentiment": "중립"},
        "theme_data": "국방 예산 증가, 지정학적 긴장, NATO 지출 확대",
    },
]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = execute_sector_report_logic(
        sectors=SAMPLE_SECTORS,
        market_regime="금리 인하 사이클 초입, 위험선호 회복 국면 (테스트 입력)",
        macro_data="Fed Funds 4.00%, US 10Y 4.1% 하향 안정, CPI 2.6%, ISM PMI 51.2 (테스트 입력)",
    )

    print("\n===== SECTOR ROTATION REPORT =====\n")
    print(result["report"])
    print("\n===== SNOWFLAKE INSERT =====\n")
    print(result["id"])
