"""SiteAdapter for aodesf7.ru/zapchasti/.

Структура страницы (подтверждена на реальном HTML-дампе пользователя):
один статический <table> внутри WPBakery-блока wpb_raw_html, три колонки:
Артикул | Наименование | Рекомендованная розничная цена, руб.
Без пагинации и AJAX — достаточно одного HTTP GET + BeautifulSoup.
"""

import re
from datetime import datetime, timezone
from typing import Iterator

import requests
from bs4 import BeautifulSoup

from .base import Category, RawItem, SiteAdapter

CATALOG_URL = "https://aodesf7.ru/zapchasti/"
SOURCE_NAME = "aodesf7"

_HEADER_HINTS = ("артикул", "наименование")
_SKU_UNVERIFIED_RE = re.compile(r"\?\s*$")
_PRICE_CLEAN_RE = re.compile(r"[^\d.,]")


def _find_catalog_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        header_text = table.get_text(" ", strip=True).lower()
        if all(hint in header_text for hint in _HEADER_HINTS):
            return table
    return None


def clean_price(raw_price: str) -> float:
    cleaned = _PRICE_CLEAN_RE.sub("", raw_price).replace(",", ".")
    if not cleaned:
        return 0.0
    return float(cleaned)


def parse_table_html(html: str, source_url: str = CATALOG_URL) -> Iterator[RawItem]:
    soup = BeautifulSoup(html, "lxml")
    table = _find_catalog_table(soup)
    if table is None:
        return

    rows = table.find_all("tr")
    scraped_at = datetime.now(timezone.utc)

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        sku_raw = cells[0].get_text(strip=True)
        name_raw = cells[1].get_text(strip=True)
        price_raw = cells[2].get_text(strip=True)

        if not sku_raw or sku_raw.lower() in _HEADER_HINTS:
            continue
        if "артикул" in sku_raw.lower() and "наименование" in name_raw.lower():
            continue

        unverified = bool(_SKU_UNVERIFIED_RE.search(sku_raw))
        sku = _SKU_UNVERIFIED_RE.sub("", sku_raw).strip()

        try:
            price = clean_price(price_raw)
        except ValueError:
            continue

        yield RawItem(
            name=name_raw,
            sku=sku,
            price=price,
            currency="RUB",
            source_url=source_url,
            scraped_at=scraped_at,
            unverified=unverified,
        )


class AodesF7Adapter(SiteAdapter):
    source_name = SOURCE_NAME

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (compatible; PartsPriceMonitor/0.1; +https://github.com/)",
        )

    def fetch_categories(self) -> list[Category]:
        # На этой странице нет отдельных категорий — один сводный каталог.
        return [Category(name="Запчасти", url=CATALOG_URL)]

    def fetch_items(self, category: Category) -> Iterator[RawItem]:
        response = self.session.get(category.url, timeout=30)
        response.raise_for_status()
        yield from parse_table_html(response.text, source_url=category.url)
