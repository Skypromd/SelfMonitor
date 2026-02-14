from copy import deepcopy
from typing import Dict, Optional

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
            "save": "Save"
        },
        "login": {
            "title": "FinTech App",
            "description": "Register or log in to continue",
            "register_button": "Register",
            "login_button": "Login"
        },
        "nav": {
            "dashboard": "Dashboard",
            "transactions": "Transactions",
            "documents": "Documents",
            "profile": "Profile"
        },
        "dashboard": {
            "title": "Main Dashboard",
            "description": "Welcome to your financial dashboard."
        },
        "profile": {
            "title": "Your Profile"
        },
        "partners": {
            "description": "Here is a list of trusted, FCA-regulated partners you can be handed off to for advice.",
            "handoff_button": "Initiate Handoff"
        },
        "submission": {
            "description": "Calculate and submit your tax return to HMRC.",
            "form_title": "New UK Tax Submission",
            "submit_button": "Calculate & Submit to HMRC",
            "success_title": "Submission Successfully Initiated"
        },
        "admin": {
            "description": "Manage users and system settings.",
            "form_title": "Deactivate a User",
            "deactivate_button": "Deactivate User"
        },
        "reports": {
            "description": "Generate custom reports based on your financial data.",
            "mortgage_title": "Mortgage Readiness Report",
            "mortgage_description": "Generate a PDF summary of your income over the last 12 months. This can be useful when applying for a mortgage.",
            "generate_button": "Generate Report",
            "generating_button": "Generating..."
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
            "all_documents_title": "All Uploaded Documents"
        }
    },
    "de-DE": {
        "common": {
            "submit": "Einreichen",
            "cancel": "Abbrechen",
            "logout": "Ausloggen",
            "save": "Speichern"
        },
        "login": {
            "title": "FinTech App",
            "description": "Registrieren Sie sich oder melden Sie sich an, um fortzufahren",
            "register_button": "Registrieren",
            "login_button": "Anmelden"
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
            "description": "Willkommen zu Ihrem Finanz-Dashboard."
        },
        "profile": {
            "title": "Ihr Profil"
        },
        "partners": {
            "description": "Hier finden Sie eine Liste von vertrauenswürdigen, von der FCA regulierten Partnern, an die Sie zur Beratung weitergeleitet werden können.",
            "handoff_button": "Handoff einleiten"
        },
        "submission": {
            "description": "Berechnen und übermitteln Sie hier Ihre Steuererklärung an HMRC.",
            "form_title": "Neue Steuererklärung für Großbritannien",
            "submit_button": "Berechnen & an HMRC senden",
            "success_title": "Übermittlung erfolgreich eingeleitet"
        },
        "admin": {
            "description": "Benutzer und Systemeinstellungen verwalten.",
            "form_title": "Einen Benutzer deaktivieren",
            "deactivate_button": "Benutzer deaktivieren"
        },
        "reports": {
            "description": "Erstellen Sie benutzerdefinierte Berichte basierend auf Ihren Finanzdaten.",
            "mortgage_title": "Bericht zur Hypothekenbereitschaft",
            "mortgage_description": "Erstellen Sie eine PDF-Zusammenfassung Ihres Einkommens der letzten 12 Monate. Dies kann bei der Beantragung einer Hypothek nützlich sein.",
            "generate_button": "Bericht erstellen",
            "generating_button": "Wird erstellt..."
        },
        "marketplace": {
            "description": "Entdecken Sie unseren Marktplatz mit vertrauenswürdigen Partnern, die Ihnen bei Buchhaltung, Hypotheken und Versicherungen helfen können."
        },
        "activity": {
            "description": "Hier ist eine Aufzeichnung der letzten wichtigen Ereignisse in Ihrem Konto.",
            "col_date": "Datum",
            "col_action": "Aktion",
            "col_details": "Details"
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
            "all_documents_title": "Alle hochgeladenen Dokumente"
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


class SupportedLocale(BaseModel):
    code: str
    native_name: str
    fallback_locale: Optional[str] = None
    status: str


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
