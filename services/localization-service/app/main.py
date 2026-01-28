from fastapi import FastAPI, HTTPException, status, Path
from typing import Dict

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
            "col_uploaded_at": "Uploaded At",
            "search_title": "Semantic Document Search",
            "search_description": "Ask a question about your documents in natural language.",
            "search_placeholder": "e.g., 'where did I buy coffee last month?'",
            "search_button": "Search",
            "search_results_title": "Search Results",
            "search_similarity_label": "Similarity score:",
            "all_documents_title": "All Uploaded Documents",
            "select_file_error": "Please select a file first.",
            "upload_success_prefix": "File uploaded:"
        },
        "reports": {
            "description": "Generate custom reports based on your financial data.",
            "mortgage_title": "Mortgage Readiness Report",
            "mortgage_description": "Generate a PDF summary of your income over the last 12 months. This can be useful when applying for a mortgage.",
            "generate_button": "Generate Report",
            "generating_button": "Generating..."
        },
        "marketplace": {
            "description": "Discover our marketplace of trusted partners for accounting, insurance, and more.",
            "request_button": "Request Contact",
            "handoff_confirmation": "Your request has been sent to"
        },
        "submission": {
            "description": "Calculate and submit your tax return to HMRC.",
            "form_title": "New UK Tax Submission",
            "submit_button": "Calculate & Submit to HMRC",
            "success_title": "Submission Successfully Initiated",
            "submitting": "Submitting...",
            "status_label": "Submission Status",
            "id_label": "HMRC Submission ID",
            "reminder_note": "We've added a calendar reminder for the 31 January payment deadline."
        },
        "profile": {
            "title": "Your Profile",
            "description": "Review and update your profile details.",
            "empty_profile": "No profile found. Create one by saving.",
            "saved_message": "Profile saved successfully!",
            "first_name": "First Name",
            "last_name": "Last Name",
            "date_of_birth": "Date of Birth"
        },
        "admin": {
            "description": "Manage users and system settings.",
            "form_title": "Deactivate a User",
            "deactivate_button": "Deactivate User",
            "email_placeholder": "user.email@example.com",
            "deactivated_message": "User deactivated:"
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
            "col_uploaded_at": "Hochgeladen am",
            "search_title": "Semantische Dokumentsuche",
            "search_description": "Stellen Sie eine Frage zu Ihren Dokumenten in natürlicher Sprache.",
            "search_placeholder": "z.B. 'wo habe ich letzten monat kaffee gekauft?'",
            "search_button": "Suchen",
            "search_results_title": "Suchergebnisse",
            "search_similarity_label": "Ähnlichkeitswert:",
            "all_documents_title": "Alle hochgeladenen Dokumente",
            "select_file_error": "Bitte wählen Sie zuerst eine Datei aus.",
            "upload_success_prefix": "Datei hochgeladen:"
        },
        "reports": {
            "description": "Erstellen Sie benutzerdefinierte Berichte basierend auf Ihren Finanzdaten.",
            "mortgage_title": "Bericht zur Hypothekenbereitschaft",
            "mortgage_description": "Erstellen Sie eine PDF-Zusammenfassung Ihres Einkommens der letzten 12 Monate. Dies kann bei der Beantragung einer Hypothek nützlich sein.",
            "generate_button": "Bericht erstellen",
            "generating_button": "Wird erstellt..."
        },
        "marketplace": {
            "description": "Entdecken Sie unseren Marktplatz mit vertrauenswürdigen Partnern für Buchhaltung, Versicherungen und mehr.",
            "request_button": "Kontakt anfragen",
            "handoff_confirmation": "Ihre Anfrage wurde gesendet an"
        },
        "submission": {
            "description": "Berechnen und übermitteln Sie hier Ihre Steuererklärung an HMRC.",
            "form_title": "Neue Steuererklärung für Großbritannien",
            "submit_button": "Berechnen & an HMRC senden",
            "success_title": "Übermittlung erfolgreich eingeleitet",
            "submitting": "Wird gesendet...",
            "status_label": "Übermittlungsstatus",
            "id_label": "HMRC-Übermittlungs-ID",
            "reminder_note": "Wir haben eine Kalendereinladung für die Zahlungsfrist am 31. Januar hinzugefügt."
        },
        "profile": {
            "title": "Ihr Profil",
            "description": "Überprüfen und aktualisieren Sie Ihre Profildaten.",
            "empty_profile": "Kein Profil gefunden. Speichern Sie, um eines zu erstellen.",
            "saved_message": "Profil erfolgreich gespeichert!",
            "first_name": "Vorname",
            "last_name": "Nachname",
            "date_of_birth": "Geburtsdatum"
        },
        "admin": {
            "description": "Benutzer und Systemeinstellungen verwalten.",
            "form_title": "Einen Benutzer deaktivieren",
            "deactivate_button": "Benutzer deaktivieren",
            "email_placeholder": "user.email@example.com",
            "deactivated_message": "Benutzer deaktiviert:"
        }
    },
    "ru-RU": {
        "common": {
            "submit": "Отправить",
            "cancel": "Отмена",
            "logout": "Выйти",
            "save": "Сохранить",
            "loading": "Загрузка..."
        },
        "login": {
            "title": "Помощник по Self-Assessment",
            "description": "Зарегистрируйтесь или войдите, чтобы продолжить",
            "register_button": "Регистрация",
            "login_button": "Войти",
            "email_placeholder": "Email",
            "password_placeholder": "Пароль",
            "register_success": "Регистрация успешна. Теперь можно войти."
        },
        "nav": {
            "dashboard": "Дашборд",
            "activity": "Активность",
            "transactions": "Транзакции",
            "documents": "Документы",
            "reports": "Отчеты",
            "marketplace": "Маркетплейс",
            "submission": "Подача налогов",
            "profile": "Профиль",
            "admin": "Админ"
        },
        "dashboard": {
            "title": "Главная панель",
            "description": "Добро пожаловать в ваш Self-Assessment.",
            "tax_estimator_title": "Оценка налога (UK)",
            "tax_estimator_button": "Рассчитать налог",
            "tax_estimator_result_title": "Оценка налога за",
            "total_income_label": "Общий доход",
            "allowable_expenses_label": "Допустимые расходы",
            "disallowable_expenses_label": "Недопустимые расходы",
            "taxable_profit_label": "Налогооблагаемая прибыль",
            "income_tax_due_label": "Подоходный налог",
            "class2_nic_label": "Class 2 NIC",
            "class4_nic_label": "Class 4 NIC",
            "estimated_tax_due_label": "Итого к уплате",
            "cashflow_title": "Прогноз денежного потока (30 дней)",
            "cashflow_loading": "Формируем прогноз...",
            "readiness_title": "Готовность к сдаче",
            "readiness_description": "Показывает готовность данных к Self-Assessment.",
            "readiness_score_label": "Индекс готовности",
            "readiness_missing_categories": "Без категории:",
            "readiness_missing_business_use": "Нет процента бизнес-использования:",
            "readiness_actions_title": "Следующие шаги",
            "readiness_action_categories": "Категоризируйте оставшиеся транзакции.",
            "readiness_action_business_use": "Укажите бизнес-долю для смешанных расходов.",
            "readiness_no_transactions": "Транзакции еще не импортированы.",
            "readiness_low": "Низкая готовность",
            "readiness_medium": "Средняя готовность",
            "readiness_high": "Высокая готовность",
            "readiness_loading": "Считаем готовность...",
            "action_next_title": "Что дальше?",
            "action_next_description": "Посмотрите маркетплейс с проверенными партнерами для страховки, бухгалтерии и другого.",
            "action_next_button": "Перейти к партнерам"
        },
        "activity": {
            "description": "Журнал последних событий в вашем аккаунте.",
            "col_date": "Дата",
            "col_action": "Действие",
            "col_details": "Детали"
        },
        "transactions": {
            "title": "Транзакции",
            "description": "Подключите банк, чтобы импортировать и категоризировать транзакции.",
            "bank_connections_title": "Банковские подключения",
            "connect_button": "Подключить банк",
            "consent_prompt": "Нажмите ссылку, чтобы дать доступ банку:",
            "loading": "Загружаем транзакции...",
            "recent_title": "Последние транзакции",
            "col_date": "Дата",
            "col_description": "Описание",
            "col_amount": "Сумма",
            "col_category": "Категория",
            "select_placeholder": "Выбрать...",
            "csv_title": "CSV импорт",
            "csv_description": "Загрузите CSV, если банк не поддерживается.",
            "csv_account_label": "Account ID",
            "csv_account_placeholder": "Вставьте UUID счета",
            "csv_upload_button": "Загрузить CSV",
            "csv_uploading": "Загружаем...",
            "csv_success": "CSV импорт принят. Импортировано:",
            "csv_skipped_label": "Пропущено:",
            "csv_select_error": "Выберите CSV файл.",
            "csv_account_error": "Нужен Account ID."
        },
        "documents": {
            "description": "Загружайте и храните чеки и счета.",
            "upload_title": "Загрузить документ",
            "upload_button": "Загрузить",
            "uploading_button": "Загрузка...",
            "col_filename": "Файл",
            "col_status": "Статус",
            "col_vendor": "Поставщик",
            "col_amount": "Сумма",
            "col_uploaded_at": "Загружено",
            "search_title": "Семантический поиск документов",
            "search_description": "Задайте вопрос к вашим документам на естественном языке.",
            "search_placeholder": "например, «где я купил кофе в прошлом месяце?»",
            "search_button": "Искать",
            "search_results_title": "Результаты поиска",
            "search_similarity_label": "Схожесть:",
            "all_documents_title": "Все документы",
            "select_file_error": "Сначала выберите файл.",
            "upload_success_prefix": "Файл загружен:"
        },
        "reports": {
            "description": "Создавайте отчеты на основе финансовых данных.",
            "mortgage_title": "Отчет для ипотеки",
            "mortgage_description": "PDF-сводка доходов за 12 месяцев.",
            "generate_button": "Сформировать отчет",
            "generating_button": "Формируется..."
        },
        "marketplace": {
            "description": "Партнеры для бухгалтерии, страховки и прочего.",
            "request_button": "Запросить контакт",
            "handoff_confirmation": "Запрос отправлен партнеру"
        },
        "submission": {
            "description": "Рассчитать и отправить декларацию в HMRC.",
            "form_title": "Новая подача UK Self-Assessment",
            "submit_button": "Рассчитать и отправить в HMRC",
            "success_title": "Подача начата",
            "submitting": "Отправляем...",
            "status_label": "Статус подачи",
            "id_label": "ID подачи HMRC",
            "reminder_note": "Мы добавили напоминание в календарь о платеже до 31 января."
        },
        "profile": {
            "title": "Профиль",
            "description": "Обновите свои персональные данные.",
            "empty_profile": "Профиль не найден. Создайте его, сохранив данные.",
            "saved_message": "Профиль сохранен.",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "date_of_birth": "Дата рождения"
        },
        "admin": {
            "description": "Управление пользователями и настройками.",
            "form_title": "Деактивация пользователя",
            "deactivate_button": "Деактивировать",
            "email_placeholder": "user.email@example.com",
            "deactivated_message": "Пользователь деактивирован:"
        }
    }
}

# --- Endpoints ---

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
    if locale_data := fake_translations_db.get(locale):
        if component_data := locale_data.get(component):
            return component_data

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Translations for locale '{locale}' and component '{component}' not found."
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
    if locale_data := fake_translations_db.get(locale):
        return locale_data

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Translations for locale '{locale}' not found."
    )
