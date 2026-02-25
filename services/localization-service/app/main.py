import json
import os
from pathlib import Path as FilePath

from fastapi import FastAPI, HTTPException, Path, status
from typing import Dict

app = FastAPI(
    title="Localization Service",
    description="Provides translation strings for different locales.",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --- Persistent Translations Catalog ---
TRANSLATIONS_PATH = FilePath(
    os.getenv("LOCALIZATION_CATALOG_PATH", str(FilePath(__file__).with_name("translations.json")))
)


def load_translations_catalog() -> Dict[str, Dict[str, Dict[str, str]]]:
    with TRANSLATIONS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


translations_catalog = load_translations_catalog()

# --- Endpoints ---

@app.get(
    "/translations/{locale}/all",
    response_model=Dict[str, Dict[str, str]],
    summary="Get all translations for a locale"
)
async def get_all_translations_for_locale(locale: str = Path(..., example="en-GB")):
    """
    Retrieves all translation namespaces for a given locale.
    This is useful for loading all strings for a single-page application.
    """
    if locale_data := translations_catalog.get(locale):
        return locale_data

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Translations for locale '{locale}' not found."
    )

@app.get(
    "/translations/{locale}/{component}",
    response_model=Dict[str, str],
    summary="Get translations for a component",
    deprecated=True
)
async def get_translations_by_component(
    locale: str = Path(..., example="en-GB"),
    component: str = Path(..., example="login")
):
    """
    Retrieves a key-value map for a given locale and component.
    """
    if locale_data := translations_catalog.get(locale):
        if component_data := locale_data.get(component):
            return component_data

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Translations for locale '{locale}' and component '{component}' not found."
    )
