"""Запросы для дашборда: сравнение цен по match_group между источниками."""

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import MatchGroup, PriceHistory, Product, ProductMatch, Source


@dataclass
class SourcePrice:
    source_name: str
    price: float
    unverified: bool
    source_url: str


@dataclass
class GroupRow:
    match_group_id: int
    canonical_name: str
    canonical_sku: str
    prices: list[SourcePrice]
    min_price: float | None
    max_price: float | None
    price_diff: float | None


def _latest_prices_by_product(session: Session, product_ids: list[int]) -> dict[int, PriceHistory]:
    """Последняя цена на товар, без N+1: один запрос на все товары сразу."""
    if not product_ids:
        return {}

    history = (
        session.query(PriceHistory)
        .filter(PriceHistory.product_id.in_(product_ids))
        .order_by(PriceHistory.product_id, PriceHistory.scraped_at.desc())
        .all()
    )
    latest: dict[int, PriceHistory] = {}
    for entry in history:
        if entry.product_id not in latest:
            latest[entry.product_id] = entry
    return latest


def get_dashboard_rows(session: Session) -> list[GroupRow]:
    groups = {g.id: g for g in session.query(MatchGroup).all()}
    if not groups:
        return []

    matches = session.query(ProductMatch).filter(ProductMatch.match_group_id.in_(groups.keys())).all()
    products = {
        p.id: p
        for p in session.query(Product).filter(Product.id.in_([m.product_id for m in matches])).all()
    }
    sources = {s.id: s for s in session.query(Source).all()}
    latest_by_product = _latest_prices_by_product(session, list(products.keys()))

    matches_by_group: dict[int, list[ProductMatch]] = {}
    for m in matches:
        matches_by_group.setdefault(m.match_group_id, []).append(m)

    rows: list[GroupRow] = []

    for group_id, group in groups.items():
        prices: list[SourcePrice] = []

        for pm in matches_by_group.get(group_id, []):
            product = products.get(pm.product_id)
            if product is None:
                continue
            source = sources.get(product.source_id)
            latest = latest_by_product.get(product.id)
            if latest is None:
                continue
            prices.append(
                SourcePrice(
                    source_name=source.name if source else "?",
                    price=latest.price,
                    unverified=product.unverified or latest.price == 0.0,
                    source_url=product.source_url,
                )
            )

        if not prices:
            continue

        verified_prices = [p.price for p in prices if not p.unverified]
        min_price = min(verified_prices) if verified_prices else None
        max_price = max(verified_prices) if verified_prices else None
        price_diff = (max_price - min_price) if (min_price is not None and max_price is not None) else None

        rows.append(
            GroupRow(
                match_group_id=group.id,
                canonical_name=group.canonical_name,
                canonical_sku=group.canonical_sku,
                prices=prices,
                min_price=min_price,
                max_price=max_price,
                price_diff=price_diff,
            )
        )

    rows.sort(key=lambda r: (r.price_diff is None, -(r.price_diff or 0)))
    return rows


def get_review_queue_rows(session: Session):
    from ..db import MatchReviewQueue

    queue = (
        session.query(MatchReviewQueue)
        .filter_by(status="pending")
        .order_by(MatchReviewQueue.similarity.desc())
        .all()
    )
    return queue


@dataclass
class PriceSnapshot:
    price: float
    scraped_at: object


@dataclass
class ProductHistoryRow:
    product_id: int
    name: str
    sku: str
    unverified: bool
    source_url: str
    snapshots: list[PriceSnapshot]
    last_change: float | None
    last_change_pct: float | None


def get_source_price_history(session: Session, source_name: str) -> list[ProductHistoryRow]:
    source = session.query(Source).filter_by(name=source_name).first()
    if source is None:
        return []

    products = session.query(Product).filter_by(source_id=source.id).all()
    if not products:
        return []

    product_ids = [p.id for p in products]
    history = (
        session.query(PriceHistory)
        .filter(PriceHistory.product_id.in_(product_ids))
        .order_by(PriceHistory.product_id, PriceHistory.scraped_at.asc())
        .all()
    )
    history_by_product: dict[int, list[PriceHistory]] = {}
    for entry in history:
        history_by_product.setdefault(entry.product_id, []).append(entry)

    rows: list[ProductHistoryRow] = []

    for product in products:
        product_history = history_by_product.get(product.id)
        if not product_history:
            continue

        snapshots = [PriceSnapshot(price=h.price, scraped_at=h.scraped_at) for h in product_history]

        last_change = None
        last_change_pct = None
        if len(snapshots) >= 2:
            prev_price = snapshots[-2].price
            curr_price = snapshots[-1].price
            last_change = curr_price - prev_price
            if prev_price:
                last_change_pct = (last_change / prev_price) * 100

        rows.append(
            ProductHistoryRow(
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                unverified=product.unverified,
                source_url=product.source_url,
                snapshots=snapshots,
                last_change=last_change,
                last_change_pct=last_change_pct,
            )
        )

    rows.sort(key=lambda r: (r.last_change is None, -(abs(r.last_change) if r.last_change else 0)))
    return rows


def get_sources_summary(session: Session) -> list[dict]:
    summary = (
        session.query(Source.name, func.count(Product.id))
        .outerjoin(Product, Product.source_id == Source.id)
        .group_by(Source.name)
        .all()
    )
    return [{"name": name, "product_count": count} for name, count in summary]
