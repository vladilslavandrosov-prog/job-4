from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional


@dataclass
class Category:
    name: str
    url: str


@dataclass
class RawItem:
    name: str
    sku: str
    price: float
    currency: str
    source_url: str
    scraped_at: datetime
    availability: Optional[str] = None
    category_path: Optional[str] = None
    image_url: Optional[str] = None
    unverified: bool = False


class SiteAdapter:
    """Common interface every site-specific adapter must implement."""

    source_name: str

    def fetch_categories(self) -> list[Category]:
        raise NotImplementedError

    def fetch_items(self, category: Category) -> Iterator[RawItem]:
        raise NotImplementedError
