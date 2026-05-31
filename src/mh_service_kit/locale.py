from __future__ import annotations


def parse_locale(accept_language: str | None = None) -> str:
    if accept_language:
        lang = accept_language.split(",")[0].split(";")[0].strip().lower()
        if lang in ("zh", "en"):
            return lang
    return "zh"


def resolve_locale(
    value: str,
    value_locale: dict[str, str] | None,
    locale: str,
) -> str:
    if locale and value_locale and locale in value_locale:
        return value_locale[locale]
    return value
