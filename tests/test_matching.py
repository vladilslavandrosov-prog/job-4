from sqlalchemy import create_engine

from parts_monitor.db import PriceHistory, Product, ProductMatch, Source, get_session, init_db
from parts_monitor.matching import run_matching
from parts_monitor.normalizer import normalize_sku


def make_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return get_session(engine)


def add_product(session, source, sku, name, price):
    product = Product(
        source_id=source.id,
        sku=sku,
        sku_normalized=normalize_sku(sku),
        name=name,
        source_url="http://example.test",
    )
    session.add(product)
    session.flush()
    session.add(PriceHistory(product_id=product.id, price=price, currency="RUB"))
    return product


def test_exact_sku_match_across_sources():
    session = make_session()
    source_a = Source(name="aodesf7", base_url="https://aodesf7.ru")
    source_b = Source(name="aodes-mdv", base_url="https://aodes-mdv.ru")
    session.add_all([source_a, source_b])
    session.flush()

    add_product(session, source_a, "001-EL-3700-0830-00", "Реле стартера", 281)
    add_product(session, source_b, "001-EL-3700-0830-00", "Реле стартера AODES", 290)
    session.commit()

    stats = run_matching(session)

    assert stats["sku_exact"] == 2
    matches = session.query(ProductMatch).all()
    assert len(matches) == 2
    assert matches[0].match_group_id == matches[1].match_group_id
    assert all(m.match_method == "sku_exact" for m in matches)


def test_same_source_duplicates_are_not_cross_matched():
    session = make_session()
    source_a = Source(name="aodesf7", base_url="https://aodesf7.ru")
    session.add(source_a)
    session.flush()

    add_product(session, source_a, "13609340000", "Болт М8", 438)
    add_product(session, source_a, "13609340000", "Болт М8 (компл.)", 1047)
    session.commit()

    stats = run_matching(session)

    assert stats["sku_exact"] == 0
    assert session.query(ProductMatch).count() == 0


def test_unmatched_products_are_counted():
    session = make_session()
    source_a = Source(name="aodesf7", base_url="https://aodesf7.ru")
    session.add(source_a)
    session.flush()

    add_product(session, source_a, "0080-0216", "Уникальная деталь", 100)
    session.commit()

    stats = run_matching(session)

    assert stats["unmatched"] == 1
