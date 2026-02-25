"""Quick demo server for SelfMonitor Platform"""
from typing import Any
from fastapi import FastAPI
from fastapi.responses import Response

app = FastAPI(
    title="SelfMonitor Demo Server",
    description="Quick demonstration server for SelfMonitor FinTech Platform",
    version="1.0.0"
)

@app.get("/favicon.ico")
async def favicon() -> Response:
    """Return empty favicon to prevent 404 errors"""
    return Response(content=b"", media_type="image/x-icon")

@app.get("/robots.txt")
async def robots() -> Response:
    """Return robots.txt"""
    return Response(content="User-agent: *\nDisallow:", media_type="text/plain")

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "SelfMonitor FinTech Platform",
        "status": "running",
        "version": "1.0.0",
        "message": "Welcome to SelfMonitor! 🚀"
    }

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
