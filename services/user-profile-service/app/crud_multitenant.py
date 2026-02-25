"""
Multi-Tenant CRUD Operations
CRUD операции с полной поддержкой tenant isolation
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, text
import json
import uuid
from datetime import datetime
import logging

from . import schemas
from .models_multitenant import UserProfile, UserProfileAudit, TenantSettings

logger = logging.getLogger(__name__)

class MultiTenantCRUD:
    """Базовый класс для multi-tenant CRUD операций"""
    
    @staticmethod
    async def set_tenant_context(db: AsyncSession, tenant_id: str):
        """Установка tenant контекста для Row Level Security"""
        try:
            await db.execute(text(f"SELECT set_tenant_id('{tenant_id}')"))
            logger.debug(f"Set tenant context to {tenant_id}")
        except Exception as e:
            logger.warning(f"Could not set tenant context: {e}")

# User Profile CRUD Operations

async def create_user_profile(
    db: AsyncSession, 
    user_profile: schemas.UserProfileCreate, 
    tenant_id: str,
    created_by: Optional[str] = None
) -> UserProfile:
    """Создание профиля пользователя в tenant-specific БД"""
    
    # Устанавливаем tenant context
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    # Создаем объект профиля
    db_user_profile = UserProfile(
        user_id=user_profile.user_id,
        tenant_id=tenant_id,
        first_name=user_profile.first_name,
        last_name=user_profile.last_name,
        email=user_profile.email,
        phone=user_profile.phone,
        date_of_birth=user_profile.date_of_birth,
        subscription_plan=user_profile.subscription_plan or "free",
        subscription_status=user_profile.subscription_status or "active",
        billing_cycle=user_profile.billing_cycle or "monthly",
        timezone=user_profile.timezone or "UTC",
        language=user_profile.language or "en",
        currency=user_profile.currency or "USD",
        created_by=created_by
    )
    
    db.add(db_user_profile)
    
    try:
        await db.commit()
        await db.refresh(db_user_profile)
        
        # Записываем в audit log
        await _create_audit_record(
            db, tenant_id, user_profile.user_id, "INSERT", 
            new_values=_user_profile_to_dict(db_user_profile),
            changed_by=created_by
        )
        
        logger.info(f"Created user profile {user_profile.user_id} for tenant {tenant_id}")
        return db_user_profile
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create user profile: {e}")
        raise

async def get_user_profile(db: AsyncSession, user_id: str, tenant_id: str) -> Optional[UserProfile]:
    """Получение профиля пользователя по ID в рамках tenant"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    stmt = select(UserProfile).where(
        and_(UserProfile.user_id == user_id, UserProfile.tenant_id == tenant_id)
    )
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_profile_by_email(db: AsyncSession, email: str, tenant_id: str) -> Optional[UserProfile]:
    """Получение профиля пользователя по email в рамках tenant"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    stmt = select(UserProfile).where(
        and_(UserProfile.email == email, UserProfile.tenant_id == tenant_id)
    )
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_profiles_list(
    db: AsyncSession, 
    tenant_id: str,
    skip: int = 0, 
    limit: int = 100,
    subscription_plan: Optional[str] = None,
    subscription_status: Optional[str] = None
) -> List[UserProfile]:
    """Получение списка профилей пользователей в рамках tenant"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    stmt = select(UserProfile).where(UserProfile.tenant_id == tenant_id)
    
    # Фильтры
    if subscription_plan:
        stmt = stmt.where(UserProfile.subscription_plan == subscription_plan)
    if subscription_status:
        stmt = stmt.where(UserProfile.subscription_status == subscription_status)
    
    # Пагинация
    stmt = stmt.offset(skip).limit(limit).order_by(UserProfile.created_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())  # type: ignore[return-value]

async def update_user_profile(
    db: AsyncSession, 
    user_id: str, 
    tenant_id: str,
    user_profile_update: schemas.UserProfileUpdate,
    updated_by: Optional[str] = None
) -> Optional[UserProfile]:
    """Обновление профиля пользователя с audit trail"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    # Получаем текущий профиль
    current_profile = await get_user_profile(db, user_id, tenant_id)
    if not current_profile:
        return None
    
    # Сохраняем старые значения для audit
    old_values = _user_profile_to_dict(current_profile)
    
    # Подготавливаем данные для обновления
    update_data = user_profile_update.model_dump(exclude_unset=True)
    if update_data:
        from datetime import timezone as dt_timezone
        update_data['updated_at'] = datetime.now(dt_timezone.utc)
        
        # Выполняем обновление
        stmt = update(UserProfile).where(
            and_(UserProfile.user_id == user_id, UserProfile.tenant_id == tenant_id)
        ).values(**update_data)
        
        await db.execute(stmt)
        await db.commit()
        
        # Получаем обновленный профиль
        updated_profile = await get_user_profile(db, user_id, tenant_id)
        new_values = _user_profile_to_dict(updated_profile)
        
        # Находим измененные поля
        changed_fields: List[str] = []
        changes = {}
        for field, new_value in new_values.items():
            if field in old_values and old_values[field] != new_value:
                changed_fields.append(field)  # type: ignore[arg-type]
                changes[field] = {"from": old_values[field], "to": new_value}
        
        # Записываем в audit log
        if changed_fields:
            await _create_audit_record(
                db, tenant_id, user_id, "UPDATE",
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields,
                changed_by=updated_by
            )
        
        logger.info(f"Updated user profile {user_id} for tenant {tenant_id}, fields: {changed_fields}")
        return updated_profile
        
    return current_profile

async def delete_user_profile(
    db: AsyncSession, 
    user_id: str, 
    tenant_id: str,
    deleted_by: Optional[str] = None
) -> bool:
    """Удаление профиля пользователя (GDPR compliance)"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    # Получаем профиль для audit
    user_profile = await get_user_profile(db, user_id, tenant_id)
    if not user_profile:
        return False
    
    old_values = _user_profile_to_dict(user_profile)
    
    try:
        # Записываем в audit log перед удалением
        await _create_audit_record(
            db, tenant_id, user_id, "DELETE",
            old_values=old_values,
            changed_by=deleted_by
        )
        
        # Удаляем профиль
        stmt = delete(UserProfile).where(
            and_(UserProfile.user_id == user_id, UserProfile.tenant_id == tenant_id)
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        success = result.rowcount > 0  # type: ignore[attr-defined]
        if success:
            logger.info(f"Deleted user profile {user_id} for tenant {tenant_id}")
        
        return success  # type: ignore[return-value]
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete user profile {user_id}: {e}")
        return False

# Statistics and Analytics

async def get_total_users_count(db: AsyncSession, tenant_id: str) -> int:
    """Общее количество пользователей в tenant"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    stmt = select(func.count(UserProfile.user_id)).where(UserProfile.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalar() or 0

async def get_active_subscriptions_count(db: AsyncSession, tenant_id: str) -> int:
    """Количество активных подписок в tenant"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    stmt = select(func.count(UserProfile.user_id)).where(
        and_(
            UserProfile.tenant_id == tenant_id,
            UserProfile.subscription_status == "active"
        )
    )
    result = await db.execute(stmt)
    return result.scalar() or 0

async def get_subscription_plan_distribution(db: AsyncSession, tenant_id: str) -> Dict[str, int]:
    """Распределение пользователей по планам подписки"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    stmt = select(
        UserProfile.subscription_plan,
        func.count(UserProfile.user_id).label('count')
    ).where(
        UserProfile.tenant_id == tenant_id
    ).group_by(UserProfile.subscription_plan)
    
    result = await db.execute(stmt)
    return {str(row.subscription_plan): int(row.count) for row in result}  # type: ignore[misc]

async def get_user_growth_stats(db: AsyncSession, tenant_id: str, days: int = 30) -> Dict[str, Any]:
    """Статистика роста пользователей за period"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    from datetime import datetime, timedelta
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Новые пользователи за период
    stmt_new = select(func.count(UserProfile.user_id)).where(
        and_(
            UserProfile.tenant_id == tenant_id,
            UserProfile.created_at >= start_date
        )
    )
    
    # Активные пользователи (логинились за период)
    stmt_active = select(func.count(UserProfile.user_id)).where(
        and_(
            UserProfile.tenant_id == tenant_id,
            UserProfile.last_login >= start_date
        )
    )
    
    new_users = await db.execute(stmt_new)
    active_users = await db.execute(stmt_active)
    
    return {
        "period_days": days,
        "new_users": new_users.scalar() or 0,
        "active_users": active_users.scalar() or 0,
        "start_date": start_date.isoformat()
    }

# Tenant Settings CRUD

async def get_tenant_settings(db: AsyncSession, tenant_id: str) -> Optional[TenantSettings]:
    """Получение настроек tenant"""
    
    stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_or_update_tenant_settings(
    db: AsyncSession, 
    tenant_id: str, 
    settings: schemas.TenantSettingsUpdate
) -> TenantSettings:
    """Создание или обновление настроек tenant"""
    
    existing = await get_tenant_settings(db, tenant_id)
    
    if existing:
        # Обновляем
        update_data = settings.model_dump(exclude_unset=True)  # type: ignore[attr-defined]
        from datetime import timezone as dt_timezone
        update_data['updated_at'] = datetime.now(dt_timezone.utc)
        
        stmt = update(TenantSettings).where(
            TenantSettings.tenant_id == tenant_id
        ).values(**update_data)
        
        await db.execute(stmt)
        await db.commit()
        
        return await get_tenant_settings(db, tenant_id)
    else:
        # Создаем
        db_settings = TenantSettings(
            tenant_id=tenant_id,
            **settings.model_dump(exclude_unset=True)  # type: ignore[attr-defined]
        )
        
        db.add(db_settings)
        await db.commit()
        await db.refresh(db_settings)
        
        return db_settings

# Audit Operations

async def _create_audit_record(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    operation: str,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    changed_fields: Optional[List[str]] = None,
    changed_by: Optional[str] = None,
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Создание записи в audit log"""
    
    audit_record = UserProfileAudit(
        audit_id=str(uuid.uuid4()),
        user_id=user_id,
        tenant_id=tenant_id,
        operation=operation,
        changed_fields=json.dumps(changed_fields) if changed_fields else None,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        changed_by=changed_by,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(audit_record)
    # Commit будет в основной операции

async def get_user_audit_trail(
    db: AsyncSession, 
    user_id: str, 
    tenant_id: str,
    limit: int = 50
) -> List[UserProfileAudit]:
    """Получение audit trail для пользователя"""
    
    await MultiTenantCRUD.set_tenant_context(db, tenant_id)
    
    stmt = select(UserProfileAudit).where(
        and_(
            UserProfileAudit.user_id == user_id,
            UserProfileAudit.tenant_id == tenant_id
        )
    ).order_by(UserProfileAudit.changed_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())  # type: ignore[return-value]

# Utility Functions

def _user_profile_to_dict(profile: UserProfile) -> Dict[str, Any]:
    """Конвертация UserProfile в dict для audit"""
    return {
        "user_id": profile.user_id,
        "tenant_id": profile.tenant_id,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "phone": profile.phone,
        "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth is not None else None,  # type: ignore[misc]
        "subscription_plan": profile.subscription_plan,
        "subscription_status": profile.subscription_status,
        "billing_cycle": profile.billing_cycle,
        "timezone": profile.timezone,
        "language": profile.language,
        "currency": profile.currency,
        "created_at": profile.created_at.isoformat() if profile.created_at is not None else None,  # type: ignore[misc]
        "updated_at": profile.updated_at.isoformat() if profile.updated_at is not None else None,  # type: ignore[misc]
        "last_login": profile.last_login.isoformat() if profile.last_login is not None else None  # type: ignore[misc]
    }