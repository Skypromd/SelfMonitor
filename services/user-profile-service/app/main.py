import os
import uuid
from typing import Annotated
from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import get_db

# Import Kafka event streaming
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'libs'))

try:
    from event_streaming.kafka_integration import EventStreamingMixin
    KAFKA_ENABLED = True
except ImportError:
    KAFKA_ENABLED = False
    logging.warning("Kafka event streaming not available")

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if KAFKA_ENABLED and hasattr(app, 'init_event_streaming'):
        await app.init_event_streaming()
        logger.info("Kafka event streaming initialized")
    
    yield
    
    # Shutdown
    if KAFKA_ENABLED and hasattr(app, 'cleanup_event_streaming'):
        await app.cleanup_event_streaming()
        logger.info("Kafka event streaming cleaned up")

class UserProfileServiceApp(FastAPI, EventStreamingMixin if KAFKA_ENABLED else object):
    """Enhanced User Profile Service with Kafka event streaming"""
    pass

app = UserProfileServiceApp(
    title="SelfMonitor User Profile Service",
    description="Manage user profiles with real-time event streaming",
    version="1.0.0",
    lifespan=lifespan
)

# --- Security ---
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    return user_id

# --- Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/profiles/me", response_model=schemas.UserProfile)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the profile for the currently authenticated user from the database."""
    db_profile = await crud.get_profile_by_user_id(db, user_id=user_id)
    if db_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    # Emit user profile access event
    if KAFKA_ENABLED and hasattr(app, 'emit_event'):
        try:
            await app.emit_event(
                topic="user.events",
                event_type="user_profile_accessed",
                data={
                    "access_type": "profile_view",
                    "profile_completeness": getattr(db_profile, 'completeness_score', 0),
                    "last_updated": getattr(db_profile, 'updated_at', '').isoformat() if hasattr(getattr(db_profile, 'updated_at', ''), 'isoformat') else None,
                    "feature": "profile_management"
                },
                user_id=user_id
            )
            
            # Track engagement analytics
            await app.emit_event(
                topic="analytics.events",
                event_type="user_profile_engagement",
                data={
                    "metric_name": "profile_view",
                    "metric_value": 1.0,
                    "engagement_type": "view",
                    "session_data": "profile_access"
                },
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to emit profile access events: {str(e)}")
    
    return db_profile

@app.put("/profiles/me", response_model=schemas.UserProfile)
async def create_or_update_my_profile(
    profile_update: schemas.UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new profile or updates an existing one for the authenticated user in the database."""
    # Check if profile exists before update
    existing_profile = await crud.get_profile_by_user_id(db, user_id=user_id)
    is_new_profile = existing_profile is None
    
    db_profile = await crud.create_or_update_profile(db, user_id=user_id, profile=profile_update)
    
    # Emit appropriate user profile events
    if KAFKA_ENABLED and hasattr(app, 'emit_event'):
        try:
            if is_new_profile:
                # New profile creation
                await app.emit_event(
                    topic="user.events",
                    event_type="user_profile_created",
                    data={
                        "profile_fields": list(profile_update.dict(exclude_unset=True).keys()),
                        "initial_completeness": getattr(db_profile, 'completeness_score', 0),
                        "onboarding_step": "profile_setup",
                        "feature": "user_onboarding"
                    },
                    user_id=user_id,
                    correlation_id=f"profile_creation_{uuid.uuid4()}"
                )
                
                # Analytics for new user onboarding
                await app.emit_event(
                    topic="analytics.events",
                    event_type="user_onboarding_milestone",
                    data={
                        "metric_name": "profile_creation",
                        "metric_value": 1.0,
                        "milestone": "profile_setup_complete",
                        "fields_completed": len(profile_update.dict(exclude_unset=True))
                    },
                    user_id=user_id
                )
            else:
                # Profile update
                updated_fields = profile_update.dict(exclude_unset=True)
                await app.emit_event(
                    topic="user.events",
                    event_type="user_profile_updated",
                    data={
                        "updated_fields": list(updated_fields.keys()),
                        "update_count": len(updated_fields),
                        "new_completeness": getattr(db_profile, 'completeness_score', 0),
                        "feature": "profile_management"
                    },
                    user_id=user_id,
                    correlation_id=f"profile_update_{uuid.uuid4()}"
                )
                
                # Track profile improvement analytics
                await app.emit_event(
                    topic="analytics.events",
                    event_type="user_profile_engagement",
                    data={
                        "metric_name": "profile_update",
                        "metric_value": len(updated_fields),
                        "engagement_type": "update",
                        "fields_modified": list(updated_fields.keys())
                    },
                    user_id=user_id
                )
            
        except Exception as e:
            logger.warning(f"Failed to emit profile update events: {str(e)}")
    
    return db_profile
