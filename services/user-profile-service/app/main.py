import logging
import sys
import uuid
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

from . import crud, schemas
from .database import get_db

logger = logging.getLogger(__name__)
KAFKA_ENABLED = False

app = FastAPI(
    title="User Profile Service",
    description="Manages user profile data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.0.248:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()


# --- Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/profiles/me", response_model=schemas.UserProfile)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)
):
    """Retrieves the profile for the currently authenticated user from the database."""
    db_profile = await crud.get_profile_by_user_id(db, user_id=user_id)
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # Emit user profile access event
    if KAFKA_ENABLED and hasattr(app, "emit_event"):
        try:
            await app.emit_event(
                topic="user.events",
                event_type="user_profile_accessed",
                data={
                    "access_type": "profile_view",
                    "profile_completeness": getattr(
                        db_profile, "completeness_score", 0
                    ),
                    "last_updated": getattr(db_profile, "updated_at", "").isoformat()
                    if hasattr(getattr(db_profile, "updated_at", ""), "isoformat")
                    else None,
                    "feature": "profile_management",
                },
                user_id=user_id,
            )

            # Track engagement analytics
            await app.emit_event(
                topic="analytics.events",
                event_type="user_profile_engagement",
                data={
                    "metric_name": "profile_view",
                    "metric_value": 1.0,
                    "engagement_type": "view",
                    "session_data": "profile_access",
                },
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Failed to emit profile access events: {str(e)}")

    return db_profile


@app.put("/profiles/me", response_model=schemas.UserProfile)
async def create_or_update_my_profile(
    profile_update: schemas.UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new profile or updates an existing one for the authenticated user in the database."""
    # Check if profile exists before update
    existing_profile = await crud.get_profile_by_user_id(db, user_id=user_id)
    is_new_profile = existing_profile is None

    db_profile = await crud.create_or_update_profile(
        db, user_id=user_id, profile=profile_update
    )

    # Emit appropriate user profile events
    if KAFKA_ENABLED and hasattr(app, "emit_event"):
        try:
            if is_new_profile:
                # New profile creation
                await app.emit_event(
                    topic="user.events",
                    event_type="user_profile_created",
                    data={
                        "profile_fields": list(
                            profile_update.model_dump(exclude_unset=True).keys()
                        ),
                        "initial_completeness": getattr(
                            db_profile, "completeness_score", 0
                        ),
                        "onboarding_step": "profile_setup",
                        "feature": "user_onboarding",
                    },
                    user_id=user_id,
                    correlation_id=f"profile_creation_{uuid.uuid4()}",
                )

                # Analytics for new user onboarding
                await app.emit_event(
                    topic="analytics.events",
                    event_type="user_onboarding_milestone",
                    data={
                        "metric_name": "profile_creation",
                        "metric_value": 1.0,
                        "milestone": "profile_setup_complete",
                        "fields_completed": len(
                            profile_update.model_dump(exclude_unset=True)
                        ),
                    },
                    user_id=user_id,
                )
            else:
                # Profile update
                updated_fields = profile_update.model_dump(exclude_unset=True)
                await app.emit_event(
                    topic="user.events",
                    event_type="user_profile_updated",
                    data={
                        "updated_fields": list(updated_fields.keys()),
                        "update_count": len(updated_fields),
                        "new_completeness": getattr(
                            db_profile, "completeness_score", 0
                        ),
                        "feature": "profile_management",
                    },
                    user_id=user_id,
                    correlation_id=f"profile_update_{uuid.uuid4()}",
                )

                # Track profile improvement analytics
                await app.emit_event(
                    topic="analytics.events",
                    event_type="user_profile_engagement",
                    data={
                        "metric_name": "profile_update",
                        "metric_value": len(updated_fields),
                        "engagement_type": "update",
                        "fields_modified": list(updated_fields.keys()),
                    },
                    user_id=user_id,
                )

        except Exception as e:
            logger.warning(f"Failed to emit profile update events: {str(e)}")

    return db_profile
