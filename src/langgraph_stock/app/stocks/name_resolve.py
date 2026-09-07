import logging
from difflib import SequenceMatcher

from app.chains.stock_name_resolve_chain import (
    stock_name_rename_chain,
    stock_name_resolve_chain,
)
from app.repositories.report_repository import fetch_stock_master_listings


logger = logging.getLogger(__name__)

_SIMILAR_AUTO = 0.88
_SIMILAR_MARGIN = 0.12
_CANDIDATE_MIN = 0.5
_CANDIDATE_LIMIT = 40


def _norm(name: str) -> str:
    return str(name or "").replace(" ", "").strip().casefold()


def _similarity(query: str, name: str) -> float:
    q = _norm(query)
    n = _norm(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0

    ratio = SequenceMatcher(None, q, n).ratio()
    if n.startswith(q) and len(n) > len(q):
        ratio -= 0.25
    if q in n and len(q) >= 4:
        ratio = max(ratio, 0.72)
    if n in q and len(n) >= 4:
        ratio = max(ratio, 0.8)
    return ratio


def _unique_by_code(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for row in rows:
        code = row["short_code"]
        if code in seen:
            continue
        seen.add(code)
        unique.append(row)
    return unique


def _exact_matches(query: str, listings: list[dict]) -> list[dict]:
    key = _norm(query)
    return [row for row in listings if _norm(row["stock_name"]) == key]


def _ranked_candidates(query: str, listings: list[dict]) -> list[tuple[float, dict]]:
    ranked = []
    for row in listings:
        score = _similarity(query, row["stock_name"])
        if score >= _CANDIDATE_MIN:
            ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)

    picked = []
    seen: set[str] = set()
    for score, row in ranked:
        if row["short_code"] in seen:
            continue
        seen.add(row["short_code"])
        picked.append((score, row))
        if len(picked) >= _CANDIDATE_LIMIT:
            break
    return picked


def _catalog_text(names: list[str]) -> str:
    unique = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return "\n".join(unique)


def _lookup_official(official_name: str, listings: list[dict]) -> dict | None:
    matches = _unique_by_code(_exact_matches(official_name, listings))
    if len(matches) == 1:
        return matches[0]
    return None


def _resolve_rename(query: str, listings: list[dict]) -> dict | None:
    result = stock_name_rename_chain.invoke({"query_name": query})
    if not result.found:
        logger.info("[name_resolve] 사명 변경 없음 query=%s", query)
        return None

    official = (result.stock_name or "").strip()
    if not official or _norm(official) == _norm(query):
        logger.info(
            "[name_resolve] 사명 확인 결과가 원명과 같음 query=%s official=%s",
            query,
            official,
        )
        return None

    matched = _lookup_official(official, listings)
    if not matched:
        logger.warning(
            "[name_resolve] 변경 사명이 마스터에 없음 query=%s official=%s",
            query,
            official,
        )
        return None

    logger.info(
        "[name_resolve] renamed query=%s → %s %s renamed=%s",
        query,
        matched["short_code"],
        matched["stock_name"],
        result.renamed,
    )
    return {**matched, "match_type": "renamed"}


def _resolve_with_llm(query: str, catalog_names: list[str], listings: list[dict]) -> dict | None:
    catalog = _catalog_text(catalog_names)
    if not catalog:
        return None

    result = stock_name_resolve_chain.invoke({
        "query_name": query,
        "catalog": catalog,
    })
    if not result.found:
        logger.warning("[name_resolve] LLM 매칭 실패 query=%s", query)
        return None

    official = (result.stock_name or "").strip()
    matched = _lookup_official(official, listings)
    if not matched:
        logger.warning(
            "[name_resolve] LLM이 목록에 없는 이름 반환 query=%s official=%s",
            query,
            official,
        )
        return None
    return matched


def resolve_stock_by_name(stock_name: str) -> dict | None:
    query = str(stock_name or "").strip()
    if not query:
        return None

    listings = fetch_stock_master_listings()
    if not listings:
        logger.warning("[name_resolve] STOCK_MASTER 가 비어 있습니다")
        return None

    exact = _unique_by_code(_exact_matches(query, listings))
    if len(exact) == 1:
        match = exact[0]
        logger.info(
            "[name_resolve] exact query=%s → %s %s",
            query,
            match["short_code"],
            match["stock_name"],
        )
        return {**match, "match_type": "exact"}
    if len(exact) > 1:
        logger.warning(
            "[name_resolve] 동명 종목 query=%s codes=%s",
            query,
            [row["short_code"] for row in exact],
        )
        return None

    ranked = _ranked_candidates(query, listings)
    if ranked:
        best_score, best = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score >= _SIMILAR_AUTO and (best_score - second_score) >= _SIMILAR_MARGIN:
            logger.info(
                "[name_resolve] similar query=%s → %s %s score=%.3f",
                query,
                best["short_code"],
                best["stock_name"],
                best_score,
            )
            return {**best, "match_type": "similar"}

    renamed = _resolve_rename(query, listings)
    if renamed:
        return renamed

    if ranked:
        catalog_names = [row["stock_name"] for _, row in ranked]
        logger.info(
            "[name_resolve] LLM 후보 %s개 query=%s top=%s",
            len(catalog_names),
            query,
            catalog_names[:8],
        )
    else:
        catalog_names = [row["stock_name"] for row in listings]
        logger.info("[name_resolve] 유사 후보 없음, 전체 목록으로 매칭 query=%s", query)

    matched = _resolve_with_llm(query, catalog_names, listings)
    if not matched:
        return None

    logger.info(
        "[name_resolve] resolved query=%s → %s %s",
        query,
        matched["short_code"],
        matched["stock_name"],
    )
    return {**matched, "match_type": "resolved"}
