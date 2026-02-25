from copy import deepcopy
import datetime
import json
import os
from pathlib import Path as FsPath
from typing import Dict, Literal, Optional

from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel

app = FastAPI(
    title="Localization Service",
    description="Provides translation strings for different locales.",
    version="1.0.0"
)

# --- "Database" for translations ---
# In a real app, this would come from a TMS (Translation Management System)
# like Lokalise or Crowdin, and be cached.
fake_translations_db = {
    "en-GB": {
        "common": {
            "submit": "Submit",
            "cancel": "Cancel",
            "logout": "Logout",
            "save": "Save",
            "loading": "Loading..."
        },
        "login": {
            "title": "Self Assessment Assistant",
            "description": "Register or log in to continue",
            "register_button": "Register",
            "login_button": "Login",
            "email_placeholder": "Email",
            "password_placeholder": "Password",
            "register_success": "Registration successful. You can now log in."
        },
        "nav": {
            "dashboard": "Dashboard",
            "activity": "Activity",
            "transactions": "Transactions",
            "documents": "Documents",
            "reports": "Reports",
            "marketplace": "Marketplace",
            "submission": "Tax Submission",
            "profile": "Profile",
            "admin": "Admin"
        },
        "dashboard": {
            "title": "Main Dashboard",
            "description": "Welcome to your Self-Assessment workspace.",
            "tax_estimator_title": "Tax Estimator (UK)",
            "tax_estimator_button": "Calculate Tax",
            "tax_estimator_result_title": "Estimated Tax for",
            "total_income_label": "Total Income",
            "allowable_expenses_label": "Allowable Expenses",
            "disallowable_expenses_label": "Disallowable Expenses",
            "taxable_profit_label": "Taxable Profit",
            "income_tax_due_label": "Income Tax",
            "class2_nic_label": "Class 2 NIC",
            "class4_nic_label": "Class 4 NIC",
            "estimated_tax_due_label": "Estimated Tax Due",
            "cashflow_title": "Cash Flow Forecast (Next 30 Days)",
            "cashflow_loading": "Generating forecast...",
            "readiness_title": "Tax Readiness Score",
            "readiness_description": "Shows how prepared your data is for Self-Assessment.",
            "readiness_score_label": "Readiness score",
            "readiness_missing_categories": "Uncategorised transactions:",
            "readiness_missing_business_use": "Missing business-use % on expenses:",
            "readiness_actions_title": "Next best actions",
            "readiness_action_categories": "Categorise remaining transactions.",
            "readiness_action_business_use": "Add business-use % for mixed expenses.",
            "readiness_no_transactions": "No transactions imported yet.",
            "readiness_low": "Low readiness",
            "readiness_medium": "Medium readiness",
            "readiness_high": "High readiness",
            "readiness_loading": "Calculating readiness...",
            "action_next_title": "What's next?",
            "action_next_description": "Explore our marketplace of trusted partners for insurance, accounting, and more.",
            "action_next_button": "Explore Partner Services"
        },
        "activity": {
            "description": "Here is a record of recent events in your account.",
            "col_date": "Date",
            "col_action": "Action",
            "col_details": "Details"
        },
        "transactions": {
            "title": "Transactions",
            "description": "Connect your bank account to import and categorize your transactions.",
            "bank_connections_title": "Bank Connections",
            "connect_button": "Connect a Bank Account",
            "consent_prompt": "Click the link to grant access at your bank:",
            "loading": "Loading transactions...",
            "recent_title": "Recent Transactions",
            "col_date": "Date",
            "col_description": "Description",
            "col_amount": "Amount",
            "col_category": "Category",
            "select_placeholder": "Select...",
            "csv_title": "CSV Import",
            "csv_description": "Upload a CSV file if your bank is not supported.",
            "csv_account_label": "Account ID",
            "csv_account_placeholder": "Paste account UUID",
            "csv_upload_button": "Upload CSV",
            "csv_uploading": "Uploading...",
            "csv_success": "CSV import accepted. Imported:",
            "csv_skipped_label": "Skipped:",
            "csv_select_error": "Please select a CSV file.",
            "csv_account_error": "Account ID is required."
        },
        "documents": {
            "description": "Upload and manage your receipts and invoices.",
            "upload_title": "Upload a Document",
            "upload_button": "Upload",
            "uploading_button": "Uploading...",
            "col_filename": "Filename",
            "col_status": "Status",
            "col_vendor": "Vendor",
            "col_amount": "Amount",
            "col_category": "Category",
            "col_expense_article": "Expense Article",
            "col_deductible": "Deductible",
            "col_receipt_draft": "Draft Transaction",
            "col_uploaded_at": "Uploaded At",
            "search_title": "Semantic Document Search",
            "search_description": "Ask a question about your documents in natural language.",
            "search_placeholder": "e.g., 'where did I buy coffee last month?'",
            "search_button": "Search",
            "all_documents_title": "All Uploaded Documents",
            "uploaded_documents_count": "{count, plural, =0 {No uploaded documents yet.} one {# uploaded document} other {# uploaded documents}}",
            "review_queue_count": "{count, plural, =0 {No documents currently require manual OCR review.} one {# document requires manual OCR review.} other {# documents require manual OCR review.}}"
        }
    },
    "de-DE": {
        "common": {
            "submit": "Einreichen",
            "cancel": "Abbrechen",
            "logout": "Ausloggen",
            "save": "Speichern",
            "loading": "Wird geladen..."
        },
        "login": {
            "title": "Self-Assessment Assistent",
            "description": "Registrieren Sie sich oder melden Sie sich an, um fortzufahren",
            "register_button": "Registrieren",
            "login_button": "Anmelden",
            "email_placeholder": "E-Mail",
            "password_placeholder": "Passwort",
            "register_success": "Registrierung erfolgreich. Sie können sich jetzt anmelden."
        },
        "nav": {
            "dashboard": "Dashboard",
            "activity": "Aktivitätsprotokoll",
            "transactions": "Transaktionen",
            "documents": "Dokumente",
            "reports": "Berichte",
            "marketplace": "Marktplatz",
            "submission": "HMRC-Übermittlung",
            "profile": "Profil",
            "admin": "Admin"
        },
        "dashboard": {
            "title": "Haupt-Dashboard",
            "description": "Willkommen in Ihrem Self-Assessment-Arbeitsbereich.",
            "tax_estimator_title": "Steuerschätzer (UK)",
            "tax_estimator_button": "Steuer berechnen",
            "tax_estimator_result_title": "Geschätzte Steuer für",
            "total_income_label": "Gesamteinnahmen",
            "allowable_expenses_label": "Abzugsfähige Ausgaben",
            "disallowable_expenses_label": "Nicht abzugsfähige Ausgaben",
            "taxable_profit_label": "Steuerpflichtiger Gewinn",
            "income_tax_due_label": "Einkommensteuer",
            "class2_nic_label": "Class 2 NIC",
            "class4_nic_label": "Class 4 NIC",
            "estimated_tax_due_label": "Voraussichtliche Steuer",
            "cashflow_title": "Cashflow-Prognose (nächste 30 Tage)",
            "cashflow_loading": "Prognose wird erstellt...",
            "readiness_title": "Steuerbereitschaft",
            "readiness_description": "Zeigt, wie gut Ihre Daten für Self-Assessment vorbereitet sind.",
            "readiness_score_label": "Bereitschaftswert",
            "readiness_missing_categories": "Nicht kategorisierte Transaktionen:",
            "readiness_missing_business_use": "Fehlender Geschäftsanteil bei Ausgaben:",
            "readiness_actions_title": "Nächste Schritte",
            "readiness_action_categories": "Restliche Transaktionen kategorisieren.",
            "readiness_action_business_use": "Geschäftsanteil für gemischte Ausgaben ergänzen.",
            "readiness_no_transactions": "Noch keine Transaktionen importiert.",
            "readiness_low": "Niedrige Bereitschaft",
            "readiness_medium": "Mittlere Bereitschaft",
            "readiness_high": "Hohe Bereitschaft",
            "readiness_loading": "Bereitschaft wird berechnet...",
            "action_next_title": "Was kommt als Nächstes?",
            "action_next_description": "Entdecken Sie unseren Marktplatz mit vertrauenswürdigen Partnern für Versicherungen, Buchhaltung und mehr.",
            "action_next_button": "Partnerdienste entdecken"
        },
        "activity": {
            "description": "Hier ist eine Aufzeichnung der letzten wichtigen Ereignisse in Ihrem Konto.",
            "col_date": "Datum",
            "col_action": "Aktion",
            "col_details": "Details"
        },
        "transactions": {
            "title": "Transaktionen",
            "description": "Verbinden Sie Ihr Bankkonto, um Transaktionen zu importieren und zu kategorisieren.",
            "bank_connections_title": "Bankverbindungen",
            "connect_button": "Bankkonto verbinden",
            "consent_prompt": "Klicken Sie auf den Link, um Zugriff bei Ihrer Bank zu gewähren:",
            "loading": "Transaktionen werden geladen...",
            "recent_title": "Letzte Transaktionen",
            "col_date": "Datum",
            "col_description": "Beschreibung",
            "col_amount": "Betrag",
            "col_category": "Kategorie",
            "select_placeholder": "Auswählen...",
            "csv_title": "CSV-Import",
            "csv_description": "Laden Sie eine CSV-Datei hoch, wenn Ihre Bank nicht unterstützt wird.",
            "csv_account_label": "Konto-ID",
            "csv_account_placeholder": "Konto-UUID einfügen",
            "csv_upload_button": "CSV hochladen",
            "csv_uploading": "Wird hochgeladen...",
            "csv_success": "CSV-Import akzeptiert. Importiert:",
            "csv_skipped_label": "Übersprungen:",
            "csv_select_error": "Bitte wählen Sie eine CSV-Datei aus.",
            "csv_account_error": "Konto-ID ist erforderlich."
        },
        "documents": {
            "description": "Laden Sie Ihre Belege und Rechnungen hoch und verwalten Sie sie.",
            "upload_title": "Dokument hochladen",
            "upload_button": "Hochladen",
            "uploading_button": "Lädt hoch...",
            "col_filename": "Dateiname",
            "col_status": "Status",
            "col_vendor": "Anbieter",
            "col_amount": "Betrag",
            "col_category": "Kategorie",
            "col_expense_article": "Kostenart",
            "col_deductible": "Absetzbar",
            "col_receipt_draft": "Entwurfstransaktion",
            "col_uploaded_at": "Hochgeladen am",
            "search_title": "Semantische Dokumentsuche",
            "search_description": "Stellen Sie eine Frage zu Ihren Dokumenten in natürlicher Sprache.",
            "search_placeholder": "z.B. 'wo habe ich letzten monat kaffee gekauft?'",
            "search_button": "Suchen",
            "all_documents_title": "Alle hochgeladenen Dokumente",
            "uploaded_documents_count": "{count, plural, =0 {Noch keine hochgeladenen Dokumente.} one {# hochgeladenes Dokument} other {# hochgeladene Dokumente}}",
            "review_queue_count": "{count, plural, =0 {Aktuell sind keine Dokumente zur manuellen OCR-Prüfung offen.} one {# Dokument benötigt eine manuelle OCR-Prüfung.} other {# Dokumente benötigen eine manuelle OCR-Prüfung.}}"
        }
    }
}

DEFAULT_LOCALE = "en-GB"
SUPPORTED_LOCALE_METADATA: dict[str, dict[str, Optional[str]]] = {
    "en-GB": {"native_name": "English (UK)", "fallback_locale": None, "status": "translated"},
    "de-DE": {"native_name": "Deutsch (Deutschland)", "fallback_locale": DEFAULT_LOCALE, "status": "translated"},
    "ru-RU": {"native_name": "Русский", "fallback_locale": DEFAULT_LOCALE, "status": "fallback_en_gb"},
    "uk-UA": {"native_name": "Українська", "fallback_locale": DEFAULT_LOCALE, "status": "fallback_en_gb"},
    "pl-PL": {"native_name": "Polski", "fallback_locale": DEFAULT_LOCALE, "status": "fallback_en_gb"},
    "ro-MD": {"native_name": "Română (Moldova)", "fallback_locale": DEFAULT_LOCALE, "status": "fallback_en_gb"},
    "tr-TR": {"native_name": "Türkçe", "fallback_locale": DEFAULT_LOCALE, "status": "fallback_en_gb"},
    "hu-HU": {"native_name": "Magyar", "fallback_locale": DEFAULT_LOCALE, "status": "fallback_en_gb"},
}

LOCALE_FORMAT_STANDARDS: dict[str, dict[str, object]] = {
    "en-GB": {
        "default_currency": "GBP",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/London",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
    "de-DE": {
        "default_currency": "EUR",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/Berlin",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
    "ru-RU": {
        "default_currency": "GBP",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/London",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
    "uk-UA": {
        "default_currency": "GBP",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/London",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
    "pl-PL": {
        "default_currency": "GBP",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/Warsaw",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
    "ro-MD": {
        "default_currency": "GBP",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/Chisinau",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
    "tr-TR": {
        "default_currency": "GBP",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/Istanbul",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
    "hu-HU": {
        "default_currency": "GBP",
        "date_style": "medium",
        "time_style": "short",
        "time_zone": "Europe/Budapest",
        "number_min_fraction_digits": 0,
        "number_max_fraction_digits": 2,
    },
}

DEFAULT_CATALOG_ROOT = FsPath(__file__).resolve().parents[1] / "catalogs"
CATALOG_ROOT = FsPath(os.getenv("LOCALIZATION_CATALOG_DIR", str(DEFAULT_CATALOG_ROOT)))


def _normalize_translation_namespaces(payload: dict[str, object]) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for namespace, namespace_values in payload.items():
        if not isinstance(namespace, str) or not isinstance(namespace_values, dict):
            continue
        key_values: dict[str, str] = {}
        for key, value in namespace_values.items():
            if isinstance(key, str) and isinstance(value, str):
                key_values[key] = value
        if key_values:
            normalized[namespace] = key_values
    return normalized


def _load_catalog_json(path: FsPath) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _load_catalog_configuration(
    catalog_root: FsPath,
) -> tuple[str, dict[str, dict[str, Optional[str]]], dict[str, dict[str, dict[str, str]]]] | None:
    locales_payload = _load_catalog_json(catalog_root / "locales.json")
    if locales_payload is None:
        return None

    default_locale_raw = locales_payload.get("default_locale")
    locales_metadata_raw = locales_payload.get("locales")
    if not isinstance(default_locale_raw, str) or not isinstance(locales_metadata_raw, dict):
        return None

    locales_metadata: dict[str, dict[str, Optional[str]]] = {}
    for locale_code, metadata in locales_metadata_raw.items():
        if not isinstance(locale_code, str) or not isinstance(metadata, dict):
            continue
        fallback_locale_raw = metadata.get("fallback_locale")
        fallback_locale = fallback_locale_raw if isinstance(fallback_locale_raw, str) else None
        locales_metadata[locale_code] = {
            "native_name": str(metadata.get("native_name") or locale_code),
            "fallback_locale": fallback_locale,
            "status": str(metadata.get("status") or "fallback_en_gb"),
        }

    if default_locale_raw not in locales_metadata:
        return None

    translations: dict[str, dict[str, dict[str, str]]] = {}
    translations_dir = catalog_root / "translations"
    for locale_code in locales_metadata:
        locale_payload = _load_catalog_json(translations_dir / f"{locale_code}.json")
        if locale_payload is None:
            continue
        translations[locale_code] = _normalize_translation_namespaces(locale_payload)

    if default_locale_raw not in translations:
        return None

    return default_locale_raw, locales_metadata, translations


if catalog_config := _load_catalog_configuration(CATALOG_ROOT):
    DEFAULT_LOCALE, SUPPORTED_LOCALE_METADATA, fake_translations_db = catalog_config


class SupportedLocale(BaseModel):
    code: str
    native_name: str
    fallback_locale: Optional[str] = None
    status: str


class LocaleFormatStandards(BaseModel):
    locale: str
    default_currency: str
    date_style: str
    time_style: str
    time_zone: str
    number_min_fraction_digits: int
    number_max_fraction_digits: int


class TranslationLocaleHealth(BaseModel):
    code: str
    status: str
    total_reference_keys: int
    localized_keys: int
    fallback_keys: int
    estimated_fallback_hit_rate_percent: float
    fully_untranslated_namespaces_count: int
    partially_translated_namespaces_count: int
    missing_key_count: int
    missing_key_samples: list[str]


class TranslationHealthSummary(BaseModel):
    total_locales: int
    locales_with_fallback: int
    average_fallback_hit_rate_percent: float
    highest_fallback_locale: Optional[str] = None
    highest_fallback_hit_rate_percent: float


class TranslationHealthResponse(BaseModel):
    generated_at: datetime.datetime
    default_locale: str
    reference_total_keys: int
    locales: list[TranslationLocaleHealth]
    summary: TranslationHealthSummary


class LocaleRoadmapItem(BaseModel):
    code: str
    native_name: str
    status: str
    fallback_locale: Optional[str] = None
    translation_coverage_percent: float
    rollout_stage: Literal["production_ready", "beta", "planning"]
    default_currency: str
    time_zone: str
    recommended_next_step: str


class LocaleRoadmapResponse(BaseModel):
    generated_at: datetime.datetime
    default_locale: str
    items: list[LocaleRoadmapItem]


def _merge_locale_data(base: Dict[str, Dict[str, str]], override: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    merged = deepcopy(base)
    for namespace, namespace_values in override.items():
        if namespace not in merged:
            merged[namespace] = {}
        merged[namespace].update(namespace_values)
    return merged


def _resolve_locale_data(locale: str) -> Dict[str, Dict[str, str]] | None:
    locale_metadata = SUPPORTED_LOCALE_METADATA.get(locale)
    if locale_metadata is None:
        return None

    base_locale_data = fake_translations_db.get(DEFAULT_LOCALE, {})
    resolved = deepcopy(base_locale_data)
    locale_specific = fake_translations_db.get(locale)
    if locale_specific:
        resolved = _merge_locale_data(resolved, locale_specific)
    return resolved


def _collect_namespace_key_map(data: Dict[str, Dict[str, str]]) -> dict[str, set[str]]:
    namespace_map: dict[str, set[str]] = {}
    for namespace, namespace_values in data.items():
        if not isinstance(namespace_values, dict):
            continue
        namespace_map[namespace] = set(namespace_values.keys())
    return namespace_map


def _flatten_keys(namespace_map: dict[str, set[str]]) -> set[str]:
    flattened: set[str] = set()
    for namespace, keys in namespace_map.items():
        for key in keys:
            flattened.add(f"{namespace}.{key}")
    return flattened


def _build_locale_health(
    *,
    locale: str,
    base_namespace_map: dict[str, set[str]],
    reference_keys: set[str],
) -> TranslationLocaleHealth:
    locale_metadata = SUPPORTED_LOCALE_METADATA.get(locale, {})
    locale_specific_data = fake_translations_db.get(locale, {})
    locale_namespace_map = _collect_namespace_key_map(locale_specific_data)
    locale_specific_keys = _flatten_keys(locale_namespace_map)
    localized_reference_keys = reference_keys.intersection(locale_specific_keys)
    missing_reference_keys = sorted(reference_keys - localized_reference_keys)
    total_reference_keys = len(reference_keys)
    fallback_keys = len(missing_reference_keys)
    fallback_hit_rate = round((fallback_keys / total_reference_keys) * 100, 1) if total_reference_keys else 0.0

    fully_untranslated_namespaces_count = sum(
        1 for namespace in base_namespace_map if namespace not in locale_namespace_map
    )
    partially_translated_namespaces_count = 0
    for namespace, base_keys in base_namespace_map.items():
        locale_keys = locale_namespace_map.get(namespace, set())
        if locale_keys and not base_keys.issubset(locale_keys):
            partially_translated_namespaces_count += 1

    return TranslationLocaleHealth(
        code=locale,
        status=str(locale_metadata.get("status") or "fallback_en_gb"),
        total_reference_keys=total_reference_keys,
        localized_keys=len(localized_reference_keys),
        fallback_keys=fallback_keys,
        estimated_fallback_hit_rate_percent=fallback_hit_rate,
        fully_untranslated_namespaces_count=fully_untranslated_namespaces_count,
        partially_translated_namespaces_count=partially_translated_namespaces_count,
        missing_key_count=fallback_keys,
        missing_key_samples=missing_reference_keys[:25],
    )


def _resolve_locale_format_standards(locale: str) -> LocaleFormatStandards | None:
    if locale not in SUPPORTED_LOCALE_METADATA:
        return None
    standards = LOCALE_FORMAT_STANDARDS.get(locale) or LOCALE_FORMAT_STANDARDS.get(DEFAULT_LOCALE)
    if standards is None:
        return None
    return LocaleFormatStandards(
        locale=locale,
        default_currency=str(standards.get("default_currency") or "GBP"),
        date_style=str(standards.get("date_style") or "medium"),
        time_style=str(standards.get("time_style") or "short"),
        time_zone=str(standards.get("time_zone") or "Europe/London"),
        number_min_fraction_digits=int(standards.get("number_min_fraction_digits") or 0),
        number_max_fraction_digits=int(standards.get("number_max_fraction_digits") or 2),
    )


def _build_locale_roadmap_item(
    *,
    locale: str,
    locale_health: TranslationLocaleHealth,
) -> LocaleRoadmapItem:
    metadata = SUPPORTED_LOCALE_METADATA.get(locale, {})
    native_name = str(metadata.get("native_name") or locale)
    fallback_locale = metadata.get("fallback_locale")
    standards = _resolve_locale_format_standards(locale) or _resolve_locale_format_standards(DEFAULT_LOCALE)
    default_currency = standards.default_currency if standards else "GBP"
    time_zone = standards.time_zone if standards else "Europe/London"
    coverage_percent = (
        round((locale_health.localized_keys / locale_health.total_reference_keys) * 100, 1)
        if locale_health.total_reference_keys
        else 100.0
    )
    if locale_health.fallback_keys == 0 and str(metadata.get("status")) == "translated":
        rollout_stage = "production_ready"
        next_step = "Maintain translation freshness and monitor fallback hit-rate drift."
    elif coverage_percent >= 60.0:
        rollout_stage = "beta"
        next_step = "Complete remaining high-traffic namespaces before production rollout."
    else:
        rollout_stage = "planning"
        next_step = "Prioritize core onboarding, dashboard, and submission namespaces first."

    return LocaleRoadmapItem(
        code=locale,
        native_name=native_name,
        status=str(metadata.get("status") or "fallback_en_gb"),
        fallback_locale=fallback_locale,
        translation_coverage_percent=coverage_percent,
        rollout_stage=rollout_stage,
        default_currency=default_currency,
        time_zone=time_zone,
        recommended_next_step=next_step,
    )

# --- Endpoints ---

@app.get(
    "/translations/locales",
    response_model=list[SupportedLocale],
    summary="List supported locales and fallback policy"
)
async def list_supported_locales():
    return [
        SupportedLocale(
            code=code,
            native_name=str(metadata.get("native_name") or code),
            fallback_locale=metadata.get("fallback_locale"),
            status=str(metadata.get("status") or "fallback_en_gb"),
        )
        for code, metadata in SUPPORTED_LOCALE_METADATA.items()
    ]


@app.get(
    "/translations/health",
    response_model=TranslationHealthResponse,
    summary="Get translation health telemetry across locales"
)
async def get_translation_health():
    base_locale_data = fake_translations_db.get(DEFAULT_LOCALE, {})
    base_namespace_map = _collect_namespace_key_map(base_locale_data)
    reference_keys = _flatten_keys(base_namespace_map)
    locale_health_rows = [
        _build_locale_health(
            locale=locale_code,
            base_namespace_map=base_namespace_map,
            reference_keys=reference_keys,
        )
        for locale_code in SUPPORTED_LOCALE_METADATA
    ]
    locale_health_rows.sort(key=lambda item: item.code)

    total_locales = len(locale_health_rows)
    locales_with_fallback = sum(1 for row in locale_health_rows if row.fallback_keys > 0)
    average_fallback = (
        round(
            sum(row.estimated_fallback_hit_rate_percent for row in locale_health_rows) / total_locales,
            1,
        )
        if total_locales
        else 0.0
    )
    highest = max(
        locale_health_rows,
        key=lambda row: row.estimated_fallback_hit_rate_percent,
        default=None,
    )

    return TranslationHealthResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        default_locale=DEFAULT_LOCALE,
        reference_total_keys=len(reference_keys),
        locales=locale_health_rows,
        summary=TranslationHealthSummary(
            total_locales=total_locales,
            locales_with_fallback=locales_with_fallback,
            average_fallback_hit_rate_percent=average_fallback,
            highest_fallback_locale=highest.code if highest else None,
            highest_fallback_hit_rate_percent=highest.estimated_fallback_hit_rate_percent if highest else 0.0,
        ),
    )


@app.get(
    "/translations/locales/roadmap",
    response_model=LocaleRoadmapResponse,
    summary="Get locale rollout roadmap for international expansion"
)
async def get_locale_rollout_roadmap():
    base_locale_data = fake_translations_db.get(DEFAULT_LOCALE, {})
    base_namespace_map = _collect_namespace_key_map(base_locale_data)
    reference_keys = _flatten_keys(base_namespace_map)
    locale_rows = [
        _build_locale_health(
            locale=locale_code,
            base_namespace_map=base_namespace_map,
            reference_keys=reference_keys,
        )
        for locale_code in SUPPORTED_LOCALE_METADATA
    ]
    roadmap_items = [
        _build_locale_roadmap_item(locale=row.code, locale_health=row)
        for row in sorted(locale_rows, key=lambda item: item.code)
    ]
    return LocaleRoadmapResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        default_locale=DEFAULT_LOCALE,
        items=roadmap_items,
    )


@app.get(
    "/translations/{locale}/format-standards",
    response_model=LocaleFormatStandards,
    summary="Get ICU/pluralization formatting standards for locale"
)
async def get_locale_format_standards(locale: str = Path(..., example="en-GB")):
    if standards := _resolve_locale_format_standards(locale):
        return standards
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Formatting standards for locale '{locale}' not found."
    )


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
    if locale_data := _resolve_locale_data(locale):
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
    locale_data = _resolve_locale_data(locale)
    if locale_data and (component_data := locale_data.get(component)):
        return component_data

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Translations for locale '{locale}' and component '{component}' not found."
    )
