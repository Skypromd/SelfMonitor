
# -*- coding: utf-8 -*-
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return """
    <html>
    <head><title>SelfMonitor Demo Platform</title></head>
    <body style="font-family: Arial; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
        <div style="background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <h1 style="color: #2c3e50; text-align: center;">SelfMonitor FinTech Platform</h1>
            <p style="text-align: center; color: #7f8c8d; font-size: 1.2rem;">Comprehensive Financial Management for UK Self-Employed Professionals</p>
            
            <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h3>Financial Overview Demo</h3>
                <p><strong>Total Income:</strong> �7,500.00</p>
                <p><strong>Total Expenses:</strong> �307.29</p>
                <p><strong>Net Profit:</strong> �7,192.71</p>
                <p><strong>Estimated Tax:</strong> �179.40</p>
            </div>
            
            <div style="margin: 30px 0; padding: 20px; background: #e8f5e8; border-radius: 10px;">
                <h3>Platform Features</h3>
                <ul>
                    <li>Real-time financial analytics</li>
                    <li>AI-powered expense categorization</li>
                    <li>UK tax calculations (HMRC compliant)</li>
                    <li>Mobile app with React Native</li>
                    <li>32 microservices architecture</li>
                    <li>Bank-grade security</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="/api/demo" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; margin: 10px;">API Demo</a>
                <a href="/api/demo/dashboard" style="background: #764ba2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; margin: 10px;">Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/api/demo")
def api_demo():
    return jsonify({
        "status": "success",
        "platform": "SelfMonitor FinTech Platform v2.0",
        "description": "Enterprise financial management for UK self-employed",
        "features": [
            "Real-time financial analytics",
            "AI-powered insights", 
            "Automated UK tax calculations",
            "Open Banking integration",
            "Mobile app support",
            "Enterprise security"
        ],
        "architecture": {
            "microservices": 32,
            "tech_stack": ["Python", "FastAPI", "React Native", "Next.js"],
            "databases": ["PostgreSQL", "Redis"],
            "deployment": "Docker + Kubernetes"
        }
    })

@app.route("/api/demo/dashboard")
def dashboard():
    return jsonify({
        "financial_overview": {
            "total_income": 7500.0,
            "total_expenses": 307.29,
            "net_profit": 7192.71,
            "tax_readiness_score": 85
        },
        "tax_calculation": {
            "taxable_profit": 7192.71,
            "income_tax": 0.0,
            "national_insurance": 179.4,
            "total_tax": 179.4
        },
        "insights": [
            "Expense ratio is excellent at 4.1%",
            "On track to meet annual targets",
            "Consider pension contributions for tax relief"
        ]
    })

if __name__ == "__main__":
    print("Demo server starting on http://localhost:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
