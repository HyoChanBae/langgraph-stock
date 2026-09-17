import json
import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.chains.macro_chain import macro_report_chain
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
from app.macro.signals import AXIS_LABELS, compute_signals
from app.repositories.report_repository import kst_now, save_market_report


logger = logging.getLogger(__name__)

MACRO_SYMBOL = "MACRO"

# 5대 축 중 이만큼 이상 비면 해석할 근거가 부족하다고 보고 리포트를 만들지 않는다.
MAX_MISSING_AXES = 3


class MacroAgentState(TypedDict):
    as_of: str
    market_raw: dict
    fred_raw: dict
    signals: dict
    missing: list[str]
    regime: dict
    sector_scores: list[dict]
    indicator_table: str
    sector_table: str
    report_text: str
    report_id: int | None


def collect_market(state: MacroAgentState):
    logger.info("[node1a] yfinance 시장 지표 수집")
    return {"market_raw": fetch_market_bundle()}


def collect_fred(state: MacroAgentState):
    logger.info("[node1b] FRED 물가·고용 지표 수집")
    return {"fred_raw": fetch_macro_bundle()}


def compute_axes(state: MacroAgentState):
    signals, missing = compute_signals(
        state.get("market_raw") or {},
        state.get("fred_raw") or {},
    )
    logger.info("[node2] 5대 축 산출, 결측 %s개", len(missing))
    return {"signals": signals, "missing": missing}


def has_enough_data(state: MacroAgentState) -> Literal["classify_regime", "end"]:
    missing = state.get("missing") or []
    if len(missing) >= MAX_MISSING_AXES:
        labels = ", ".join(AXIS_LABELS[key] for key in missing)
        logger.warning("[route] 평가 불가 축이 %s개(%s)라 리포트를 건너뜁니다", len(missing), labels)
        return "end"
    return "classify_regime"


def judge_regime(state: MacroAgentState):
    regime = classify_regime(state["signals"])
    logger.info("[node3] 레짐 %s 신뢰도 %.2f", regime["name"], regime["confidence"])
    return {"regime": regime}


def rank_sectors(state: MacroAgentState):
    sector_scores = score_sectors(state["signals"], state["regime"])
    return {
        "sector_scores": sector_scores,
        "indicator_table": build_indicator_table(state["signals"]),
        "sector_table": build_sector_table(sector_scores),
    }


def write_report(state: MacroAgentState):
    as_of = state["as_of"]
    report_text = macro_report_chain.invoke({
        "as_of": as_of,
        "regime_brief": build_regime_brief(state["regime"], state.get("missing") or []),
        "indicator_table": state["indicator_table"],
        "raw_notes": build_raw_notes(state["signals"]),
        "sector_table": state["sector_table"],
        "sector_detail": build_sector_detail(state["sector_scores"]),
    })

    logger.info("[node4] 리포트 생성 완료")
    return {"report_text": f"기준 시각: {as_of}\n\n{report_text}"}


def save_report(state: MacroAgentState):
    market_context = json.dumps(
        {
            "regime": state["regime"],
            "signals": state["signals"],
            "sector_scores": state["sector_scores"],
            "missing": state.get("missing") or [],
        },
        ensure_ascii=False,
        default=str,
    )

    report_id = save_market_report(
        symbols=[MACRO_SYMBOL],
        report=state["report_text"],
        market_context=market_context,
        created_at=kst_now().replace(tzinfo=None),
    )

    logger.info("[node5] MARKET_REPORTS 저장 id=%s", report_id)
    return {"report_id": report_id}


builder = StateGraph(MacroAgentState)

builder.add_node("collect_market", collect_market)
builder.add_node("collect_fred", collect_fred)
builder.add_node("compute_axes", compute_axes)
builder.add_node("classify_regime", judge_regime)
builder.add_node("score_sectors", rank_sectors)
builder.add_node("write_report", write_report)
builder.add_node("save_report", save_report)

# 두 수집 노드는 같은 superstep에서 병렬로 돌고 compute_axes 에서 합쳐진다.
builder.add_edge(START, "collect_market")
builder.add_edge(START, "collect_fred")
builder.add_edge("collect_market", "compute_axes")
builder.add_edge("collect_fred", "compute_axes")

builder.add_conditional_edges(
    "compute_axes",
    has_enough_data,
    {
        "classify_regime": "classify_regime",
        "end": END,
    },
)
builder.add_edge("classify_regime", "score_sectors")
builder.add_edge("score_sectors", "write_report")
builder.add_edge("write_report", "save_report")
builder.add_edge("save_report", END)

graph = builder.compile()
