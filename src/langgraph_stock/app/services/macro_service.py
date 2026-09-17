import logging
import sys

from app.config import settings  # noqa: F401  dotenv 로드
from app.graphs.macro_agent import MACRO_SYMBOL, graph
from app.macro.format import (
    build_indicator_table,
    build_raw_notes,
    build_regime_brief,
    build_sector_detail,
    build_sector_table,
)
from app.macro.fred_client import fetch_macro_bundle
from app.macro.market_client import fetch_market_bundle
from app.macro.regime import classify_regime
from app.macro.sector_map import score_sectors
from app.macro.signals import compute_signals
from app.repositories.report_repository import kst_now


logger = logging.getLogger(__name__)


def execute_macro_logic(as_of: str | None = None) -> dict:
    """매크로 에이전트를 실행하고 MACRO 리포트를 저장한다."""
    created_at = kst_now()
    as_of = as_of or created_at.strftime("%Y-%m-%d %H:%M KST")

    logger.info("[MacroService] macro agent as_of=%s", as_of)

    final_state = graph.invoke({"as_of": as_of})

    report_text = final_state.get("report_text")
    if not report_text:
        logger.warning("[MacroService] 데이터 부족으로 리포트를 만들지 못했습니다")
        return {
            "id": None,
            "symbols": [MACRO_SYMBOL],
            "report": None,
            "missing": final_state.get("missing") or [],
        }

    regime = final_state.get("regime") or {}
    logger.info(
        "[MacroService] %s 리포트 저장 id=%s",
        regime.get("name"),
        final_state.get("report_id"),
    )

    return {
        "id": final_state.get("report_id"),
        "symbols": [MACRO_SYMBOL],
        "report": report_text,
        "regime": regime,
        "sector_scores": final_state.get("sector_scores") or [],
        "missing": final_state.get("missing") or [],
    }


def describe_quant_output(market: dict, fred: dict) -> str:
    """LLM 없이 정량 계층만 돌려 결과를 출력용 문자열로 만든다."""
    signals, missing = compute_signals(market, fred)
    regime = classify_regime(signals)
    sectors = score_sectors(signals, regime)

    return "\n\n".join([
        "===== 레짐 판정 =====",
        build_regime_brief(regime, missing),
        "===== 5대 지표 =====",
        build_indicator_table(signals),
        "===== 특이 신호 =====",
        build_raw_notes(signals),
        "===== 섹터 점수 =====",
        build_sector_table(sectors),
        "===== 섹터 상세 =====",
        build_sector_detail(sectors),
    ])


# 네트워크 없이 판정 로직만 검증하기 위한 고정 입력 (성장 유지 + 물가 둔화 시나리오)
SAMPLE_MARKET = {
    "ust_10y": {"value": 4.12, "diff_1m": -0.08, "diff_3m": -0.31, "pct_1m": -0.019, "pct_3m": -0.070, "as_of": "샘플"},
    "ust_5y": {"value": 3.88, "diff_1m": -0.10, "diff_3m": -0.35, "pct_1m": -0.025, "pct_3m": -0.083, "as_of": "샘플"},
    "ust_3m": {"value": 4.05, "diff_1m": -0.12, "diff_3m": -0.48, "pct_1m": -0.029, "pct_3m": -0.106, "as_of": "샘플"},
    "dollar_index": {"value": 101.4, "diff_1m": -0.6, "diff_3m": -2.4, "pct_1m": -0.006, "pct_3m": -0.023, "as_of": "샘플"},
    "wti": {"value": 68.4, "diff_1m": -1.9, "diff_3m": -6.2, "pct_1m": -0.027, "pct_3m": -0.083, "as_of": "샘플"},
    "brent": {"value": 72.1, "diff_1m": -1.8, "diff_3m": -6.0, "pct_1m": -0.024, "pct_3m": -0.077, "as_of": "샘플"},
    "copper": {"value": 4.62, "diff_1m": 0.08, "diff_3m": 0.24, "pct_1m": 0.018, "pct_3m": 0.055, "as_of": "샘플"},
    "gold": {"value": 2680.0, "diff_1m": 15.0, "diff_3m": 40.0, "pct_1m": 0.006, "pct_3m": 0.015, "as_of": "샘플"},
    "vix": {"value": 15.8, "diff_1m": -1.2, "diff_3m": -2.6, "pct_1m": -0.071, "pct_3m": -0.141, "as_of": "샘플"},
    "hy_credit": {"value": 79.6, "diff_1m": 0.5, "diff_3m": 1.6, "pct_1m": 0.006, "pct_3m": 0.021, "as_of": "샘플"},
    "treasury_etf": {"value": 95.2, "diff_1m": 0.3, "diff_3m": 0.5, "pct_1m": 0.003, "pct_3m": 0.005, "as_of": "샘플"},
    "curve_10y_3m": {"value": 0.07, "diff_1m": 0.04, "diff_3m": 0.17, "as_of": "샘플"},
    "copper_gold": {"value": 0.00172, "pct_1m": 0.012, "pct_3m": 0.039, "as_of": "샘플"},
    "credit_proxy": {"value": 0.836, "pct_1m": 0.003, "pct_3m": 0.016, "as_of": "샘플"},
}

SAMPLE_FRED = {
    "available": True,
    "cpi_yoy": {"value": 2.6, "chg_1m": -0.1, "chg_3m": -0.4, "as_of": "샘플"},
    "core_cpi_yoy": {"value": 2.9, "chg_1m": -0.1, "chg_3m": -0.3, "as_of": "샘플"},
    "breakeven_5y": {"value": 2.22, "chg_1m": -0.04, "chg_3m": -0.12, "as_of": "샘플"},
    "breakeven_10y": {"value": 2.28, "chg_1m": -0.03, "chg_3m": -0.10, "as_of": "샘플"},
    "unemployment": {"value": 4.2, "chg_1m": 0.0, "chg_3m": 0.1, "as_of": "샘플"},
    "initial_claims": {"value": 221000.0, "chg_1m": 3000.0, "chg_3m": 6000.0, "as_of": "샘플"},
    "fed_funds": {"value": 4.33, "chg_1m": -0.25, "chg_3m": -0.50, "as_of": "샘플"},
    "real_yield_10y": {"value": 1.84, "chg_1m": -0.05, "chg_3m": -0.21, "as_of": "샘플"},
    "payroll_change": {"value": 168.0, "chg_1m": -12.0, "chg_3m": -30.0, "as_of": "샘플"},
    "payroll_3m_avg": 172.0,
    "initial_claims_4w_avg": 219500.0,
    "sahm_gap": 0.17,
}


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "--dry":
        print(describe_quant_output(SAMPLE_MARKET, SAMPLE_FRED))
    elif mode == "--data":
        print(describe_quant_output(fetch_market_bundle(), fetch_macro_bundle()))
    else:
        result = execute_macro_logic()
        print("\n===== MACRO REPORT =====\n")
        print(result["report"])
        print("\n===== SNOWFLAKE INSERT =====\n")
        print(result["id"])
