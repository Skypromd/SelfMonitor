"""
Dependency injection for SelfMonitor Recommendation Engine
"""

from typing import Dict, Any, List

from fastapi import Depends, HTTPException, Request

from app.core.logging import get_logger

logger = get_logger("dependencies")


async def get_recommendation_service(request: Request):  # type: ignore
    """Get recommendation service from app state."""
    try:
        service = getattr(request.app.state, "recommendation_service", None)
        if service is None:
            raise HTTPException(
                status_code=500, 
                detail="Recommendation service not available"
            )
        return service
    except Exception as e:
        logger.error(f"Failed to get recommendation service: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Service temporarily unavailable"
        )


async def get_current_user_id(request: Request) -> str:
    """Extract user ID from request headers or JWT token."""
    # In a real implementation, this would validate JWT token
    # For now, we'll extract from headers
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User authentication required"
        )
    return user_id


async def validate_recommendation_request(request: Request) -> Dict[str, Any]:
    """Validate recommendation request parameters."""
    # Extract and validate request parameters
    try:
        # Get limit parameter with default and validation
        limit = int(request.query_params.get("limit", 10))
        if limit <= 0 or limit > 50:
            raise ValueError("Limit must be between 1 and 50")
        
        # Get recommendation type
        rec_type = request.query_params.get("type", "general")
        valid_types = ["general", "spending", "saving", "investment", "budgeting"]
        if rec_type not in valid_types:
            raise ValueError(f"Invalid recommendation type. Must be one of: {valid_types}")
        
        # Get time horizon
        time_horizon = request.query_params.get("time_horizon", "short_term")
        valid_horizons = ["short_term", "medium_term", "long_term"]
        if time_horizon not in valid_horizons:
            raise ValueError(f"Invalid time horizon. Must be one of: {valid_horizons}")
        
        return {
            "limit": limit,
            "type": rec_type,
            "time_horizon": time_horizon,
            "include_reasoning": request.query_params.get("include_reasoning", "false").lower() == "true",
            "personalization_level": request.query_params.get("personalization_level", "medium")
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error validating recommendation request: {e}")
        raise HTTPException(status_code=400, detail="Invalid request parameters")


class RateLimiter:
    """Simple in-memory rate limiter for recommendations."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests: Dict[str, List[float]] = {}
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit."""
        import time
        
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Clean up old entries
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if req_time > window_start
            ]
        else:
            self.user_requests[user_id] = []
        
        # Check if limit exceeded
        request_count = len(self.user_requests[user_id])
        if request_count >= self.max_requests:
            return False
        
        # Add current request
        self.user_requests[user_id].append(current_time)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(user_id: str = Depends(get_current_user_id)) -> str:
    """Dependency to check rate limiting."""
    if not await rate_limiter.check_rate_limit(user_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    return user_id