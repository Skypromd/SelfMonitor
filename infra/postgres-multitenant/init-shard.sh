#!/bin/bash
set -e

# PostgreSQL Multi-Tenant Shard Initialization Script
# Создает отдельные БД для каждого tenant и настраивает Row Level Security

echo "🏗️ Initializing PostgreSQL Multi-Tenant Shard..."

# Function to create a tenant database with proper structure
create_tenant_database() {
    local db_name=$1
    local tenant_id=$2
    
    echo "Creating database $db_name for tenant $tenant_id..."
    
    # Create database
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
        CREATE DATABASE "$db_name";
        GRANT ALL PRIVILEGES ON DATABASE "$db_name" TO $POSTGRES_USER;
EOSQL

    # Initialize tenant database structure
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db_name" <<-EOSQL
        -- Enable necessary extensions
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        
        -- Create tenant context function
        CREATE OR REPLACE FUNCTION set_tenant_id(tenant_id text)
        RETURNS void AS \$\$
        BEGIN
            PERFORM set_config('app.current_tenant_id', tenant_id, true);
        END;
        \$\$ LANGUAGE plpgsql;
        
        -- Create schemas for microservices
        CREATE SCHEMA IF NOT EXISTS user_profiles;
        CREATE SCHEMA IF NOT EXISTS transactions;
        CREATE SCHEMA IF NOT EXISTS analytics;
        CREATE SCHEMA IF NOT EXISTS compliance;
        CREATE SCHEMA IF NOT EXISTS documents;
        CREATE SCHEMA IF NOT EXISTS calendar;
        CREATE SCHEMA IF NOT EXISTS fraud_detection;
        CREATE SCHEMA IF NOT EXISTS business_intelligence;
        CREATE SCHEMA IF NOT EXISTS banking;
        CREATE SCHEMA IF NOT EXISTS notifications;
        
        -- Create user_profiles table
        CREATE TABLE IF NOT EXISTS user_profiles.profiles (
            user_id VARCHAR PRIMARY KEY,
            tenant_id VARCHAR NOT NULL DEFAULT '$tenant_id',
            first_name VARCHAR,
            last_name VARCHAR,
            email VARCHAR UNIQUE,
            phone VARCHAR,
            date_of_birth DATE,
            subscription_plan VARCHAR NOT NULL DEFAULT 'free',
            subscription_status VARCHAR NOT NULL DEFAULT 'active',
            billing_cycle VARCHAR NOT NULL DEFAULT 'monthly',
            timezone VARCHAR DEFAULT 'UTC',
            language VARCHAR DEFAULT 'en', 
            currency VARCHAR(3) DEFAULT 'USD',
            data_retention_days INTEGER DEFAULT 2555,
            gdpr_consent TIMESTAMP WITH TIME ZONE,
            marketing_consent TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_by VARCHAR,
            last_login TIMESTAMP WITH TIME ZONE,
            
            CONSTRAINT check_subscription_plan CHECK (subscription_plan IN ('free', 'basic', 'premium', 'enterprise')),
            CONSTRAINT check_subscription_status CHECK (subscription_status IN ('active', 'inactive', 'cancelled', 'suspended')),
            CONSTRAINT check_billing_cycle CHECK (billing_cycle IN ('monthly', 'quarterly', 'yearly'))
        );
        
        -- Create transactions table
        CREATE TABLE IF NOT EXISTS transactions.transactions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id VARCHAR NOT NULL,
            tenant_id VARCHAR NOT NULL DEFAULT '$tenant_id',
            account_id UUID NOT NULL,
            provider_transaction_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            description VARCHAR NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            category VARCHAR,
            tax_category VARCHAR,
            business_use_percent DECIMAL(5,2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create analytics events table
        CREATE TABLE IF NOT EXISTS analytics.events (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id VARCHAR NOT NULL DEFAULT '$tenant_id',
            user_id VARCHAR NOT NULL,
            event_type VARCHAR NOT NULL,
            event_data JSONB,
            session_id VARCHAR,
            ip_address INET,
            user_agent VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create compliance table
        CREATE TABLE IF NOT EXISTS compliance.compliance_checks (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id VARCHAR NOT NULL DEFAULT '$tenant_id',
            user_id VARCHAR NOT NULL,
            check_type VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            details JSONB,
            risk_score INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create audit table
        CREATE TABLE IF NOT EXISTS user_profiles.profiles_audit (
            audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id VARCHAR NOT NULL,
            tenant_id VARCHAR NOT NULL DEFAULT '$tenant_id',
            operation VARCHAR NOT NULL,
            changed_fields TEXT,
            old_values TEXT,
            new_values TEXT,
            changed_by VARCHAR,
            changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            request_id VARCHAR,
            ip_address INET,
            user_agent VARCHAR
        );
        
        -- Create tenant settings table
        CREATE TABLE IF NOT EXISTS tenant_settings (
            tenant_id VARCHAR PRIMARY KEY,
            company_name VARCHAR NOT NULL,
            business_type VARCHAR DEFAULT 'individual',
            country_code VARCHAR(2) NOT NULL DEFAULT 'US',
            tax_jurisdiction VARCHAR,
            features_enabled TEXT,
            api_rate_limit INTEGER DEFAULT 1000,
            storage_limit_gb INTEGER DEFAULT 100,
            users_limit INTEGER DEFAULT 10,
            data_retention_days INTEGER DEFAULT 2555,
            gdpr_applicable VARCHAR DEFAULT 'unknown',
            encryption_required VARCHAR DEFAULT 'yes',
            branding_colors TEXT,
            custom_domain VARCHAR,
            webhook_url VARCHAR,
            billing_plan VARCHAR DEFAULT 'free',
            billing_status VARCHAR DEFAULT 'active',
            trial_ends_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            CONSTRAINT check_business_type CHECK (business_type IN ('individual', 'company', 'enterprise')),
            CONSTRAINT check_billing_plan CHECK (billing_plan IN ('free', 'basic', 'premium', 'enterprise')),
            CONSTRAINT check_billing_status CHECK (billing_status IN ('active', 'suspended', 'cancelled'))
        );
        
        -- Insert default tenant settings
        INSERT INTO tenant_settings (tenant_id, company_name) 
        VALUES ('$tenant_id', 'Demo Company $tenant_id')
        ON CONFLICT (tenant_id) DO NOTHING;
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_profiles_tenant ON user_profiles.profiles(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_profiles_email ON user_profiles.profiles(email);
        CREATE INDEX IF NOT EXISTS idx_profiles_subscription ON user_profiles.profiles(subscription_plan, subscription_status);
        CREATE INDEX IF NOT EXISTS idx_profiles_created ON user_profiles.profiles(created_at);
        
        CREATE INDEX IF NOT EXISTS idx_transactions_tenant ON transactions.transactions(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions.transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions.transactions(date);
        CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions.transactions(amount);
        CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions.transactions(category);
        
        CREATE INDEX IF NOT EXISTS idx_events_tenant ON analytics.events(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_events_user ON analytics.events(user_id);
        CREATE INDEX IF NOT EXISTS idx_events_type ON analytics.events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_created ON analytics.events(created_at);
        
        CREATE INDEX IF NOT EXISTS idx_compliance_tenant ON compliance.compliance_checks(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_compliance_user ON compliance.compliance_checks(user_id);
        CREATE INDEX IF NOT EXISTS idx_compliance_type ON compliance.compliance_checks(check_type);
        CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance.compliance_checks(status);
        
        CREATE INDEX IF NOT EXISTS idx_audit_tenant ON user_profiles.profiles_audit(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_audit_user ON user_profiles.profiles_audit(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_operation ON user_profiles.profiles_audit(operation);
        CREATE INDEX IF NOT EXISTS idx_audit_time ON user_profiles.profiles_audit(changed_at);
        
        -- Enable Row Level Security
        ALTER TABLE user_profiles.profiles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE transactions.transactions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE analytics.events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE compliance.compliance_checks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE user_profiles.profiles_audit ENABLE ROW LEVEL SECURITY;
        ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;
        
        -- Create RLS policies
        CREATE POLICY tenant_isolation_profiles ON user_profiles.profiles
            FOR ALL
            USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '$tenant_id'));
            
        CREATE POLICY tenant_isolation_transactions ON transactions.transactions
            FOR ALL 
            USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '$tenant_id'));
            
        CREATE POLICY tenant_isolation_events ON analytics.events
            FOR ALL
            USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '$tenant_id'));
            
        CREATE POLICY tenant_isolation_compliance ON compliance.compliance_checks
            FOR ALL
            USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '$tenant_id'));
            
        CREATE POLICY tenant_isolation_audit ON user_profiles.profiles_audit
            FOR ALL
            USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '$tenant_id'));
            
        CREATE POLICY tenant_isolation_settings ON tenant_settings
            FOR ALL
            USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), '$tenant_id'));
        
        -- Create application role
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_role') THEN
                CREATE ROLE app_role;
                GRANT USAGE ON ALL SCHEMAS IN DATABASE "$db_name" TO app_role;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN DATABASE "$db_name" TO app_role;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN DATABASE "$db_name" TO app_role;
            END IF;
        END
        \$\$;
        
        -- Grant permissions to main user
        GRANT app_role TO $POSTGRES_USER;
        
        -- Create sample data for demo
        INSERT INTO user_profiles.profiles (user_id, first_name, last_name, email, subscription_plan)
        VALUES 
            ('demo_user_1', 'John', 'Doe', 'john.doe@$tenant_id.example.com', 'premium'),
            ('demo_user_2', 'Jane', 'Smith', 'jane.smith@$tenant_id.example.com', 'basic')
        ON CONFLICT (user_id) DO NOTHING;
        
        INSERT INTO transactions.transactions (user_id, account_id, provider_transaction_id, date, description, amount, category)
        VALUES 
            ('demo_user_1', uuid_generate_v4(), 'demo_tx_1', CURRENT_DATE, 'Demo Income Transaction', 1500.00, 'income'),
            ('demo_user_1', uuid_generate_v4(), 'demo_tx_2', CURRENT_DATE - 1, 'Demo Expense Transaction', -45.50, 'office_supplies'),
            ('demo_user_2', uuid_generate_v4(), 'demo_tx_3', CURRENT_DATE, 'Demo Service Transaction', 2500.00, 'consulting')
        ON CONFLICT (id) DO NOTHING;
        
        -- Create maintenance functions
        CREATE OR REPLACE FUNCTION cleanup_old_audit_records()
        RETURNS INTEGER AS \$\$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM user_profiles.profiles_audit 
            WHERE changed_at < NOW() - INTERVAL '2 years';
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        \$\$ LANGUAGE plpgsql;
        
        CREATE OR REPLACE FUNCTION get_tenant_stats()
        RETURNS TABLE(
            total_users BIGINT,
            active_subscriptions BIGINT,
            total_transactions BIGINT,
            total_events BIGINT
        ) AS \$\$
        BEGIN
            RETURN QUERY
            SELECT 
                (SELECT COUNT(*) FROM user_profiles.profiles),
                (SELECT COUNT(*) FROM user_profiles.profiles WHERE subscription_status = 'active'),
                (SELECT COUNT(*) FROM transactions.transactions),
                (SELECT COUNT(*) FROM analytics.events);
        END;
        \$\$ LANGUAGE plpgsql;
        
        COMMENT ON DATABASE "$db_name" IS 'Multi-tenant database for tenant $tenant_id - Created by SelfMonitor Platform';
        
EOSQL

    echo "✅ Database $db_name initialized successfully for tenant $tenant_id"
}

# Main execution
if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Creating multiple tenant databases..."
    
    # Convert comma-separated list to array
    IFS=',' read -ra DATABASES <<< "$POSTGRES_MULTIPLE_DATABASES"
    
    for db_name in "${DATABASES[@]}"; do
        # Extract tenant ID from database name (tenant_xxx)
        tenant_id=$(echo "$db_name" | sed 's/tenant_//')
        create_tenant_database "$db_name" "$tenant_id"
    done
else
    echo "No multiple databases specified in POSTGRES_MULTIPLE_DATABASES"
    echo "Creating default database structure..."
    
    # Apply same structure to default database
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        
        SELECT 'Default database initialized' as status;
EOSQL
fi

echo "🎉 PostgreSQL Multi-Tenant Shard initialization completed!"
echo "📊 Created databases:"
if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "$POSTGRES_MULTIPLE_DATABASES"
else
    echo "$POSTGRES_DB (default)"
fi