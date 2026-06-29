"""SiteAdapter for aodes-mdv.ru/zapchasti/.

Структура страницы (подтверждена на реальном HTML-дампе пользователя):
<table class="partsTable w100"> с <thead> из двух колонок в порядке
Наименование, Артикул (обратный порядок по сравнению с aodesf7.ru!) и
<tbody> строк вида:
<tr><td>{name}</td><td class="tar"><div class="fs12">{sku}</div></td></tr>

ВАЖНО: в этом дампе колонки с ценой нет вообще — в отличие от aodesf7.ru
(там 3 колонки: Артикул | Наименование | Цена). Пока цена на этой странице
не найдена, элементы сохраняются с price=0.0 и unverified=True, чтобы не
терять позиции для матчинга по артикулу, но явно помечать отсутствие
проверенной цены (нельзя сравнивать цены, если цены не было на странице).
"""

import re
from datetime import datetime, timezone
from typing import Iterator

import requests
from bs4 import BeautifulSoup

from .base import Category, RawItem, SiteAdapter

CATALOG_URL = "https://aodes-mdv.ru/zapchasti/"
SOURCE_NAME = "aodes-mdv"

_HEADER_HINTS = ("наименование", "артикул")
_SKU_UNVERIFIED_RE = re.compile(r"\?\s*$")
_PRICE_CLEAN_RE = re.compile(r"[^\d.,]")


def _find_catalog_table(soup: BeautifulSoup):
    table = soup.find("table", class_="partsTable")
    if table is not None:
        return table
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

    body = table.find("tbody") or table
    rows = body.find_all("tr")
    scraped_at = datetime.now(timezone.utc)

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        name_raw = cells[0].get_text(strip=True)
        sku_cell = cells[1]
        sku_div = sku_cell.find("div", class_="fs12")
        sku_raw = (sku_div or sku_cell).get_text(strip=True)

        if not sku_raw or sku_raw.lower() in _HEADER_HINTS:
            continue
        if "наименование" in name_raw.lower() and "артикул" in sku_raw.lower():
            continue

        price = 0.0
        unverified = True
        if len(cells) >= 3:
            price_raw = cells[2].get_text(strip=True)
            try:
                price = clean_price(price_raw)
                unverified = price == 0.0
            except ValueError:
                pass

        unverified = unverified or bool(_SKU_UNVERIFIED_RE.search(sku_raw))
        sku = _SKU_UNVERIFIED_RE.sub("", sku_raw).strip()

        yield RawItem(
            name=name_raw,
            sku=sku,
            price=price,
            currency="RUB",
            source_url=source_url,
            scraped_at=scraped_at,
            unverified=unverified,
        )


class AodesMdvAdapter(SiteAdapter):
    source_name = SOURCE_NAME

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (compatible; PartsPriceMonitor/0.1; +https://github.com/)",
        )

    def fetch_categories(self) -> list[Category]:
        return [Category(name="Запчасти", url=CATALOG_URL)]

    def fetch_items(self, category: Category) -> Iterator[RawItem]:
        response = self.session.get(category.url, timeout=30)
        response.raise_for_status()
        yield from parse_table_html(response.text, source_url=category.url)
