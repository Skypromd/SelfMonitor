"""Quick demo server for SelfMonitor Platform - Full Interactive Version"""
from typing import Any
from fastapi import FastAPI
from fastapi.responses import Response, HTMLResponse
import json

app = FastAPI(
    title="SelfMonitor FinTech Platform - Interactive Demo",
    description="Full demonstration server with 33 microservices visualization and interactive menu",
    version="2.0.0"
)

# Complete list of all 33 microservices
ALL_SERVICES = [
    {"id": 1, "name": "auth-service", "port": 8001, "status": "running", "category": "core", "description": "Аутентификация и авторизация"},
    {"id": 2, "name": "user-profile-service", "port": 8002, "status": "running", "category": "core", "description": "Управление профилями пользователей"},
    {"id": 3, "name": "tenant-router", "port": 8003, "status": "running", "category": "core", "description": "Маршрутизация multi-tenant запросов"},
    {"id": 4, "name": "transactions-service", "port": 8004, "status": "running", "category": "financial", "description": "Обработка транзакций"},
    {"id": 5, "name": "banking-connector", "port": 8005, "status": "running", "category": "financial", "description": "Подключение к банковским API"},
    {"id": 6, "name": "categorization-service", "port": 8006, "status": "running", "category": "financial", "description": "Категоризация транзакций"},
    {"id": 7, "name": "analytics-service", "port": 8007, "status": "running", "category": "analytics", "description": "Финансовая аналитика"},
    {"id": 8, "name": "business-intelligence", "port": 8008, "status": "running", "category": "analytics", "description": "BI и отчетность"},
    {"id": 9, "name": "fraud-detection", "port": 8009, "status": "running", "category": "security", "description": "Детектирование мошенничества"},
    {"id": 10, "name": "compliance-service", "port": 8010, "status": "running", "category": "security", "description": "Соответствие регуляторным требованиям"},
    {"id": 11, "name": "documents-service", "port": 8011, "status": "running", "category": "documents", "description": "Управление документами"},
    {"id": 12, "name": "qna-service", "port": 8012, "status": "degraded", "category": "ai", "description": "AI вопросы-ответы (Weaviate)"},
    {"id": 13, "name": "advice-service", "port": 8013, "status": "running", "category": "ai", "description": "AI финансовые советы"},
    {"id": 14, "name": "ai-agent-service", "port": 8014, "status": "running", "category": "ai", "description": "AI агенты для автоматизации"},
    {"id": 15, "name": "tax-optimization", "port": 8015, "status": "running", "category": "tax", "description": "Налоговая оптимизация"},
    {"id": 16, "name": "tax-filing", "port": 8016, "status": "running", "category": "tax", "description": "Подача налоговых деклараций"},
    {"id": 17, "name": "invoice-service", "port": 8017, "status": "running", "category": "documents", "description": "Управление счетами"},
    {"id": 18, "name": "calendar-service", "port": 8018, "status": "running", "category": "productivity", "description": "Календарь и события"},
    {"id": 19, "name": "notifications-service", "port": 8019, "status": "running", "category": "communications", "description": "Уведомления push/email/SMS"},
    {"id": 20, "name": "goal-tracking", "port": 8020, "status": "running", "category": "productivity", "description": "Отслеживание целей"},
    {"id": 21, "name": "cost-optimization", "port": 8021, "status": "running", "category": "financial", "description": "Оптимизация расходов"},
    {"id": 22, "name": "predictive-analytics", "port": 8022, "status": "running", "category": "analytics", "description": "Предсказательная аналитика ML"},
    {"id": 23, "name": "subscription-management", "port": 8023, "status": "running", "category": "billing", "description": "Управление подписками"},
    {"id": 24, "name": "payment-gateway", "port": 8024, "status": "running", "category": "billing", "description": "Платежный шлюз"},
    {"id": 25, "name": "localization-service", "port": 8025, "status": "running", "category": "infrastructure", "description": "Локализация и переводы"},
    {"id": 26, "name": "integrations-service", "port": 8026, "status": "running", "category": "infrastructure", "description": "Интеграции с внешними API"},
    {"id": 27, "name": "consent-service", "port": 8027, "status": "running", "category": "security", "description": "Управление согласиями GDPR"},
    {"id": 28, "name": "customer-success", "port": 8028, "status": "running", "category": "support", "description": "Поддержка клиентов"},
    {"id": 29, "name": "graphql-gateway", "port": 4000, "status": "running", "category": "infrastructure", "description": "GraphQL Federation Gateway"},
    {"id": 30, "name": "tenant-provisioning", "port": 8030, "status": "running", "category": "core", "description": "Создание новых tenant"},
    {"id": 31, "name": "audit-logging", "port": 8031, "status": "running", "category": "security", "description": "Аудит всех действий"},
    {"id": 32, "name": "recommendation-engine", "port": 8032, "status": "running", "category": "ai", "description": "Рекомендательная система ML"},
    {"id": 33, "name": "nginx-gateway", "port": 8000, "status": "running", "category": "infrastructure", "description": "Nginx API Gateway"}
]

@app.get("/favicon.ico")
async def favicon() -> Response:
    """Return empty favicon to prevent 404 errors"""
    return Response(content=b"", media_type="image/x-icon")

@app.get("/robots.txt")
async def robots() -> Response:
    """Return robots.txt"""
    return Response(content="User-agent: *\nDisallow:", media_type="text/plain")

@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Main landing page with complete navigation menu"""
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SelfMonitor FinTech Platform - Главная</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .navbar {
                background: rgba(255,255,255,0.95);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 20px 30px;
                margin-bottom: 30px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
            }
            .logo { font-size: 1.8em; font-weight: bold; color: #667eea; }
            .nav-links { display: flex; gap: 20px; flex-wrap: wrap; }
            .nav-link {
                color: #333;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 8px;
                transition: all 0.3s;
                font-weight: 500;
            }
            .nav-link:hover {
                background: #667eea;
                color: white;
                transform: translateY(-2px);
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            .hero {
                background: white;
                border-radius: 20px;
                padding: 60px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                margin-bottom: 30px;
                animation: fadeIn 0.8s ease-in;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            h1 {
                font-size: 3.5em;
                margin-bottom: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .subtitle { font-size: 1.3em; color: #6b7280; margin-bottom: 30px; }
            .status-badge {
                display: inline-block;
                background: #10b981;
                color: white;
                padding: 12px 24px;
                border-radius: 50px;
                font-weight: bold;
                margin: 20px 0;
                font-size: 1.1em;
            }
            .menu-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-top: 40px;
            }
            .menu-card {
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-decoration: none;
                color: #333;
                transition: all 0.3s;
                border: 2px solid transparent;
            }
            .menu-card:hover {
                transform: translateY(-10px);
                box-shadow: 0 15px 50px rgba(102, 126, 234, 0.4);
                border-color: #667eea;
            }
            .card-icon { font-size: 3em; margin-bottom: 15px; }
            .card-title { font-size: 1.5em; font-weight: bold; margin-bottom: 10px; color: #667eea; }
            .card-desc { color: #6b7280; line-height: 1.6; }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                text-align: center;
            }
            .stat-number { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
            .stat-label { font-size: 0.9em; opacity: 0.9; }
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="logo">🚀 SelfMonitor</div>
            <div class="nav-links">
                <a href="/" class="nav-link">🏠 Главная</a>
                <a href="/dashboard" class="nav-link">📊 Dashboard</a>
                <a href="/architecture" class="nav-link">🏗️ Архитектура</a>
                <a href="/guide" class="nav-link">📖 Руководство</a>
                <a href="/docs" class="nav-link">📚 API Docs</a>
            </div>
        </nav>
        
        <div class="container">
            <div class="hero">
                <h1>SelfMonitor FinTech Platform</h1>
                <p class="subtitle">Полнофункциональная платформа для самозанятых с 33 микросервисами</p>
                <div class="status-badge">✅ ВСЕ СИСТЕМЫ РАБОТАЮТ</div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">33</div>
                        <div class="stat-label">Микросервиса</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">100%</div>
                        <div class="stat-label">Uptime</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">5</div>
                        <div class="stat-label">Категорий</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">AI</div>
                        <div class="stat-label">Powered</div>
                    </div>
                </div>
            </div>
            
            <div class="menu-grid">
                <a href="/dashboard" class="menu-card">
                    <div class="card-icon">📊</div>
                    <div class="card-title">Dashboard</div>
                    <div class="card-desc">Мониторинг всех 33 микросервисов в реальном времени. Проверьте статус, производительность и доступность каждого сервиса.</div>
                </a>
                
                <a href="/architecture" class="menu-card">
                    <div class="card-icon">🏗️</div>
                    <div class="card-title">Архитектура</div>
                    <div class="card-desc">Интерактивная карта архитектуры платформы. Посмотрите как связаны сервисы и как данные перемещаются по системе.</div>
                </a>
                
                <a href="/guide" class="menu-card">
                    <div class="card-icon">📖</div>
                    <div class="card-title">Руководство</div>
                    <div class="card-desc">Пошаговое руководство по использованию платформы. Узнайте как работает каждый модуль и как их использовать вместе.</div>
                </a>
                
                <a href="/api/profile" class="menu-card">
                    <div class="card-icon">👤</div>
                    <div class="card-title">Профиль</div>
                    <div class="card-desc">Управление профилем пользователя. Настройки, предпочтения, subscription tier и персональные данные.</div>
                </a>
                
                <a href="/api/transactions" class="menu-card">
                    <div class="card-icon">💰</div>
                    <div class="card-title">Транзакции</div>
                    <div class="card-desc">Все финансовые транзакции в одном месте. Автоматическая категоризация и интеграция с банками.</div>
                </a>
                
                <a href="/api/analytics" class="menu-card">
                    <div class="card-icon">📈</div>
                    <div class="card-title">Аналитика</div>
                    <div class="card-desc">Подробная финансовая аналитика. Доходы, расходы, тренды и прогнозы на основе ML моделей.</div>
                </a>
                
                <a href="/docs" class="menu-card">
                    <div class="card-icon">📚</div>
                    <div class="card-title">API Документация</div>
                    <div class="card-desc">Swagger UI с интерактивной документацией. Тестируйте API эндпоинты прямо в браузере.</div>
                </a>
                
                <a href="/health" class="menu-card">
                    <div class="card-icon">❤️</div>
                    <div class="card-title">Health Check</div>
                    <div class="card-desc">Статус здоровья системы. Проверка доступности API, базы данных, кэша и других критических компонентов.</div>
                </a>
            </div>
        </div>
    </body>
    </html>
    """
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "services": {
            "api": "operational",
            "database": "ready (mock)",
            "cache": "ready (mock)"
        }
    }

@app.get("/api/profile")
async def get_profile() -> dict[str, str]:
    return {
        "user_id": "demo-user-001",
        "email": "demo@selfmonitor.io",
        "name": "Demo User",
        "currency": "USD",
        "timezone": "UTC",
        "subscription": "premium"
    }

@app.get("/api/transactions")
async def get_transactions() -> dict[str, Any]:
    return {
        "transactions": [
            {
                "id": "tx-001",
                "amount": 150.50,
                "currency": "USD",
                "description": "Software subscription",
                "date": "2026-02-25",
                "category": "Business expense"
            },
            {
                "id": "tx-002",
                "amount": 89.99,
                "currency": "USD",
                "description": "Office supplies",
                "date": "2026-02-24",
                "category": "Supplies"
            }
        ],
        "total": 2
    }

@app.get("/api/analytics")
async def get_analytics() -> dict[str, Any]:
    return {
        "period": "February 2026",
        "total_income": 5420.00,
        "total_expenses": 2340.50,
        "net_profit": 3079.50,
        "expense_categories": {
            "Software & Tools": 450.00,
            "Office Supplies": 289.99,
            "Marketing": 800.00,
            "Professional Services": 800.51
        }
    }

@app.get("/api/services")
async def list_services() -> dict[str, Any]:
    return {
        "microservices": [
            "auth-service",
            "user-profile-service",
            "transactions-service",
            "analytics-service",
            "advice-service",
            "banking-connector",
            "fraud-detection",
            "compliance-service",
            "documents-service",
            "calendar-service",
            "ai-agent-service",
            "recommendation-engine",
            "business-intelligence",
            "customer-success",
            "pricing-engine",
            "integrations-service",
            "partner-registry",
            "payment-gateway",
            "localization-service",
            "consent-service",
            "tax-engine",
            "qna-service",
            "predictive-analytics",
            "security-operations",
            "cost-optimization",
            "referral-service",
            "invoice-service",
            "ipo-readiness",
            "strategic-partnerships",
            "international-expansion",
            "categorization-service",
            "graphql-gateway",
            "tenant-router"
        ],
        "total": 33,
        "architecture": "Multi-tenant microservices"
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 SelfMonitor FinTech Platform - Demo Server")
    print("="*60)
    print("\n📍 Server running at: http://localhost:8000")
    print("\n📚 Available endpoints:")
    print("  • http://localhost:8000/         - Welcome")
    print("  • http://localhost:8000/health    - Health check")
    print("  • http://localhost:8000/api/profile - User profile")
    print("  • http://localhost:8000/api/transactions - Transactions")
    print("  • http://localhost:8000/api/analytics - Analytics")
    print("  • http://localhost:8000/api/services - Service list")
    print("  • http://localhost:8000/docs      - Interactive API docs")
    print("\n⚡ Press CTRL+C to stop\n")
    print("="*60 + "\n")
    
    # Run without WebSocket support to avoid compatibility issues
    import sys
    sys.argv = ["uvicorn", "demo_server_quick:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "none"]
    from uvicorn.main import main as uvicorn_main
    uvicorn_main()  # type: ignore[misc]
