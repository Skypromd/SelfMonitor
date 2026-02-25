# -*- coding: utf-8 -*-
"""
Simple HTTP Server for SelfMonitor Demo
Uses only Python standard library - no external dependencies
"""

import http.server
import socketserver
import json
import urllib.parse
from datetime import datetime
from typing import Dict, Any

class SelfMonitorHandler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self) -> None:
        # Parse URL
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Set common headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'text/html; charset=utf-8')
        
        if path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self.get_home_page().encode('utf-8'))
            
        elif path == '/api/demo':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.get_demo_data(), ensure_ascii=False).encode('utf-8'))
            
        elif path == '/api/demo/dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.get_dashboard_data(), ensure_ascii=False).encode('utf-8'))
            
        elif path == '/api/demo/tax':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')  
            self.end_headers()
            self.wfile.write(json.dumps(self.get_tax_data(), ensure_ascii=False).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')
    
    def get_home_page(self) -> str:
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SelfMonitor FinTech Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: rgba(255,255,255,0.95);
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header h1 {
            color: #2c3e50;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .header p {
            color: #7f8c8d;
            font-size: 1.3rem;
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.4rem;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            margin: 15px 0;
            padding: 10px 0;
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
        .negative { color: #e74c3c; }
        .features {
            background: rgba(255,255,255,0.9);
            margin: 30px 0;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .feature {
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            text-align: center;
        }
        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 15px;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            margin: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        .demo-links {
            text-align: center;
            margin: 40px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SelfMonitor FinTech Platform</h1>
            <p>Comprehensive Financial Management for UK Self-Employed Professionals</p>
        </div>
        
        <div class="dashboard">
            <div class="card">
                <h3>💰 Financial Overview</h3>
                <div class="stat">
                    <span class="stat-label">Total Income:</span>
                    <span class="stat-value">£7,500.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Expenses:</span>
                    <span class="stat-value negative">£307.29</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Net Profit:</span>
                    <span class="stat-value">£7,192.71</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Tax Readiness:</span>
                    <span class="stat-value">85%</span>
                </div>
            </div>
            
            <div class="card">
                <h3>🧮 UK Tax Calculation</h3>
                <div class="stat">
                    <span class="stat-label">Taxable Profit:</span>
                    <span class="stat-value">£7,192.71</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Income Tax:</span>
                    <span class="stat-value">£0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">National Insurance:</span>
                    <span class="stat-value negative">£179.40</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Tax:</span>
                    <span class="stat-value negative">£179.40</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 Platform Architecture</h3>
                <div class="stat">
                    <span class="stat-label">Microservices:</span>
                    <span class="stat-value">32 Services</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Mobile App:</span>
                    <span class="stat-value">React Native</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Backend:</span>
                    <span class="stat-value">Python FastAPI</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Deployment:</span>
                    <span class="stat-value">Docker + K8s</span>
                </div>
            </div>
        </div>
        
        <div class="features">
            <h2 style="text-align: center; margin-bottom: 20px; color: #2c3e50;">🎯 Key Features</h2>
            <div class="feature-grid">
                <div class="feature">
                    <div class="feature-icon">📱</div>
                    <h4>Mobile App</h4>
                    <p>React Native with offline support and receipt scanning</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🏦</div>
                    <h4>Bank Integration</h4>
                    <p>Open Banking API with all major UK banks</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <h4>AI Assistant</h4>
                    <p>Smart categorization and financial advice</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔒</div>
                    <h4>Security</h4>
                    <p>Bank-grade security with GDPR compliance</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <h4>Analytics</h4>
                    <p>Real-time dashboards and forecasting</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">⚖️</div>
                    <h4>Compliance</h4>
                    <p>HMRC reporting and Making Tax Digital ready</p>
                </div>
            </div>
        </div>
        
        <div class="demo-links">
            <a href="/api/demo" class="btn">🛠️ API Demo</a>
            <a href="/api/demo/dashboard" class="btn">📊 Dashboard Data</a>
            <a href="/api/demo/tax" class="btn">💰 Tax Calculator</a>
        </div>
        
        <div style="background: rgba(255,255,255,0.9); padding: 20px; border-radius: 10px; margin: 20px 0; font-family: monospace; font-size: 0.9rem;">
            <strong>🔗 API Endpoints:</strong><br>
            GET /api/demo - Platform overview<br>
            GET /api/demo/dashboard - Financial dashboard<br>
            GET /api/demo/tax - UK tax calculation
        </div>
    </div>
</body>
</html>
"""
    
    def get_demo_data(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "platform": "SelfMonitor FinTech Platform v2.0",
            "description": "Enterprise financial management for UK self-employed",
            "features": [
                "Real-time financial analytics",
                "AI-powered insights and categorization", 
                "Automated UK tax calculations (HMRC compliant)",
                "Open Banking integration",
                "Mobile app with offline support",
                "Enterprise-grade security"
            ],
            "architecture": {
                "microservices": 32,
                "tech_stack": ["Python FastAPI", "React Native", "Next.js", "TypeScript"],
                "databases": ["PostgreSQL", "Redis"],
                "deployment": "Docker + Kubernetes",
                "monitoring": "Prometheus + Grafana + Jaeger"
            },
            "demo_endpoints": [
                "/api/demo - This overview",
                "/api/demo/dashboard - Financial dashboard",
                "/api/demo/tax - UK tax calculator"  
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        return {
            "financial_overview": {
                "total_income": 7500.00,
                "total_expenses": 307.29,
                "net_profit": 7192.71,
                "tax_readiness_score": 85,
                "profit_margin": 95.9
            },
            "recent_transactions": [
                {"amount": 2500.0, "description": "Freelance consulting", "category": "income", "date": "2026-02-01"},
                {"amount": 1800.0, "description": "Design project", "category": "income", "date": "2026-02-10"},
                {"amount": -45.99, "description": "Adobe subscription", "category": "software", "date": "2026-02-15"},
                {"amount": 3200.0, "description": "Monthly retainer", "category": "income", "date": "2026-02-22"}
            ],
            "insights": [
                "💡 Expense ratio is excellent at 4.1%",
                "📈 Income is 15% higher than last month",
                "🎯 On track to meet annual targets",
                "💰 Consider pension contributions for tax relief"
            ],
            "upcoming_deadlines": [
                {"title": "Self Assessment deadline", "date": "2026-01-31", "priority": "high"},
                {"title": "VAT Return Q1", "date": "2026-04-07", "priority": "medium"}
            ]
        }
    
    def get_tax_data(self) -> Dict[str, Any]:
        # UK Tax calculation for 2024/25
        profit = 7192.71
        personal_allowance = 12570.0
        taxable_income = max(0, profit - personal_allowance)
        
        income_tax = 0.0  # Below personal allowance
        class2_ni = 0.0  # Below £6,725 threshold
        class4_ni = 0.0  # Below £12,570 threshold
        
        return {
            "calculation": {
                "gross_profit": profit,
                "personal_allowance": personal_allowance,
                "taxable_income": taxable_income,
                "income_tax": income_tax,
                "national_insurance": {
                    "class_2": class2_ni,
                    "class_4": class4_ni,
                    "total": class2_ni + class4_ni
                },
                "total_tax_liability": income_tax + class2_ni + class4_ni
            },
            "summary": f"Annual profit of £{profit:,.2f} results in minimal tax liability",
            "advice": [
                "✅ Well below higher rate tax threshold",
                "📊 Consider maximizing business expenses",
                "💼 Pension contributions offer tax relief",
                "📅 Set aside funds for future growth"
            ],
            "rates_info": "Based on UK 2024/25 tax rates and thresholds"
        }

def run_server(port: int = 8080) -> None:
    try:
        with socketserver.TCPServer(("", port), SelfMonitorHandler) as httpd:
            print(f"🚀 SelfMonitor Demo Server starting on http://localhost:{port}")
            print(f"📱 Main interface: http://localhost:{port}")
            print(f"🛠️ API demo: http://localhost:{port}/api/demo")
            print(f"📊 Dashboard: http://localhost:{port}/api/demo/dashboard")
            print("\n✨ Server is ready! Open the URLs above in your browser.")
            print("Press Ctrl+C to stop the server.")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    run_server(8080)