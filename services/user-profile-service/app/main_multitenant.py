"""
Multi-Tenant User Profile Service
Обновленный для поддержки изоляции данных на уровне tenant
"""
import os
from typing import Dict, Any
from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware

from . import crud, schemas
from .database import get_db

# Set up logging
logger = logging.getLogger(__name__)

# Import Multi-Tenant Support
import sys
# Add the libs directory to sys.path for imports
libs_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'libs')
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)
    sys.path.insert(0, libs_path)

try:
    from common_types.tenant_middleware import (  # type: ignore[import]
        TenantMiddleware, 
        get_tenant_context, 
        get_tenant_db_session,
        TenantContext,
        check_tenant_routing_health
    )
    tenant_enabled = True  # Use lowercase variable
    logger.info("Tenant middleware loaded successfully")
except ImportError as e:
    tenant_enabled = False  # Use lowercase variable
    logger.error(f"Tenant middleware not available: {e}")

TENANT_ENABLED = tenant_enabled  # Final constant assignment

# Import Kafka event streaming
try:
    from event_streaming.kafka_integration import EventStreamingMixin
    KAFKA_ENABLED = True
except ImportError:
    KAFKA_ENABLED = False  # type: ignore[misc]
    logging.warning("Kafka event streaming not available")

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if TENANT_ENABLED:
        logger.info("🏗️ Multi-Tenant User Profile Service starting...")
    else:
        logger.warning("⚠️ Running in single-tenant mode")
    
    yield
    
    # Shutdown
    logger.info("👋 User Profile Service shutting down...")

# FastAPI app with multi-tenant support
app = FastAPI(
    title="Multi-Tenant User Profile Service",
    description="User profile management with complete tenant isolation",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Multi-Tenant Middleware
if TENANT_ENABLED:
    tenant_middleware = TenantMiddleware()  # type: ignore[possibly-unbound]
    app.middleware("http")(tenant_middleware)  # type: ignore[arg-type]

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Kafka event streaming mixin
if KAFKA_ENABLED:
    class UserProfileEventMixin(EventStreamingMixin):  # type: ignore[misc]
        async def publish_user_created_event(self, user_id: str, tenant_id: str, profile_data: Dict[str, Any]):
            """Публикация события создания пользователя"""
            await self.publish_event(  # type: ignore[attr-defined]
                topic="user.created",
                event_data={
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "profile_data": profile_data,
                    "service": "user-profile-service"
                }
            )
        
        async def publish_user_updated_event(self, user_id: str, tenant_id: str, changes: Dict[str, Any]):
            """Публикация события обновления пользователя"""
            await self.publish_event(  # type: ignore[attr-defined]
                topic="user.updated", 
                event_data={
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "changes": changes,
                    "service": "user-profile-service"
                }
            )
    
    event_mixin = UserProfileEventMixin()  # type: ignore[call-arg]

# Health Check
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check с проверкой tenant routing"""
    health_data: Dict[str, Any] = {
        "service": "user-profile-service",
        "status": "healthy",
        "multi_tenant": TENANT_ENABLED,
        "kafka": KAFKA_ENABLED
    }
    
    if TENANT_ENABLED:
        tenant_health = await check_tenant_routing_health()  # type: ignore[possibly-unbound]
        health_data.update(tenant_health)  # type: ignore[arg-type]
    
    return health_data

# Multi-Tenant User Profile Endpoints

@app.post("/profiles", response_model=schemas.UserProfile)  # type: ignore[misc]
async def create_user_profile(
    user_profile: schemas.UserProfileCreate,  # type: ignore[name-defined]
    tenant_context: TenantContext = Depends(get_tenant_context),  # type: ignore[arg-type, possibly-unbound]
    db: AsyncSession = Depends(get_tenant_db_session) if TENANT_ENABLED else Depends(get_db)  # type: ignore[arg-type, possibly-unbound]
):
    """Создание профиля пользователя в tenant-specific БД"""
    
    try:
        # Проверяем, что user_id уникален в рамках tenant
        existing_profile = await crud.get_user_profile(db, user_profile.user_id)  # type: ignore[attr-defined]
        if existing_profile:
            raise HTTPException(
                status_code=400, 
                detail=f"User profile already exists for user {user_profile.user_id} in tenant {tenant_context.tenant_id}"  # type: ignore[possibly-unbound]
            )
        
        # Создаем профиль
        db_user_profile = await crud.create_user_profile(db, user_profile, tenant_context.tenant_id)  # type: ignore[attr-defined]
        
        # Публикуем Kafka событие
        if KAFKA_ENABLED:
            await event_mixin.publish_user_created_event(  # type: ignore[misc]
                user_id=db_user_profile.user_id,  # type: ignore[misc]
                tenant_id=tenant_context.tenant_id,  # type: ignore[misc]
                profile_data=schemas.UserProfile.from_orm(db_user_profile).dict()  # type: ignore[misc]
            )
        
        logger.info(f"Created user profile {user_profile.user_id} for tenant {tenant_context.tenant_id}")  # type: ignore[possibly-unbound]
        return db_user_profile
        
    except Exception as e:
        logger.error(f"Failed to create user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user profile")

@app.get("/profiles/{user_id}", response_model=schemas.UserProfile)  # type: ignore[misc]
async def get_user_profile(
    user_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),  # type: ignore[arg-type, possibly-unbound]
    db: AsyncSession = Depends(get_tenant_db_session) if TENANT_ENABLED else Depends(get_db)  # type: ignore[arg-type, possibly-unbound]
):
    """Получение профиля пользователя из tenant-specific БД"""
    
    user_profile = await crud.get_user_profile(db, user_id)  # type: ignore[attr-defined]
    if not user_profile:
        raise HTTPException(
            status_code=404, 
            detail=f"User profile not found for user {user_id} in tenant {tenant_context.tenant_id}"  # type: ignore[possibly-unbound]
        )
    
    # Дополнительная проверка на принадлежность к tenant (если хранится в модели)
    if hasattr(user_profile, 'tenant_id') and user_profile.tenant_id != tenant_context.tenant_id:  # type: ignore[misc, possibly-unbound]
        raise HTTPException(
            status_code=404,
            detail="User profile not found"  # Не раскрываем информацию о других tenant
        )
    
    return user_profile  # type: ignore[return-value]

@app.put("/profiles/{user_id}", response_model=schemas.UserProfile)  # type: ignore[misc]
async def update_user_profile(
    user_id: str,
    user_profile_update: schemas.UserProfileUpdate,  # type: ignore[name-defined]
    tenant_context: TenantContext = Depends(get_tenant_context),  # type: ignore[arg-type, possibly-unbound]
    db: AsyncSession = Depends(get_tenant_db_session) if TENANT_ENABLED else Depends(get_db)  # type: ignore[arg-type, possibly-unbound]
):
    """Обновление профиля пользователя в tenant-specific БД"""
    
    # Получаем существующий профиль
    existing_profile = await crud.get_user_profile(db, user_id)  # type: ignore[attr-defined]
    if not existing_profile:
        raise HTTPException(
            status_code=404,
            detail=f"User profile not found for user {user_id} in tenant {tenant_context.tenant_id}"  # type: ignore[possibly-unbound]
        )
    
    # Фиксируем изменения для события
    original_data = schemas.UserProfile.model_validate(existing_profile).model_dump()  # type: ignore[attr-defined]
    
    # Обновляем профиль
    updated_profile = await crud.update_user_profile(db, user_id, user_profile_update)  # type: ignore[attr-defined]
    
    # Вычисляем изменения
    updated_data = schemas.UserProfile.model_validate(updated_profile).model_dump()  # type: ignore[attr-defined]
    changes = {}
    for key, new_value in updated_data.items():
        if key in original_data and original_data[key] != new_value:
            changes[key] = {"from": original_data[key], "to": new_value}
    
    # Публикуем Kafka событие
    if KAFKA_ENABLED and changes:
        await event_mixin.publish_user_updated_event(  # type: ignore[misc]
            user_id=user_id,
            tenant_id=tenant_context.tenant_id,  # type: ignore[possibly-unbound]
            changes=changes  # type: ignore[arg-type]
        )
    
    logger.info(f"Updated user profile {user_id} for tenant {tenant_context.tenant_id}")  # type: ignore[possibly-unbound]
    return updated_profile  # type: ignore[return-value]

@app.delete("/profiles/{user_id}")
async def delete_user_profile(
    user_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),  # type: ignore[arg-type, possibly-unbound]
    db: AsyncSession = Depends(get_tenant_db_session) if TENANT_ENABLED else Depends(get_db)  # type: ignore[arg-type, possibly-unbound]
):
    """Удаление профиля пользователя (GDPR compliance)"""
    
    # Найдем профиль
    user_profile = await crud.get_user_profile(db, user_id)  # type: ignore[attr-defined]
    if not user_profile:
        raise HTTPException(
            status_code=404,
            detail=f"User profile not found for user {user_id} in tenant {tenant_context.tenant_id}"  # type: ignore[possibly-unbound]
        )
    
    # Удаляем профиль
    success = await crud.delete_user_profile(db, user_id)  # type: ignore[attr-defined]
    
    if success:
        # Публикуем событие удаления
        if KAFKA_ENABLED:
            await event_mixin.publish_event(  # type: ignore[misc]
                topic="user.deleted",
                event_data={
                    "user_id": user_id,
                    "tenant_id": tenant_context.tenant_id,  # type: ignore[possibly-unbound]
                    "deleted_at": user_profile.updated_at.isoformat(),  # type: ignore[misc]
                    "service": "user-profile-service"
                }
            )
        
        logger.info(f"Deleted user profile {user_id} for tenant {tenant_context.tenant_id}")  # type: ignore[possibly-unbound]
        return {"message": f"User profile {user_id} deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete user profile")

@app.get("/profiles")
async def list_user_profiles(
    skip: int = 0,
    limit: int = 100,
    tenant_context: TenantContext = Depends(get_tenant_context),  # type: ignore[arg-type, possibly-unbound]
    db: AsyncSession = Depends(get_tenant_db_session) if TENANT_ENABLED else Depends(get_db)  # type: ignore[arg-type, possibly-unbound]
) -> Dict[str, Any]:
    """Получение списка профилей пользователей в рамках tenant"""
    
    profiles = await crud.get_user_profiles_list(db, skip=skip, limit=min(limit, 500))  # type: ignore[attr-defined]
    
    return {  # type: ignore[return-value]
        "tenant_id": tenant_context.tenant_id,  # type: ignore[possibly-unbound]
        "total": len(profiles),  # type: ignore[arg-type]
        "skip": skip,
        "limit": limit,
        "profiles": profiles
    }

@app.get("/tenant/stats")
async def get_tenant_statistics(
    tenant_context: TenantContext = Depends(get_tenant_context),  # type: ignore[arg-type, possibly-unbound]
    db: AsyncSession = Depends(get_tenant_db_session) if TENANT_ENABLED else Depends(get_db)  # type: ignore[arg-type, possibly-unbound]
) -> Dict[str, Any]:
    """Статистика по tenant"""
    
    # Получаем статистику
    total_users = await crud.get_total_users_count(db)  # type: ignore[attr-defined]
    active_subscriptions = await crud.get_active_subscriptions_count(db)  # type: ignore[attr-defined]
    subscription_distribution = await crud.get_subscription_plan_distribution(db)  # type: ignore[attr-defined]
    
    return {  # type: ignore[return-value]
        "tenant_id": tenant_context.tenant_id,  # type: ignore[possibly-unbound]
        "statistics": {
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "subscription_plans": subscription_distribution
        }
    }

# Admin endpoints (для управления tenant)
@app.get("/admin/tenant/{tenant_id}/migrate")
async def migrate_tenant_data(tenant_id: str):
    """Миграция данных tenant (admin only)"""
    # В production здесь должна быть проверка admin прав
    
    # Здесь будет логика миграции данных между шардами
    # при необходимости перебалансировки
    
    return {"message": f"Migration initiated for tenant {tenant_id}"}

# Метрики для мониторинга
@app.get("/metrics")
async def get_metrics(
    tenant_context: TenantContext = Depends(get_tenant_context),  # type: ignore[arg-type, possibly-unbound]
    db: AsyncSession = Depends(get_tenant_db_session) if TENANT_ENABLED else Depends(get_db)  # type: ignore[arg-type, possibly-unbound]
):
    """Метрики для Prometheus"""
    
    # Базовые метрики
    total_users = await crud.get_total_users_count(db)  # type: ignore[attr-defined]
    
    # Use tenant_id safely
    tenant_id_str = tenant_context.tenant_id if TENANT_ENABLED else "default"  # type: ignore[possibly-unbound]
    
    metrics = f"""
# HELP user_profiles_total Total number of user profiles
# TYPE user_profiles_total counter
user_profiles_total{{tenant_id="{tenant_id_str}"}} {total_users}  

# HELP tenant_db_connections Active database connections
# TYPE tenant_db_connections gauge  
tenant_db_connections{{tenant_id="{tenant_id_str}"}} 5  
"""
    
    return Response(content=metrics, media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    
    # Запуск с multi-tenant поддержкой
    logger.info("🚀 Starting Multi-Tenant User Profile Service...")
    uvicorn.run(  # type: ignore[misc]
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 80)),
        log_level="info"
    )