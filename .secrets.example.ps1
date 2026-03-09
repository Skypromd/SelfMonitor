# =============================================================================
# ШАБЛОН СЕКРЕТОВ — скопируй как .secrets.ps1 и заполни своими данными
# Этот файл безопасно хранить в git (нет реальных паролей)
# =============================================================================

# Auth JWT Secret — сгенерируй: openssl rand -hex 32
$SECRET["AUTH_SECRET_KEY"]       = "REPLACE_WITH_LONG_RANDOM_SECRET"
$SECRET["AUTH_ADMIN_PASSWORD"]   = "REPLACE_WITH_ADMIN_PASSWORD"

# SMTP — для отправки писем восстановления пароля
# Gmail: создай App Password на https://myaccount.google.com/apppasswords
$SECRET["SMTP_HOST"]             = "smtp.gmail.com"
$SECRET["SMTP_PORT"]             = "587"
$SECRET["SMTP_USER"]             = "your@gmail.com"
$SECRET["SMTP_PASSWORD"]         = "xxxx xxxx xxxx xxxx"
$SECRET["SMTP_FROM"]             = "SelfMonitor <your@gmail.com>"
