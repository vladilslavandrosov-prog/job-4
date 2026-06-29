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


def get_engine(database_url: str | None = None):
    database_url = database_url or os.environ["DATABASE_URL"]
    return create_engine(database_url)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session(engine) -> Session:
    return Session(engine)
