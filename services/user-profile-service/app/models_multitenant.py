"""
Multi-Tenant Database Models
Модели данных с поддержкой tenant изоляции
"""
from sqlalchemy import Column, String, Date, DateTime, Integer, Index, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserProfile(Base):
    """
    Multi-Tenant SQLAlchemy model для user_profiles table
    
    Ключевые особенности:
    - tenant_id для изоляции данных
    - Composite primary key (user_id, tenant_id)
    - Row Level Security готовность
    - Audit fields
    """
    __tablename__ = "user_profiles"

    # Composite primary key для multi-tenancy
    user_id = Column(String, primary_key=True, index=True, nullable=False)
    tenant_id = Column(String, primary_key=True, index=True, nullable=False)
    
    # User data fields
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    
    # Subscription fields
    subscription_plan = Column(String, nullable=False, default="free")
    subscription_status = Column(String, nullable=False, default="active")
    billing_cycle = Column(String, nullable=False, default="monthly")
    current_period_start = Column(Date, nullable=True)
    current_period_end = Column(Date, nullable=True)
    monthly_close_day = Column(Integer, nullable=True, default=1)
    
    # Preferences
    timezone = Column(String, default="UTC")
    language = Column(String, default="en")
    currency = Column(String(3), default="USD")
    
    # Security and compliance
    data_retention_days = Column(Integer, default=2555)  # 7 years default
    gdpr_consent = Column(DateTime(timezone=True), nullable=True)
    marketing_consent = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String, nullable=True)  # Service or admin user
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes для производительности
    __table_args__ = (
        # Composite indexes
        Index('ix_user_profiles_tenant_email', 'tenant_id', 'email'),
        Index('ix_user_profiles_tenant_subscription', 'tenant_id', 'subscription_plan', 'subscription_status'),
        Index('ix_user_profiles_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_user_profiles_tenant_updated', 'tenant_id', 'updated_at'),
        
        # Constraints
        CheckConstraint('subscription_plan IN (\'free\', \'basic\', \'premium\', \'enterprise\')', name='check_subscription_plan'),
        CheckConstraint('subscription_status IN (\'active\', \'inactive\', \'cancelled\', \'suspended\')', name='check_subscription_status'),
        CheckConstraint('billing_cycle IN (\'monthly\', \'quarterly\', \'yearly\')', name='check_billing_cycle'),
        CheckConstraint('monthly_close_day >= 1 AND monthly_close_day <= 28', name='check_close_day'),
        
        # Уникальность email в рамках tenant
        Index('ix_unique_email_per_tenant', 'tenant_id', 'email', unique=True, postgresql_where=Column('email').isnot(None)),
    )

class UserProfileAudit(Base):
    """
    Audit trail для изменений профилей пользователей
    Важно для compliance и отслеживания изменений
    """
    __tablename__ = "user_profiles_audit"
    
    # Primary key
    audit_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Reference to original record
    user_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    
    # Audit metadata
    operation = Column(String, nullable=False)  # INSERT, UPDATE, DELETE
    changed_fields = Column(String, nullable=True)  # JSON list of changed fields
    old_values = Column(String, nullable=True)  # JSON of old values
    new_values = Column(String, nullable=True)  # JSON of new values
    
    # Who and when
    changed_by = Column(String, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Context
    request_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    __table_args__ = (
        Index('ix_audit_tenant_user', 'tenant_id', 'user_id'),
        Index('ix_audit_tenant_time', 'tenant_id', 'changed_at'),
        Index('ix_audit_operation', 'operation'),
    )

class TenantSettings(Base):
    """
    Настройки на уровне tenant
    Позволяет кастомизировать поведение для каждого клиента
    """
    __tablename__ = "tenant_settings"
    
    tenant_id = Column(String, primary_key=True)
    
    # Business settings
    company_name = Column(String, nullable=False)
    business_type = Column(String, nullable=True)  # individual, company, enterprise
    country_code = Column(String(2), nullable=False, default='US')
    tax_jurisdiction = Column(String, nullable=True)
    
    # Feature flags
    features_enabled = Column(String, nullable=True)  # JSON list of enabled features
    api_rate_limit = Column(Integer, default=1000)  # per hour
    storage_limit_gb = Column(Integer, default=100)
    users_limit = Column(Integer, default=10)
    
    # Compliance settings
    data_retention_days = Column(Integer, default=2555)  # 7 years
    gdpr_applicable = Column(String, default='unknown')  # yes, no, unknown
    encryption_required = Column(String, default='yes')  # yes, no
    
    # Customization
    branding_colors = Column(String, nullable=True)  # JSON
    custom_domain = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)
    
    # Billing
    billing_plan = Column(String, default='free')
    billing_status = Column(String, default='active')
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_tenant_country', 'country_code'),
        Index('ix_tenant_business_type', 'business_type'),
        Index('ix_tenant_billing', 'billing_plan', 'billing_status'),
        CheckConstraint('business_type IN (\'individual\', \'company\', \'enterprise\')', name='check_business_type'),
        CheckConstraint('billing_plan IN (\'free\', \'basic\', \'premium\', \'enterprise\')', name='check_billing_plan'),
        CheckConstraint('billing_status IN (\'active\', \'suspended\', \'cancelled\')', name='check_billing_status'),
    )

# Row Level Security Policies (PostgreSQL specific)
"""
После создания таблиц, нужно применить Row Level Security:

-- Enable RLS on tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;

-- Create policies for tenant isolation
CREATE POLICY tenant_isolation_user_profiles ON user_profiles
    FOR ALL TO app_role
    USING (tenant_id = current_setting('app.current_tenant_id'));

CREATE POLICY tenant_isolation_audit ON user_profiles_audit  
    FOR ALL TO app_role
    USING (tenant_id = current_setting('app.current_tenant_id'));

CREATE POLICY tenant_isolation_settings ON tenant_settings
    FOR ALL TO app_role  
    USING (tenant_id = current_setting('app.current_tenant_id'));

-- Function to set tenant context
CREATE OR REPLACE FUNCTION set_tenant_id(tenant_id text)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', tenant_id, true);
END;
$$ LANGUAGE plpgsql;
"""

import uuid