# Деплой на Amvera + PostgreSQL

## 1. База данных

В панели Amvera создать отдельный сервис **PostgreSQL** (Marketplace →
PostgreSQL). После создания Amvera выдаёт переменные подключения
(host, port, user, password, db name) — собрать из них `DATABASE_URL`:

```
postgresql://USER:PASSWORD@HOST:PORT/DBNAME
```

## 2. Приложение

Репозиторий уже содержит `Dockerfile` и `amvera.yml` — Amvera собирает
образ по Dockerfile и запускает команду из `run.command`.

В настройках приложения на Amvera задать переменную окружения:

- `DATABASE_URL` — строка подключения к Postgres-сервису из шага 1.

## 3. Запуск сбора по источникам

Каждый сайт собирается отдельным независимым запросом (см.
`src/parts_monitor/cli.py`, команда `menu` — отдельная строка меню на
каждый сайт, `collect --source <name>` — точечный запуск одного источника):

```
python -m parts_monitor.cli collect --source aodesf7
python -m parts_monitor.cli collect --source aodes-mdv   # после разведки структуры сайта
```

На Amvera это можно запускать как cron-задачу (Amvera Cron Jobs) с
отдельным расписанием на каждый источник — соответствует Этапу 3
концепции (`docs/parts-price-monitor-concept.md`), где сбор по каждому
сайту не должен блокироваться падением другого.

## 4. Локальная проверка перед деплоем

```
docker build -t parts-monitor .
docker run --rm -e DATABASE_URL=postgresql://... parts-monitor
```
