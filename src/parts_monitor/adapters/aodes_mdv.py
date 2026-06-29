"""SiteAdapter for aodes-mdv.ru/zapchasti/.

Структура страницы пока не подтверждена технически (HTML с этого сайта ещё
не предоставлен). Реализация-заглушка: интерфейс совпадает с AodesF7Adapter,
запрос к этому сайту выполняется отдельным HTTP-вызовом, независимо от
aodesf7 — падение/изменение одного сайта не блокирует сбор с другого.
"""

from datetime import datetime, timezone
from typing import Iterator

import requests

from .base import Category, RawItem, SiteAdapter

CATALOG_URL = "https://aodes-mdv.ru/zapchasti/"
SOURCE_NAME = "aodes-mdv"


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
        raise NotImplementedError(
            "Структура aodes-mdv.ru ещё не разведана: нужен пример HTML "
            "страницы каталога, чтобы написать парсер (см. Этап 0 концепции)."
        )
