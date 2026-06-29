"""Matching Engine: объединяет товары разных источников в match_group.

Стратегия (см. docs/parts-price-monitor-concept.md, 3.4):
1. Точное совпадение по нормализованному артикулу — основной путь.
2. Fallback на fuzzy-сравнение названий, если артикул не совпал/отсутствует.
   Высокая similarity (>= AUTO_MATCH_THRESHOLD) — автоматический матч.
   Средняя (>= REVIEW_THRESHOLD) — уходит в очередь ручной проверки, не
   считается совпадением автоматически: ложный матч дороже отсутствия матча.
"""

from collections import defaultdict

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from .db import MatchGroup, MatchReviewQueue, Product, ProductMatch
from .normalizer import normalize_name

AUTO_MATCH_THRESHOLD = 95.0
REVIEW_THRESHOLD = 75.0


def _get_or_create_group(session: Session, product: Product) -> MatchGroup:
    existing = (
        session.query(ProductMatch).filter_by(product_id=product.id).first()
    )
    if existing is not None:
        return existing.match_group

    group = MatchGroup(canonical_name=product.name, canonical_sku=product.sku_normalized)
    session.add(group)
    session.flush()
    return group


def _link(session: Session, product: Product, group: MatchGroup, method: str, confidence: float) -> None:
    existing = session.query(ProductMatch).filter_by(product_id=product.id).first()
    if existing is not None:
        return
    session.add(
        ProductMatch(
            product_id=product.id,
            match_group_id=group.id,
            match_method=method,
            confidence=confidence,
        )
    )


def run_matching(session: Session) -> dict[str, int]:
    """Прогоняет matching по всем продуктам в БД. Возвращает статистику."""
    products = session.query(Product).all()
    stats = {"sku_exact": 0, "fuzzy_auto": 0, "review_queue": 0, "unmatched": 0}

    by_sku: dict[str, list[Product]] = defaultdict(list)
    for product in products:
        if product.sku_normalized:
            by_sku[product.sku_normalized].append(product)

    matched_ids: set[int] = set()

    for sku, group_products in by_sku.items():
        distinct_sources = {p.source_id for p in group_products}
        if len(group_products) < 2 or len(distinct_sources) < 2:
            continue  # совпадение нужно только между разными источниками
        group = _get_or_create_group(session, group_products[0])
        for product in group_products:
            _link(session, product, group, method="sku_exact", confidence=1.0)
            matched_ids.add(product.id)
            stats["sku_exact"] += 1

    unmatched = [p for p in products if p.id not in matched_ids]
    queued_pairs: set[tuple[int, int]] = set()

    for i, product_a in enumerate(unmatched):
        if product_a.id in matched_ids:
            continue
        name_a = normalize_name(product_a.name)

        for product_b in unmatched[i + 1 :]:
            if product_b.id in matched_ids:
                continue
            if product_a.source_id == product_b.source_id:
                continue  # matching нужен только между разными источниками

            similarity = fuzz.token_sort_ratio(name_a, normalize_name(product_b.name))

            if similarity >= AUTO_MATCH_THRESHOLD:
                group = _get_or_create_group(session, product_a)
                _link(session, product_a, group, method="fuzzy_name", confidence=similarity / 100)
                _link(session, product_b, group, method="fuzzy_name", confidence=similarity / 100)
                matched_ids.add(product_a.id)
                matched_ids.add(product_b.id)
                stats["fuzzy_auto"] += 2
                break

            if similarity >= REVIEW_THRESHOLD:
                pair = tuple(sorted((product_a.id, product_b.id)))
                if pair not in queued_pairs:
                    queued_pairs.add(pair)
                    session.add(
                        MatchReviewQueue(
                            product_a_id=pair[0],
                            product_b_id=pair[1],
                            similarity=similarity / 100,
                        )
                    )
                    stats["review_queue"] += 1

    stats["unmatched"] = len(products) - len(matched_ids)
    session.commit()
    return stats
