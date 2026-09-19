"""정량 결과를 LLM에 그대로 넘길 표/문단으로 만든다. 여기서 만든 숫자는 LLM이 바꾸지 않는다."""

from app.macro.signals import AXIS_LABELS, NA


TOP_SECTOR_COUNT = 6


def _join(values: list[str]) -> str:
    """빈 목록은 '없음'이다. NA(평가 불가)는 데이터가 빠진 축에만 쓴다."""
    return ", ".join(values) if values else "없음"


def build_indicator_table(signals: dict) -> str:
    header = (
        "| 축 | 현재 수준 | 1개월 변화 | 3개월 변화 | 방향 | 신호강도 |\n"
        "| --- | --- | --- | --- | --- | --- |"
    )

    rows = []
    for key in AXIS_LABELS:
        axis = signals[key]
        strength = f"{axis['score']:+.2f}" if axis["available"] else NA
        rows.append(
            "| "
            + " | ".join([
                axis["label"],
                axis["level"],
                axis["chg_1m"],
                axis["chg_3m"],
                axis["direction"],
                strength,
            ])
            + " |"
        )

    return "\n".join([header] + rows)


def _layer_label(sector: dict) -> str:
    return "하위" if sector.get("layer") == "overlay" else "부모"


def _parent_label(sector: dict) -> str:
    return sector.get("parent") or "-"


def build_sector_table(sectors: list[dict]) -> str:
    header = (
        "| 순위 | 계층 | 섹터 | 부모 | ETF | 매크로 점수 | 유리 요인 | 부담 요인 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |"
    )

    rows = []
    for rank, sector in enumerate(sectors, start=1):
        rows.append(
            "| "
            + " | ".join([
                str(rank),
                _layer_label(sector),
                sector["sector"],
                _parent_label(sector),
                sector["sector_etf"],
                f"{sector['macro_score']}/30",
                _join(sector["drivers"]),
                _join(sector["headwinds"]),
            ])
            + " |"
        )

    return "\n".join([header] + rows)


def build_regime_brief(regime: dict, missing: list[str]) -> str:
    lines = [
        f"- 판정: {regime['name']} ({regime['summary']})",
        f"- 성장 점수: {regime['growth_score']:+.2f} (커버리지 {regime['growth_coverage']:.0%})",
        f"- 물가 점수: {regime['inflation_score']:+.2f} (커버리지 {regime['inflation_coverage']:.0%})",
        f"- 원점 거리: {regime['distance']:.2f} (작을수록 레짐 경계에 걸쳐 있음)",
        f"- 신뢰도: {regime['confidence']:.2f} (5대 축 중 {regime['available_axes']}개 평가 가능)",
    ]

    caveats = regime.get("caveats") or []
    if caveats:
        lines.append("- 판정 유보 사항:")
        lines += [f"  - {item}" for item in caveats]

    modifiers = regime.get("modifiers") or []
    if modifiers:
        lines.append("- 유동성·가격 보정:")
        lines += [f"  - {item['label']}" for item in modifiers]
    else:
        lines.append("- 유동성·가격 보정: 임계치를 넘는 조건 없음")

    if missing:
        labels = ", ".join(AXIS_LABELS[key] for key in missing)
        lines.append(f"- 평가 불가 축: {labels} — 해당 축은 해석에서 단정하지 말 것")

    return "\n".join(lines)


def build_sector_detail(sectors: list[dict], count: int = TOP_SECTOR_COUNT) -> str:
    blocks = []
    for rank, sector in enumerate(sectors[:count], start=1):
        parent_line = (
            f"- 계층: {_layer_label(sector)}"
            + (f" (부모: {_parent_label(sector)})" if sector.get("parent") else "")
        )
        blocks.append("\n".join([
            f"[{rank}] {sector['sector']} (ETF: {sector['sector_etf']}) - "
            f"{sector['macro_score']}/30",
            parent_line,
            f"- 유리 요인: {_join(sector['drivers'])}",
            f"- 부담 요인: {_join(sector['headwinds'])}",
            f"- 가장 민감한 축: {sector['watch']}",
            f"- 축별 기여도: {sector['contributions']}",
            f"- 레짐 선호도 보정: {sector['regime_tilt']:+.2f}",
        ]))

    worst = sectors[-1]
    blocks.append("\n".join([
        f"[최하위] {worst['sector']} (ETF: {worst['sector_etf']}) - {worst['macro_score']}/30",
        f"- 부담 요인: {_join(worst['headwinds'])}",
        f"- 축별 기여도: {worst['contributions']}",
    ]))

    return "\n\n".join(blocks)


def build_raw_notes(signals: dict) -> str:
    notes = []
    for key in AXIS_LABELS:
        for note in signals[key].get("notes") or []:
            notes.append(f"- {AXIS_LABELS[key]}: {note}")

    return "\n".join(notes) if notes else "- 특이 신호 없음"
