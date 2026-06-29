"""Приведение RawItem к единой схеме Product перед записью в БД."""

import re

_NON_ALNUM_RE = re.compile(r"[\s\-_]+")


def normalize_sku(sku: str) -> str:
    """Убирает пробелы/дефисы/регистр и ведущие нули для сравнения артикулов."""
    cleaned = _NON_ALNUM_RE.sub("", sku).upper()
    stripped = cleaned.lstrip("0")
    return stripped or cleaned


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()
