"""
SelfMonitor Demo Web Interface
Простой веб-интерфейс для демонстрации возможностей платформы
"""

from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from typing import List, Dict, Any

app = Flask(__name__)
CORS(app)

# Демо HTML-интерфейс
DEMO_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 SelfMonitor Demo Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 0.5rem;
            font-size: 2.5rem;
        }
        
        .header p {
            color: #7f8c8d;
            font-size: 1.2rem;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card h3 {
            color: #2c3e50;
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }
        
        .stat {
            display: flex;
            justify-content: space-between;
            margin: 1rem 0;
            padding: 0.5rem 0;
            border-bottom: 1px solid #eee;
        }
        
        .stat-label {
            font-weight: 600;
            color: #555;
        }
        
        .stat-value {
            color: #27ae60;
            font-weight: bold;
        }
        
        .negative {
            color: #e74c3c;
        }
        
        .features {
            background: rgba(255, 255, 255, 0.9);
            margin: 2rem 0;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .features h2 {
            color: #2c3e50;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
        }
        
        .feature {
            padding: 1.5rem;
            background: #f8f9fa;
            border-radius: 10px;
            text-align: center;
        }
        
        .feature-icon {
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        
        .cta {
            text-align: center;
            margin: 3rem 0;
        }
        
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        
        .demo-data {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-family: monospace;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .dashboard {
                grid-template-columns: 1fr;
            }
            
            .container {
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 SelfMonitor FinTech Platform</h1>
        <p>Comprehensive Financial Management for Self-Employed Professionals in the UK</p>
    </div>
    
    <div class="container">
        <div class="dashboard">
            <div class="card">
                <h3>📊 Financial Overview</h3>
                <div class="stat">
                    <span class="stat-label">💰 Total Income:</span>
                    <span class="stat-value">£7,500.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">💸 Total Expenses:</span>
                    <span class="stat-value negative">£307.29</span>
                </div>
                <div class="stat">
                    <span class="stat-label">📈 Net Profit:</span>
                    <span class="stat-value">£7,192.71</span>
                </div>
                <div class="stat">
                    <span class="stat-label">🎯 Tax Readiness:</span>
                    <span class="stat-value">85%</span>
                </div>
            </div>
            
            <div class="card">
                <h3>🧮 Tax Calculation</h3>
                <div class="stat">
                    <span class="stat-label">📋 Taxable Profit:</span>
                    <span class="stat-value">£7,192.71</span>
                </div>
                <div class="stat">
                    <span class="stat-label">🏦 Income Tax:</span>
                    <span class="stat-value negative">£0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">🔒 National Insurance:</span>
                    <span class="stat-value negative">£179.4</span>
                </div>
                <div class="stat">
                    <span class="stat-label">💰 Total Tax Liability:</span>
                    <span class="stat-value negative">£179.4</span>
                </div>
                <small style="color: #777;">*Based on UK 2024/25 tax rates</small>
            </div>
            
            <div class="card">
                <h3>📅 Key Deadlines</h3>
                <div class="stat">
                    <span class="stat-label">📄 Self Assessment:</span>
                    <span class="stat-value">31 Jan 2026</span>
                </div>
                <div class="stat">
                    <span class="stat-label">💷 Tax Payment:</span>
                    <span class="stat-value">31 Jan 2026</span>
                </div>
                <div class="stat">
                    <span class="stat-label">📊 VAT Return:</span>
                    <span class="stat-value">7 Apr 2026</span>
                </div>
            </div>
        </div>
        
        <div class="features">
            <h2>🎯 Platform Features</h2>
            <div class="feature-grid">
                <div class="feature">
                    <div class="feature-icon">📱</div>
                    <h4>Mobile App</h4>
                    <p>React Native app with offline support, receipt scanning, and real-time sync</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">🏦</div>
                    <h4>Bank Integration</h4>
                    <p>Open Banking API integration with all major UK banks for automatic transaction import</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <h4>AI Assistant</h4>
                    <p>Smart categorization, expense predictions, and personalized financial advice</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <h4>Real-time Analytics</h4>
                    <p>Interactive dashboards, cash flow forecasting, and business intelligence</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">🔒</div>
                    <h4>Enterprise Security</h4>
                    <p>Bank-grade security with OAuth2, JWT, encryption, and GDPR compliance</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">⚖️</div>
                    <h4>Compliance Suite</h4>
                    <p>Automated HMRC reporting, Making Tax Digital ready, audit trails</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>🏗️ Technical Architecture</h3>
            <div class="stat">
                <span class="stat-label">🔧 Microservices:</span>
                <span class="stat-value">32 Services</span>
            </div>
            <div class="stat">
                <span class="stat-label">🐳 Containerized:</span>
                <span class="stat-value">Docker + Kubernetes</span>
            </div>
            <div class="stat">
                <span class="stat-label">📡 API Gateway:</span>
                <span class="stat-value">GraphQL Federation</span>
            </div>
            <div class="stat">
                <span class="stat-label">📊 Monitoring:</span>
                <span class="stat-value">Prometheus + Grafana</span>
            </div>
            <div class="stat">
                <span class="stat-label">🔍 Tracing:</span>
                <span class="stat-value">OpenTelemetry + Jaeger</span>
            </div>
            <div class="stat">
                <span class="stat-label">🚀 Testing:</span>
                <span class="stat-value">95% Coverage</span>
            </div>
        </div>
        
        <div class="cta">
            <a href="/api/demo" class="btn">🛠️ Explore API Demo</a>
            <a href="/api/docs" class="btn" style="margin-left: 1rem;">📖 API Documentation</a>
        </div>
        
        <div class="demo-data">
            <strong>🔗 Quick API Test:</strong><br>
            GET /api/demo/dashboard - Get financial dashboard<br>
            POST /api/demo/transaction - Add new transaction<br>
            GET /api/demo/tax-calculation - Calculate taxes<br>
            GET /api/demo/ai-insights - AI financial insights
        </div>
    </div>
</body>
</html>
"""

# Демо данные
demo_transactions: List[Dict[str, Any]] = [
    {"amount": 2500.0, "description": "Freelance consulting - Web development", "category": "income", "date": "2026-02-01"},
    {"amount": 1800.0, "description": "Design project - Mobile app", "category": "income", "date": "2026-02-10"},
    {"amount": -45.99, "description": "Adobe Creative Suite subscription", "category": "software", "date": "2026-02-15"},
    {"amount": -89.50, "description": "Coworking space rental", "category": "workspace", "date": "2026-02-16"},
    {"amount": -15.80, "description": "Coffee meeting with client", "category": "meals", "date": "2026-02-20"},
    {"amount": 3200.0, "description": "Monthly retainer - SEO consulting", "category": "income", "date": "2026-02-22"},
    {"amount": -156.00, "description": "Professional development course", "category": "education", "date": "2026-02-24"}
]

@app.route('/')
def home():
    """Главная демо-страница"""
    return render_template_string(DEMO_HTML)

@app.route('/api/demo')
def api_demo():
    """API демо-эндпоинт"""
    return jsonify({
        "message": "🎉 Добро пожаловать в SelfMonitor API Demo!",
        "platform": "SelfMonitor FinTech Platform v2.0",
        "description": "Enterprise-grade financial management for UK self-employed",
        "features": [
            "📊 Real-time financial analytics",
            "🤖 AI-powered insights and recommendations", 
            "💰 Automated UK tax calculations",
            "🏦 Open Banking integration",
            "📱 Mobile app with offline support",
            "🔒 Bank-grade security and compliance"
        ],
        "architecture": {
            "microservices": 32,
            "languages": ["Python", "TypeScript", "React Native"],
            "frameworks": ["FastAPI", "Next.js", "Expo"],
            "databases": ["PostgreSQL", "Redis"],
            "deployment": "Docker + Kubernetes",
            "monitoring": "Prometheus + Grafana + Jaeger"
        },
        "demo_endpoints": {
            "dashboard": "/api/demo/dashboard",
            "transactions": "/api/demo/transactions", 
            "tax_calculation": "/api/demo/tax",
            "ai_insights": "/api/demo/ai-insights",
            "health": "/api/demo/health"
        }
    })

@app.route('/api/demo/dashboard')
def dashboard():
    """Демо дашборд с финансовой статистикой"""
    income = sum(t["amount"] for t in demo_transactions if t["amount"] > 0)
    expenses = abs(sum(t["amount"] for t in demo_transactions if t["amount"] < 0))
    net_profit = income - expenses
    
    return jsonify({
        "financial_overview": {
            "total_income": income,
            "total_expenses": expenses,
            "net_profit": net_profit,
            "tax_readiness_score": 85,
            "total_transactions": len(demo_transactions)
        },
        "upcoming_deadlines": [
            {
                "title": "Self Assessment deadline",
                "date": "2026-01-31",
                "days_remaining": 340,
                "priority": "high"
            },
            {
                "title": "VAT Return Q1",
                "date": "2026-04-07", 
                "days_remaining": 41,
                "priority": "medium"
            }
        ],
        "quick_insights": [
            "💡 Your expense ratio is healthy at 4.1%",
            "📈 Income is 15% higher than last month", 
            "🎯 You're on track to meet your annual targets",
            "💰 Consider increasing pension contributions for tax relief"
        ]
    })

@app.route('/api/demo/transactions')
def transactions():
    """Демо транзакции"""
    return jsonify({
        "transactions": demo_transactions,
        "summary": {
            "total_count": len(demo_transactions),
            "categorized": 7,
            "uncategorized": 0,
            "needs_review": 1
        }
    })

@app.route('/api/demo/tax')
def tax_calculation():
    """Демо расчет налогов для UK"""
    income = sum(t["amount"] for t in demo_transactions if t["amount"] > 0)
    expenses = abs(sum(t["amount"] for t in demo_transactions if t["amount"] < 0))
    profit = income - expenses
    
    # UK tax calculation 2024/25
    personal_allowance = 12570.0
    taxable_income = max(0, profit - personal_allowance)
    
    # Income tax is £0 as profit is below personal allowance
    income_tax = 0.0
    
    # National Insurance Class 2 & 4
    class2_ni = 52 * 3.45 if profit > 6725 else 0  # £3.45/week
    class4_ni = max(0, min(profit, 50270) - 12570) * 0.09  # 9% between £12,570-£50,270
    
    total_ni = class2_ni + class4_ni
    total_tax = income_tax + total_ni
    
    return jsonify({
        "calculation": {
            "gross_profit": profit,
            "personal_allowance": personal_allowance,
            "taxable_income": taxable_income,
            "income_tax": income_tax,
            "national_insurance": {
                "class_2": class2_ni,
                "class_4": class4_ni,
                "total": total_ni
            },
            "total_tax_liability": total_tax,
            "net_income_after_tax": profit - total_tax
        },
        "breakdown": f"Annual profit of £{profit:,.2f} results in £{total_tax:,.2f} total tax liability",
        "advice": [
            "✅ You're well below the higher rate tax threshold",
            "📊 Consider pension contributions for additional tax relief",
            "💼 Maximize business expense deductions",
            "📅 Set aside ~20% for taxes and NI"
        ]
    })

@app.route('/api/demo/ai-insights')
def ai_insights():
    """AI анализ и рекомендации"""
    income = sum(t["amount"] for t in demo_transactions if t["amount"] > 0)
    # expenses - calculated but not used in current implementation
    
    return jsonify({
        "financial_health_score": 92,
        "expense_efficiency": "excellent",
        "ai_recommendations": [
            {
                "category": "Tax Optimization",
                "suggestion": "Your current profit margin of 95.9% is excellent. Consider maximizing pension contributions to reduce tax liability.",
                "potential_savings": "£500-800 annually"
            },
            {
                "category": "Business Growth", 
                "suggestion": "Based on industry trends, freelancers in your sector can increase rates by 15-25%.",
                "potential_impact": "£15,000-25,000 additional annual income"
            },
            {
                "category": "Expense Management",
                "suggestion": "Your expenses are very well controlled. Consider investing in professional development.",
                "recommended_budget": "5-10% of income for skills advancement"
            }
        ],
        "predictions": {
            "monthly_income_forecast": income * 1.12,  # 12% growth predicted
            "annual_tax_estimate": 2200.0,
            "cash_flow_stability": "very_stable"
        },
        "market_insights": [
            "📈 Average freelancer rates in your sector increased 18% this year",
            "💻 AI skills command 40% premium in current market",
            "🎯 83% of client work is moving towards retainer-based models"
        ]
    })

@app.route('/api/demo/health')
def health():
    """Проверка состояния системы"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "services": {
            "api_gateway": "online ✅",
            "transaction_service": "online ✅", 
            "tax_engine": "online ✅",
            "ai_analytics": "online ✅",
            "mobile_app": "online ✅",
            "web_portal": "online ✅"
        },
        "metrics": {
            "uptime": "99.97%",
            "avg_response_time": "45ms",
            "transactions_processed": "2.3M+",
            "active_users": "8,456"
        }
    })

@app.route('/api/docs')
def api_docs():
    """API документация"""
    docs_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SelfMonitor API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 4px 8px; border-radius: 3px; font-weight: bold; }
            .get { background: #61affe; }
            .post { background: #49cc90; }
            pre { background: #f8f8f8; padding: 10px; border-radius: 3px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🚀 SelfMonitor API Documentation</h1>
        <p>Complete REST API for the SelfMonitor Financial Platform</p>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/api/demo</strong>
            <p>Platform overview and feature list</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/api/demo/dashboard</strong>  
            <p>Financial dashboard with income, expenses, and key metrics</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/api/demo/transactions</strong>
            <p>List all transactions with categorization status</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/api/demo/tax</strong>
            <p>UK tax calculation including Income Tax and National Insurance</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/api/demo/ai-insights</strong>
            <p>AI-powered financial analysis and recommendations</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <strong>/api/demo/health</strong>
            <p>System health check and service status</p>
        </div>
        
        <h2>🏗️ Full Platform Architecture</h2>
        <ul>
            <li><strong>32 Microservices:</strong> User management, transactions, analytics, AI, compliance</li>
            <li><strong>GraphQL Gateway:</strong> Unified API endpoint with federation</li>
            <li><strong>Mobile App:</strong> React Native with 21 custom components</li>
            <li><strong>Web Portal:</strong> Next.js with TypeScript</li>
            <li><strong>Infrastructure:</strong> Kubernetes, Docker, Prometheus, Grafana</li>
            <li><strong>Security:</strong> OAuth2, JWT, encryption, GDPR compliant</li>
        </ul>
        
        <p><a href="/">← Back to Demo</a></p>
    </body>
    </html>
    """
    return docs_html

if __name__ == '__main__':
    print("🚀 SelfMonitor Demo Platform Starting...")
    print("📱 Main Interface: http://localhost:5000")
    print("🛠️ API Demo: http://localhost:5000/api/demo")
    print("📖 API Docs: http://localhost:5000/api/docs")
    print("")
    app.run(host='0.0.0.0', port=5000, debug=True)