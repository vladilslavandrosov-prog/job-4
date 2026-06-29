import os
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    base_url = Column(String, nullable=False)
    status = Column(String, default="active")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    sku = Column(String, nullable=False)
    sku_normalized = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    unverified = Column(Boolean, default=False)

    source = relationship("Source")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    scraped_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")


class MatchGroup(Base):
    __tablename__ = "match_groups"

    id = Column(Integer, primary_key=True)
    canonical_name = Column(String, nullable=False)
    canonical_sku = Column(String, nullable=False, index=True)


class ProductMatch(Base):
    __tablename__ = "product_matches"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    match_group_id = Column(Integer, ForeignKey("match_groups.id"), nullable=False)
    match_method = Column(String, nullable=False)  # "sku_exact" | "fuzzy_name"
    confidence = Column(Float, nullable=False)

    product = relationship("Product")
    match_group = relationship("MatchGroup")


class MatchReviewQueue(Base):
    __tablename__ = "match_review_queue"

    id = Column(Integer, primary_key=True)
    product_a_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_b_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    similarity = Column(Float, nullable=False)
    status = Column(String, default="pending")  # "pending" | "confirmed" | "rejected"

    product_a = relationship("Product", foreign_keys=[product_a_id])
    product_b = relationship("Product", foreign_keys=[product_b_id])


def get_engine(database_url: str | None = None):
    database_url = database_url or os.environ["DATABASE_URL"]
    return create_engine(database_url)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session(engine) -> Session:
    return Session(engine)
