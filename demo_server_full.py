"""SelfMonitor Platform - Full Interactive Demo with 33 Microservices"""
from typing import Any
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
import json

app = FastAPI(
    title="SelfMonitor FinTech Platform",
    description="Complete demo with 33 microservices, interactive dashboard and architecture visualization",
    version="2.0.0"
)

# All 33 microservices
SERVICES = [
    {"id": 1, "name": "auth-service", "port": 8001, "status": "●", "category": "Core", "desc": "Аутентификация JWT"},
    {"id": 2, "name": "user-profile-service", "port": 8002, "status": "●", "category": "Core", "desc": "Профили пользователей"},
    {"id": 3, "name": "tenant-router", "port": 8003, "status": "●", "category": "Core", "desc": "Multi-tenant маршрутизация"},
    {"id": 4, "name": "transactions-service", "port": 8004, "status": "●", "category": "Financial", "desc": "Обработка транзакций"},
    {"id": 5, "name": "banking-connector", "port": 8005, "status": "●", "category": "Financial", "desc": "Интеграция с банками"},
    {"id": 6, "name": "categorization-service", "port": 8006, "status": "●", "category": "Financial", "desc": "Категоризация AI"},
    {"id": 7, "name": "analytics-service", "port": 8007, "status": "●", "category": "Analytics", "desc": "Финансовая аналитика"},
    {"id": 8, "name": "business-intelligence", "port": 8008, "status": "●", "category": "Analytics", "desc": "BI отчёты"},
    {"id": 9, "name": "fraud-detection", "port": 8009, "status": "●", "category": "Security", "desc": "Детекция мошенничества ML"},
    {"id": 10, "name": "compliance-service", "port": 8010, "status": "●", "category": "Security", "desc": "Compliance & GDPR"},
    {"id": 11, "name": "documents-service", "port": 8011, "status": "●", "category": "Documents", "desc": "Управление документами"},
    {"id": 12, "name": "qna-service", "port": 8012, "status": "◐", "category": "AI", "desc": "Q&A Weaviate (degraded)"},
    {"id": 13, "name": "advice-service", "port": 8013, "status": "●", "category": "AI", "desc": "Финансовые советы AI"},
    {"id": 14, "name": "ai-agent-service", "port": 8014, "status": "●", "category": "AI", "desc": "AI агенты автоматизации"},
    {"id": 15, "name": "tax-optimization", "port": 8015, "status": "●", "category": "Tax", "desc": "Налоговая оптимизация"},
    {"id": 16, "name": "tax-filing", "port": 8016, "status": "●", "category": "Tax", "desc": "Подача деклараций"},
    {"id": 17, "name": "invoice-service", "port": 8017, "status": "●", "category": "Documents", "desc": "Управление счетами"},
    {"id": 18, "name": "calendar-service", "port": 8018, "status": "●", "category": "Productivity", "desc": "Календарь"},
    {"id": 19, "name": "notifications-service", "port": 8019, "status": "●", "category": "Communications", "desc": "Push/Email/SMS"},
    {"id": 20, "name": "goal-tracking", "port": 8020, "status": "●", "category": "Productivity", "desc": "Трекинг целей"},
    {"id": 21, "name": "cost-optimization", "port": 8021, "status": "●", "category": "Financial", "desc": "Оптимизация расходов"},
    {"id": 22, "name": "predictive-analytics", "port": 8022, "status": "●", "category": "Analytics", "desc": "ML предсказания"},
    {"id": 23, "name": "subscription-management", "port": 8023, "status": "●", "category": "Billing", "desc": "Управление подписками"},
    {"id": 24, "name": "payment-gateway", "port": 8024, "status": "●", "category": "Billing", "desc": "Платёжный шлюз"},
    {"id": 25, "name": "localization-service", "port": 8025, "status": "●", "category": "Infrastructure", "desc": "i18n переводы"},
    {"id": 26, "name": "integrations-service", "port": 8026, "status": "●", "category": "Infrastructure", "desc": "Внешние API"},
    {"id": 27, "name": "consent-service", "port": 8027, "status": "●", "category": "Security", "desc": "GDPR согласия"},
    {"id": 28, "name": "customer-success", "port": 8028, "status": "●", "category": "Support", "desc": "Поддержка клиентов"},
    {"id": 29, "name": "graphql-gateway", "port": 4000, "status": "●", "category": "Infrastructure", "desc": "GraphQL Federation"},
    {"id": 30, "name": "tenant-provisioning", "port": 8030, "status": "●", "category": "Core", "desc": "Создание tenant"},
    {"id": 31, "name": "audit-logging", "port": 8031, "status": "●", "category": "Security", "desc": "Аудит действий"},
    {"id": 32, "name": "recommendation-engine", "port": 8032, "status": "●", "category": "AI", "desc": "ML рекомендации"},
    {"id": 33, "name": "nginx-gateway", "port": 8000, "status": "●", "category": "Infrastructure", "desc": "API Gateway"}
]

NAVBAR = """
<nav class="navbar">
    <div class="logo">🚀 SelfMonitor</div>
    <div class="nav-links">
        <a href="/" class="nav-link">🏠 Главная</a>
        <a href="/dashboard" class="nav-link">📊 Dashboard</a>
        <a href="/architecture" class="nav-link">🏗️ Архитектура</a>
        <a href="/guide" class="nav-link">📖 Руководство</a>
        <a href="/docs" class="nav-link">📚 API</a>
    </div>
</nav>
"""

BASE_STYLE = """
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
    .nav-links { display: flex; gap: 15px; flex-wrap: wrap; }
    .nav-link {
        color: #333;
        text-decoration: none;
        padding: 8px 16px;
        border-radius: 8px;
        transition: all 0.3s;
        font-weight: 500;
        font-size: 0.95em;
    }
    .nav-link:hover {
        background: #667eea;
        color: white;
        transform: translateY(-2px);
    }
    .container { max-width: 1400px; margin: 0 auto; }
    .content-box {
        background: white;
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        animation: fadeIn 0.6s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    h1 {
        font-size: 2.5em;
        margin-bottom: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    h2 { color: #667eea; margin: 30px 0 15px; font-size: 1.8em; }
    h3 { color: #764ba2; margin: 20px 0 10px; font-size: 1.3em; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    """Main page with menu"""
    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SelfMonitor - Главная</title>
        {BASE_STYLE}
        <style>
            .menu-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 25px;
                margin-top: 30px;
            }}
            .menu-card {{
                background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
                border-radius: 15px;
                padding: 30px;
                text-decoration: none;
                color: #333;
                transition: all 0.3s;
                border: 2px solid #e5e7eb;
                display: block;
            }}
            .menu-card:hover {{
                transform: translateY(-8px);
                box-shadow: 0 15px 40px rgba(102, 126, 234, 0.3);
                border-color: #667eea;
            }}
            .card-icon {{ font-size: 3em; margin-bottom: 15px; }}
            .card-title {{ font-size: 1.5em; font-weight: bold; color: #667eea; margin-bottom: 10px; }}
            .card-desc {{ color: #6b7280; line-height: 1.6; }}
            .stat-row {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-box {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
            }}
            .stat-num {{ font-size: 2.5em; font-weight: bold; }}
            .stat-label {{ font-size: 0.9em; opacity: 0.9; margin-top: 5px; }}
        </style>
    </head>
    <body>
        {NAVBAR}
        <div class="container">
            <div class="content-box">
                <h1>🚀 Self Monitor FinTech Platform</h1>
                <p style="font-size: 1.2em; color: #6b7280; margin-bottom: 25px;">
                    Полнофункциональная платформа для самозанятых. 33 микросервиса, AI-powered аналитика, автоматизация финансов.
                </p>
                
                <div class="stat-row">
                    <div class="stat-box">
                        <div class="stat-num">33</div>
                        <div class="stat-label">Микросервисов</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">32</div>
                        <div class="stat-label">Активны</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">97%</div>
                        <div class="stat-label">Uptime</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">AI</div>
                        <div class="stat-label">Powered</div>
                    </div>
                </div>
                
                <div class="menu-grid">
                    <a href="/dashboard" class="menu-card">
                        <div class="card-icon">📊</div>
                        <div class="card-title">Dashboard</div>
                        <div class="card-desc">Мониторинг всех 33 микросервисов. Статус, производительность, доступность каждого сервиса в реальном времени.</div>
                    </a>
                    
                    <a href="/architecture" class="menu-card">
                        <div class="card-icon">🏗️</div>
                        <div class="card-title">Архитектура</div>
                        <div class="card-desc">Интерактивная карта архитектуры. Связи между сервисами, потоки данных, технологический стек.</div>
                    </a>
                    
                    <a href="/guide" class="menu-card">
                        <div class="card-icon">📖</div>
                        <div class="card-title">Руководство</div>
                        <div class="card-desc">Пошаговая инструкция по использованию. Как работает каждый модуль и как использовать их вместе.</div>
                    </a>
                    
                    <a href="/api/profile" class="menu-card">
                        <div class="card-icon">👤</div>
                        <div class="card-title">Профиль</div>
                        <div class="card-desc">Управление профилем пользователя, настройки, subscription tier, персональные данные.</div>
                    </a>
                    
                    <a href="/api/transactions" class="menu-card">
                        <div class="card-icon">💰</div>
                        <div class="card-title">Транзакции</div>
                        <div class="card-desc">Финансовые операции, автоматическая категоризация, интеграция с банковскими API.</div>
                    </a>
                    
                    <a href="/api/analytics" class="menu-card">
                        <div class="card-icon">📈</div>
                        <div class="card-title">Аналитика</div>
                        <div class="card-desc">Финансовая аналитика, доходы/расходы, тренды, ML-прогнозы на основе истории.</div>
                    </a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard with all 33 microservices"""
    services_html = ""
    categories = {}
    
    for svc in SERVICES:
        cat = svc["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(svc)
    
    for cat, svcs in sorted(categories.items()):
        services_html += f'<h3 style="margin-top: 30px; color: #764ba2;">📦 {cat} ({len(svcs)} сервисов)</h3>'
        services_html += '<div class="service-grid">'
        for svc in svcs:
            status_color = "#10b981" if svc["status"] == "●" else "#f59e0b"
            services_html += f"""
            <div class="service-card">
                <div class="service-header">
                    <span class="service-status" style="color: {status_color};">{svc["status"]}</span>
                    <span class="service-port">:{svc["port"]}</span>
                </div>
                <div class="service-name">{svc["name"]}</div>
                <div class="service-desc">{svc["desc"]}</div>
            </div>
            """
        services_html += '</div>'
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - 33 Микросервиса</title>
        {BASE_STYLE}
        <style>
            .service-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }}
            .service-card {{
                background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 15px;
                transition: all 0.3s;
            }}
            .service-card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.2);
                border-color: #667eea;
            }}
            .service-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .service-status {{ font-size: 1.5em; }}
            .service-port {{
                background: #e5e7eb;
                padding: 4px 10px;
                border-radius: 5px;
                font-size: 0.85em;
                font-weight: 600;
                color: #6b7280;
            }}
            .service-name {{
                font-size: 1.1em;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 8px;
            }}
            .service-desc {{
                font-size: 0.9em;
                color: #6b7280;
                line-height: 1.4;
            }}
        </style>
    </head>
    <body>
        {NAVBAR}
        <div class="container">
            <div class="content-box">
                <h1>📊 Dashboard - Мониторинг Микросервисов</h1>
                <p style="color: #6b7280; margin-bottom: 20px;">
                    Статус всех 33 микросервисов платформы SelfMonitor. 
                    <span style="color: #10b981; font-weight: bold;">● Работает</span> | 
                    <span style="color: #f59e0b; font-weight: bold;">◐ Деградирован</span>
                </p>
                {services_html}
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/architecture", response_class=HTMLResponse)
async def architecture():
    """Architecture visualization"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Архитектура Платформы</title>
        {BASE_STYLE}
        <style>
            .layer {{ margin: 30px 0; }}
            .layer-title {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                font-size: 1.3em;
                font-weight: bold;
                margin-bottom: 15px;
            }}
            .layer-items {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 12px;
            }}
            .layer-item {{
                background: #f9fafb;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                font-weight: 500;
                color: #333;
                transition: all 0.3s;
            }}
            .layer-item:hover {{
                border-color: #667eea;
                background: white;
                transform: scale(1.05);
            }}
            .flow-arrow {{
                text-align: center;
                font-size: 2em;
                color: #667eea;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        {NAVBAR}
        <div class="container">
            <div class="content-box">
                <h1>🏗️ Архитектура Платформы</h1>
                <p style="color: #6b7280; margin-bottom: 30px;">
                    Многоуровневая микросервисная архитектура с GraphQL Federation, Event-Driven коммуникацией и ML/AI моделями.
                </p>
                
                <div class="layer">
                    <div class="layer-title">🌐 Уровень 1: API Gateway & Frontend</div>
                    <div class="layer-items">
                        <div class="layer-item">nginx-gateway (8000)</div>
                        <div class="layer-item">graphql-gateway (4000)</div>
                        <div class="layer-item">web-portal (Next.js)</div>
                        <div class="layer-item">mobile-app (React Native)</div>
                    </div>
                </div>
                
                <div class="flow-arrow">⬇️</div>
                
                <div class="layer">
                    <div class="layer-title">🔐 Уровень 2: Authentication & Routing</div>
                    <div class="layer-items">
                        <div class="layer-item">auth-service</div>
                        <div class="layer-item">tenant-router</div>
                        <div class="layer-item">consent-service</div>
                    </div>
                </div>
                
                <div class="flow-arrow">⬇️</div>
                
                <div class="layer">
                    <div class="layer-title">💼 Уровень 3: Core Business Services</div>
                    <div class="layer-items">
                        <div class="layer-item">user-profile-service</div>
                        <div class="layer-item">transactions-service</div>
                        <div class="layer-item">banking-connector</div>
                        <div class="layer-item">categorization-service</div>
                        <div class="layer-item">analytics-service</div>
                        <div class="layer-item">invoice-service</div>
                        <div class="layer-item">documents-service</div>
                        <div class="layer-item">payment-gateway</div>
                    </div>
                </div>
                
                <div class="flow-arrow">⬇️</div>
                
                <div class="layer">
                    <div class="layer-title">🤖 Уровень 4: AI & ML Services</div>
                    <div class="layer-items">
                        <div class="layer-item">ai-agent-service</div>
                        <div class="layer-item">advice-service</div>
                        <div class="layer-item">fraud-detection</div>
                        <div class="layer-item">recommendation-engine</div>
                        <div class="layer-item">predictive-analytics</div>
                        <div class="layer-item">qna-service (Weaviate)</div>
                    </div>
                </div>
                
                <div class="flow-arrow">⬇️</div>
                
                <div class="layer">
                    <div class="layer-title">🔧 Уровень 5: Supporting Services</div>
                    <div class="layer-items">
                        <div class="layer-item">notifications-service</div>
                        <div class="layer-item">calendar-service</div>
                        <div class="layer-item">localization-service</div>
                        <div class="layer-item">integrations-service</div>
                        <div class="layer-item">audit-logging</div>
                        <div class="layer-item">customer-success</div>
                    </div>
                </div>
                
                <div class="flow-arrow">⬇️</div>
                
                <div class="layer">
                    <div class="layer-title">💾 Уровень 6: Data Layer</div>
                    <div class="layer-items">
                        <div class="layer-item">PostgreSQL (Multi-tenant)</div>
                        <div class="layer-item">Redis (Cache)</div>
                        <div class="layer-item">Kafka (Events)</div>
                        <div class="layer-item">Weaviate (Vector DB)</div>
                        <div class="layer-item">MLflow (Models)</div>
                    </div>
                </div>
                
                <h2 style="margin-top: 50px;">🔄 Паттерны Коммуникации</h2>
                <div class="layer-items" style="margin-top: 20px;">
                    <div class="layer-item">Синхронные (HTTP/REST)</div>
                    <div class="layer-item">Асинхронные (Kafka Events)</div>
                    <div class="layer-item">GraphQL Federation</div>
                    <div class="layer-item">gRPC (Internal)</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/guide", response_class=HTMLResponse)
async def guide():
    """Usage guide"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Руководство по Использованию</title>
        {BASE_STYLE}
        <style>
            .step {{
                background: #f9fafb;
                border-left: 4px solid #667eea;
                padding: 25px;
                margin: 25px 0;
                border-radius: 8px;
            }}
            .step-num {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 1.2em;
                margin-right: 15px;
            }}
            .step-title {{ font-size: 1.4em; font-weight: bold; color: #333; margin-bottom: 15px; }}
            .step-content {{ color: #6b7280; line-height: 1.8; }}
            ul {{ margin: 15px 0 15px 25px; }}
            li {{ margin: 8px 0; color: #4b5563; }}
            code {{
                background: #e5e7eb;
                padding: 3px 8px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                color: #d6336c;
            }}
        </style>
    </head>
    <body>
        {NAVBAR}
        <div class="container">
            <div class="content-box">
                <h1>📖 Руководство по Использованию</h1>
                <p style="color: #6b7280; margin-bottom: 30px; font-size: 1.1em;">
                    Полное пошаговое руководство по работе с платформой SelfMonitor. Узнайте как синхронизировать модули и правильно использовать систему.
                </p>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">1</span>
                        Регистрация и Аутентификация
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>auth-service</code>, <code>user-profile-service</code>, <code>tenant-provisioning</code></p>
                        <p><strong>Что происходит:</strong></p>
                        <ul>
                            <li>Пользователь регистрируется через <code>auth-service</code> (JWT токены)</li>
                            <li>Создаётся новый tenant через <code>tenant-provisioning</code></li>
                            <li>Создаётся профиль в <code>user-profile-service</code></li>
                            <li>Выделяется изолированная база данных (multi-tenant)</li>
                        </ul>
                        <p><strong>API:</strong> <code>POST /api/auth/register</code>, <code>POST /api/auth/login</code></p>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">2</span>
                        Подключение Банка
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>banking-connector</code>, <code>consent-service</code>, <code>integrations-service</code></p>
                        <p><strong>Последовательность:</strong></p>
                        <ul>
                            <li>Получение согласия GDPR через <code>consent-service</code></li>
                            <li>OAuth подключение к банку в <code>banking-connector</code></li>
                            <li>Синхронизация транзакций (автоматическая каждые 6 часов)</li>
                            <li>Webhook для мгновенных уведомлений о новых транзакциях</li>
                        </ul>
                        <p><strong>Поддерживаемые банки:</strong> Sberbank, Tinkoff, Alfa-Bank (через Open Banking API)</p>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">3</span>
                        Автоматическая Обработка Транзакций
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>transactions-service</code>, <code>categorization-service</code>, <code>fraud-detection</code></p>
                        <p><strong>Flow:</strong></p>
                        <ul>
                            <li><strong>Получение:</strong> Транзакция приходит из банка → <code>transactions-service</code></li>
                            <li><strong>Категоризация:</strong> AI модель в <code>categorization-service</code> определяет категорию</li>
                            <li><strong>Проверка:</strong> <code>fraud-detection</code> анализирует на мошенничество (ML аномальный детектор)</li>
                            <li><strong>Сохранение:</strong> Данные сохраняются в tenant-specific PostgreSQL</li>
                            <li><strong>Event:</strong> Публикуется событие в Kafka для других сервисов</li>
                        </ul>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">4</span>
                        Аналитика и Инсайты
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>analytics-service</code>, <code>business-intelligence</code>, <code>predictive-analytics</code></p>
                        <p><strong>Что считается:</strong></p>
                        <ul>
                            <li><strong>Доходы/Расходы:</strong> Группировка по категориям, периодам</li>
                            <li><strong>Тренды:</strong> ML-анализ исторических данных</li>
                            <li><strong>Прогнозы:</strong> Предсказание будущих расходов на 3 месяца</li>
                            <li><strong>Рекомендации:</strong> <code>recommendation-engine</code> предлагает способы сэкономить</li>
                            <li><strong>Отчёты:</strong> <code>business-intelligence</code> генерирует PDF отчёты</li>
                        </ul>
                        <p><strong>API:</strong> <code>GET /api/analytics</code>, <code>GET /api/analytics/forecast</code></p>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">5</span>
                        AI Финансовые Советы
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>advice-service</code>, <code>ai-agent-service</code>, <code>qna-service</code></p>
                        <p><strong>Возможности:</strong></p>
                        <ul>
                            <li><strong>Вопросы:</strong> "Сколько я трачу на кофе?" → <code>qna-service</code> (Weaviate vector search)</li>
                            <li><strong>Советы:</strong> "Как сэкономить на налогах?" → <code>advice-service</code> (GPT-powered)</li>
                            <li><strong>Автоматизация:</strong> <code>ai-agent-service</code> создаёт задачи в календаре</li>
                            <li><strong>Персонализация:</strong> ML модели учитывают историю пользователя</li>
                        </ul>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">6</span>
                        Налоги и Комплаенс
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>tax-optimization</code>, <code>tax-filing</code>, <code>compliance-service</code></p>
                        <p><strong>Процесс:</strong></p>
                        <ul>
                            <li><strong>Расчёт:</strong> Автоматический расчёт налогов на основе транзакций</li>
                            <li><strong>Оптимизация:</strong> <code>tax-optimization</code> находит возможности для вычетов</li>
                            <li><strong>Подача:</strong> <code>tax-filing</code> генерирует декларации (формат ФНС)</li>
                            <li><strong>Compliance:</strong> <code>compliance-service</code> проверяет соответствие законам</li>
                        </ul>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">7</span>
                        Документы и Счета
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>documents-service</code>, <code>invoice-service</code></p>
                        <p><strong>Функции:</strong></p>
                        <ul>
                            <li>Загрузка и хранение документов (S3-compatible)</li>
                            <li>OCR распознавание текста из чеков</li>
                            <li>Генерация счетов для клиентов</li>
                            <li>Архивирование с соответствием GDPR</li>
                        </ul>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-title">
                        <span class="step-num">8</span>
                        Уведомления и Календарь
                    </div>
                    <div class="step-content">
                        <p><strong>Сервисы:</strong> <code>notifications-service</code>, <code>calendar-service</code>, <code>goal-tracking</code></p>
                        <p><strong>Интеграции:</strong></p>
                        <ul>
                            <li><strong>Push:</strong> Firebase для мобильных уведомлений</li>
                            <li><strong>Email:</strong> SendGrid для важных событий</li>
                            <li><strong>SMS:</strong> Twilio для критических алертов</li>
                            <li><strong>Календарь:</strong> Синхронизация с Google Calendar</li>
                            <li><strong>Цели:</strong> Трекинг финансовых целей с прогрес-барами</li>
                        </ul>
                    </div>
                </div>
                
                <h2 style="margin-top: 50px;">🔗 Как Все Связано</h2>
                <div class="step">
                    <div class="step-content">
                        <p><strong>Event-Driven Architecture (Kafka):</strong></p>
                        <ul>
                            <li>Новая транзакция → <code>transactions-service</code> → Kafka event</li>
                            <li>Слушатели: <code>analytics-service</code>, <code>tax-optimization</code>, <code>fraud-detection</code></li>
                            <li>Каждый сервис обрабатывает событие независимо</li>
                            <li>Никаких синхронных зависимостей между сервисами</li>
                        </ul>
                        
                        <p style="margin-top: 20px;"><strong>GraphQL Federation:</strong></p>
                        <ul>
                            <li><code>graphql-gateway</code> объединяет схемы всех сервисов</li>
                            <li>Один запрос → данные из нескольких микросервисов</li>
                            <li>Пример: <code>query {{ user {{ profile transactions analytics }} }}</code></li>
                        </ul>
                        
                        <p style="margin-top: 20px;"><strong>Мониторинг:</strong></p>
                        <ul>
                            <li><code>audit-logging</code> записывает все действия пользователя</li>
                            <li>OpenTelemetry для distributed tracing</li>
                            <li>Prometheus + Grafana для метрик</li>
                        </ul>
                    </div>
                </div>
                
                <h2 style="margin-top: 50px;">🚀 Быстрый Старт - Типичный Сценарий</h2>
                <div class="step">
                    <div class="step-content">
                        <ol style="line-height: 2;">
                            <li><strong>Регистрация:</strong> <code>POST /api/auth/register</code></li>
                            <li><strong>Вход:</strong> <code>POST /api/auth/login</code> → получаете JWT token</li>
                            <li><strong>Профиль:</strong> <code>GET /api/profile</code> (с Authorization header)</li>
                            <li><strong>Подключить банк:</strong> <code>POST /api/banking/connect</code></li>
                            <li><strong>Дождаться синхронизации:</strong> ~30 секунд</li>
                            <li><strong>Транзакции:</strong> <code>GET /api/transactions</code></li>
                            <li><strong>Аналитика:</strong> <code>GET /api/analytics</code></li>
                            <li><strong>Вопрос AI:</strong> <code>POST /api/ai/ask</code> с телом <code>{{ "question": "Как сэкономить?" }}</code></li>
                        </ol>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/favicon.ico")
async def favicon():
    return Response(content=b"", media_type="image/x-icon")

@app.get("/robots.txt")
async def robots():
    return Response(content="User-agent: *\nDisallow:", media_type="text/plain")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "services_total": 33,
        "services_running": 32,
        "services_degraded": 1,
        "version": "2.0.0"
    }

@app.get("/api/services")
async def get_services():
    """JSON endpoint with all services"""
    return {"services": SERVICES, "total": len(SERVICES)}

@app.get("/api/profile")
async def get_profile():
    return {
        "user_id": "demo-user-001",
        "email": "demo@selfmonitor.io",
        "name": "Demo User",
        "currency": "RUB",
        "timezone": "Europe/Moscow",
        "subscription": "premium"
    }

@app.get("/api/transactions")
async def get_transactions():
    return {
        "total": 2,
        "transactions": [
            {
                "id": "tx-001",
               "amount": 15000.00,
                "currency": "RUB",
                "description": "Оплата за разработку сайта",
                "date": "2026-02-25",
                "category": "Доход от бизнеса",
                "type": "income"
            },
            {
                "id": "tx-002",
                "amount": -2340.50,
                "currency": "RUB",
                "description": "Аренда офиса",
                "date": "2026-02-20",
                "category": "Бизнес расходы",
                "type": "expense"
            }
        ]
    }

@app.get("/api/analytics")
async def get_analytics():
    return {
        "period": "Февраль 2026",
        "total_income": 145000.00,
        "total_expenses": 67340.50,
        "net_profit": 77659.50,
        "profit_margin": "53.6%",
        "expense_categories": {
            "Программное обеспечение": 12450.00,
            "Офис": 28900.00,
            "Маркетинг": 15800.00,
            "Профуслуги": 10190.50
        },
        "ml_forecast": {
            "next_month_income": 152000.00,
            "next_month_expenses": 69000.00,
            "confidence": "87%"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 SelfMonitor FinTech Platform - Full Demo")
    print("=" * 60)
    print("\n📍 Доступно по адресам:")
    print(f"   http://localhost:8000         - Главная с меню")
    print(f"   http://localhost:8000/dashboard    - 33 микросервиса")
    print(f"   http://localhost:8000/architecture - Архитектура")
    print(f"   http://localhost:8000/guide        - Руководство")
    print(f"   http://localhost:8000/docs         - API Swagger UI")
    print("\n⚡ Нажмите CTRL+C для остановки\n")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, ws="none")
