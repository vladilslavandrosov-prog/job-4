"""FastAPI-приложение: дашборд сравнения цен + ручной запуск сбора с фронта."""

import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ..cli import ADAPTERS, collect
from ..db import get_engine, get_session, init_db
from ..matching import run_matching
from .queries import get_dashboard_rows, get_review_queue_rows, get_sources_summary

TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Parts Price Monitor")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_collect_status: dict[str, str] = {}


def _database_url() -> str | None:
    return os.environ.get("DATABASE_URL")


def _run_collect_and_match(source_key: str) -> None:
    try:
        _collect_status[source_key] = "running"
        collect(source_key, _database_url())
        engine = get_engine(_database_url())
        init_db(engine)
        with get_session(engine) as session:
            run_matching(session)
        _collect_status[source_key] = "done"
    except Exception as exc:  # noqa: BLE001 — статус для фронта, не даём упасть воркеру
        _collect_status[source_key] = f"error: {exc}"


@app.get("/")
def dashboard(request: Request):
    engine = get_engine(_database_url())
    init_db(engine)
    with get_session(engine) as session:
        rows = get_dashboard_rows(session)
        review_rows = get_review_queue_rows(session)
        sources = get_sources_summary(session)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "rows": rows,
            "review_rows": review_rows,
            "sources": sources,
            "adapter_keys": list(ADAPTERS.keys()),
            "collect_status": _collect_status,
        },
    )


@app.post("/api/collect/{source_key}")
def trigger_collect(source_key: str, background_tasks: BackgroundTasks):
    if source_key not in ADAPTERS:
        return {"error": f"неизвестный источник: {source_key}"}
    background_tasks.add_task(_run_collect_and_match, source_key)
    return {"status": "started", "source": source_key}


@app.get("/api/collect/{source_key}/status")
def collect_status(source_key: str):
    return {"source": source_key, "status": _collect_status.get(source_key, "idle")}


@app.post("/collect/{source_key}")
def trigger_collect_form(source_key: str, background_tasks: BackgroundTasks):
    if source_key in ADAPTERS:
        background_tasks.add_task(_run_collect_and_match, source_key)
    return RedirectResponse(url="/", status_code=303)
