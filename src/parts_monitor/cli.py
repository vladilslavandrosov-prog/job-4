"""CLI: `python -m parts_monitor.cli collect` — собрать каталог и сохранить в БД."""

import argparse
import os
import time

from .adapters.aodes_mdv import AodesMdvAdapter
from .adapters.aodesf7 import AodesF7Adapter
from .db import PriceHistory, Product, Source, get_engine, get_session, init_db
from .normalizer import normalize_name, normalize_sku

ADAPTERS = {
    "aodesf7": AodesF7Adapter,
    "aodes-mdv": AodesMdvAdapter,
}


def collect(source_key: str, database_url: str | None = None) -> int:
    adapter_cls = ADAPTERS[source_key]
    adapter = adapter_cls()

    engine = get_engine(database_url)
    init_db(engine)

    saved = 0
    with get_session(engine) as session:
        source = session.query(Source).filter_by(name=adapter.source_name).first()
        if source is None:
            source = Source(name=adapter.source_name, base_url=adapter.fetch_categories()[0].url)
            session.add(source)
            session.flush()

        for category in adapter.fetch_categories():
            for item in adapter.fetch_items(category):
                product = (
                    session.query(Product)
                    .filter_by(source_id=source.id, sku=item.sku)
                    .first()
                )
                if product is None:
                    product = Product(
                        source_id=source.id,
                        sku=item.sku,
                        sku_normalized=normalize_sku(item.sku),
                        name=item.name,
                        source_url=item.source_url,
                        unverified=item.unverified,
                    )
                    session.add(product)
                    session.flush()
                else:
                    product.name = normalize_name(item.name) and item.name

                session.add(
                    PriceHistory(
                        product_id=product.id,
                        price=item.price,
                        currency=item.currency,
                        scraped_at=item.scraped_at,
                    )
                )
                saved += 1

        session.commit()

    return saved


def run_menu(database_url: str | None = None) -> None:
    """Интерактивное меню: каждый сайт — отдельная строка, запрос делается
    только к выбранному источнику (без батчинга по нескольким сайтам сразу)."""
    sources = list(ADAPTERS.keys())

    while True:
        print("\nВыберите источник для сбора данных:")
        for i, key in enumerate(sources, start=1):
            print(f"  {i}. {key}")
        print(f"  {len(sources) + 1}. Собрать все источники по очереди")
        print("  0. Выход")

        choice = input("> ").strip()
        if choice == "0":
            return

        try:
            choice_idx = int(choice)
        except ValueError:
            print("Некорректный ввод")
            continue

        if 1 <= choice_idx <= len(sources):
            selected = [sources[choice_idx - 1]]
        elif choice_idx == len(sources) + 1:
            selected = sources
        else:
            print("Некорректный ввод")
            continue

        for source_key in selected:
            print(f"\n[{source_key}] запрос отправляется отдельно...")
            try:
                saved = collect(source_key, database_url)
                print(f"[{source_key}] сохранено снимков цен: {saved}")
            except NotImplementedError as exc:
                print(f"[{source_key}] пропущено: {exc}")


def run_forever(source_key: str, database_url: str | None, interval_seconds: int) -> None:
    """Долгоживущий процесс: сбор по расписанию, без выхода.

    Нужен для хостингов (Amvera и т.п.), которые держат сервис как
    постоянно работающий и перезапускают контейнер по back-off, если
    процесс завершается (даже успешно)."""
    while True:
        try:
            saved = collect(source_key, database_url)
            print(f"[{source_key}] сохранено снимков цен: {saved}", flush=True)
        except Exception as exc:  # noqa: BLE001 — не даём процессу упасть между циклами
            print(f"[{source_key}] ошибка сбора: {exc}", flush=True)

        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parts price monitor CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    collect_parser = sub.add_parser("collect", help="Собрать каталог одного источника и сохранить в БД (один раз)")
    collect_parser.add_argument("--source", default="aodesf7", choices=ADAPTERS.keys())
    collect_parser.add_argument("--database-url", default=None)

    menu_parser = sub.add_parser("menu", help="Интерактивное меню: выбор источника отдельной строкой")
    menu_parser.add_argument("--database-url", default=None)

    serve_parser = sub.add_parser("serve", help="Долгоживущий процесс: сбор по расписанию, не завершается")
    serve_parser.add_argument("--source", default="aodesf7", choices=ADAPTERS.keys())
    serve_parser.add_argument("--database-url", default=None)
    serve_parser.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.environ.get("COLLECT_INTERVAL_SECONDS", "3600")),
    )

    args = parser.parse_args()

    if args.command == "collect":
        saved = collect(args.source, args.database_url)
        print(f"Сохранено снимков цен: {saved}")
    elif args.command == "menu":
        run_menu(args.database_url)
    elif args.command == "serve":
        run_forever(args.source, args.database_url, args.interval_seconds)


if __name__ == "__main__":
    main()
