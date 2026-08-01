from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Callable

from fastapi import Request

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
SUPPORTED_LOCALES = {"en", "zh_TW"}
DEFAULT_LOCALE = "en"

@lru_cache(maxsize=None)
def load_catalog(locale: str) -> dict[str, str]:
    safe = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    path = LOCALES_DIR / f"{safe}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

def normalize_locale(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE
    normalized = value.replace("-", "_").lower()
    if normalized in {"zh_tw", "zh_hant", "zh_hant_tw"} or normalized.startswith("zh_hant"):
        return "zh_TW"
    return "en"

def locale_for_request(request: Request) -> str:
    selected = request.session.get("locale")
    if selected in SUPPORTED_LOCALES:
        return selected
    return normalize_locale(request.headers.get("accept-language", "").split(",", 1)[0])

def translator(locale: str) -> Callable[..., str]:
    catalog = load_catalog(locale)
    fallback = load_catalog(DEFAULT_LOCALE)
    def translate(key: str, **values: object) -> str:
        text = catalog.get(key, fallback.get(key, key))
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text
    return translate
