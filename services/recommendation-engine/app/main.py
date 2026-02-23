"""
SelfMonitor Real-time Recommendation Engine
Enterprise-grade AI-powered financial recommendation system

Features:
- Real-time personalized recommendations
- Multiple ML model ensemble
- A/B testing framework
- Vector-based similarity search
- Real-time data processing
- Performance monitoring
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app  # type: ignore
import uvicorn  # type: ignore

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import recommendations, health, metrics  # type: ignore
from app.services.recommendation_service import RecommendationService  # type: ignore

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("🚀 Starting SelfMonitor Recommendation Engine...")
    
    # Initialize services
    try:
        # Initialize recommendation service
        recommendation_service = RecommendationService()  # type: ignore
        await recommendation_service.initialize()  # type: ignore
        
        # Store in app state
        app.state.recommendation_service = recommendation_service
        
        logger.info("✅ Recommendation Engine started successfully")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start Recommendation Engine: {e}")
        raise
    finally:
        logger.info("🔄 Shutting down Recommendation Engine...")
        if hasattr(app.state, 'recommendation_service'):
            await app.state.recommendation_service.cleanup()  # type: ignore
        logger.info("✅ Recommendation Engine shut down complete")


# Create FastAPI application
app = FastAPI(
    title="SelfMonitor Recommendation Engine",
    description="Enterprise AI-powered real-time financial recommendation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])  # type: ignore
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])  # type: ignore
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])  # type: ignore

# Add Prometheus metrics endpoint 
metrics_app = make_asgi_app()  # type: ignore
app.mount("/metrics", metrics_app)  # type: ignore


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "service": "SelfMonitor Recommendation Engine",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Real-time personalized recommendations",
            "Multi-model ML ensemble",
            "A/B testing framework", 
            "Vector similarity search",
            "Performance monitoring"
        ]
    }


@app.get("/openapi.json")
async def custom_openapi() -> Any:
    """Custom OpenAPI schema."""
    return app.openapi()


if __name__ == "__main__":
    uvicorn.run(  # type: ignore
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )