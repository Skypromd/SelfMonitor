"""
Tenant Router Service - Динамическое управление базами данных клиентов
"""
import asyncpg  # type: ignore[import]
import redis.asyncio as redis  # type: ignore[import]
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any
import logging
import os
from datetime import datetime

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Typed shard configuration
ShardConfig = Dict[str, Any]

POSTGRES_SHARDS: Dict[str, ShardConfig] = {
    'shard_1': {
        'host': os.getenv('POSTGRES_SHARD_1_HOST', 'postgres-shard-1'),
        'port': int(os.getenv('POSTGRES_SHARD_1_PORT', '5432')),
        'user': os.getenv('POSTGRES_USER', 'tenant_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'secure_tenant_password_2026'),
        'max_tenants': int(os.getenv('MAX_TENANTS_PER_SHARD', '1000')),
        'current_tenants': 0
    },
    'shard_2': {
        'host': os.getenv('POSTGRES_SHARD_2_HOST', 'postgres-shard-2'),
        'port': int(os.getenv('POSTGRES_SHARD_2_PORT', '5433')),
        'user': os.getenv('POSTGRES_USER', 'tenant_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'secure_tenant_password_2026'),
        'max_tenants': int(os.getenv('MAX_TENANTS_PER_SHARD', '1000')),
        'current_tenants': 0
    }
}

logger = logging.getLogger(__name__)

class TenantConfig(BaseModel):
    tenant_id: str
    shard_id: str
    database_name: str
    created_at: datetime
    tier: str = "bronze"  # bronze, silver, gold
    region: str = "us-east-1"

class TenantRouter:
    def __init__(self):
        self.redis_client: Optional[redis.Redis[str]] = None
        self.shard_pools: Dict[str, asyncpg.Pool] = {}
        
    async def initialize(self):
        """Инициализация соединений с Redis и PostgreSQL шардами"""
        # Redis для метаданных tenant
        self.redis_client = redis.from_url(REDIS_URL)  # type: ignore[misc]
        
        # Пулы соединений для каждого шарда
        for shard_id, config in POSTGRES_SHARDS.items():
            try:
                self.shard_pools[shard_id] = await asyncpg.create_pool(  # type: ignore[misc]
                    host=config['host'],
                    port=config['port'],
                    user=config['user'],
                    password=config['password'],
                    database='postgres',  # Подключаемся к системной БД для создания tenant БД
                    min_size=5,
                    max_size=20
                )
                logger.info(f"Connected to shard {shard_id}")
            except Exception as e:
                logger.error(f"Failed to connect to shard {shard_id}: {e}")
                
    async def get_tenant_database_url(self, tenant_id: str) -> str:
        """Получить URL базы данных для конкретного клиента"""
        # Проверяем кэш Redis
        if self.redis_client is None:
            raise HTTPException(status_code=503, detail="Redis not initialized")
            
        cached_config = await self.redis_client.get(f"tenant:{tenant_id}")
        
        if cached_config:
            config = TenantConfig.model_validate_json(cached_config)
            return self._build_database_url(config)
            
        # Если нет в кэше, создаем новый tenant
        config = await self._create_new_tenant(tenant_id)
        return self._build_database_url(config)
    
    async def _create_new_tenant(self, tenant_id: str) -> TenantConfig:
        """Создание нового клиента с отдельной БД"""
        # Выбираем оптимальный шард
        shard_id = await self._select_optimal_shard()
        
        if not shard_id:
            raise HTTPException(status_code=503, detail="No available shards")
            
        database_name = f"tenant_{tenant_id}"
        
        # Создаем БД в выбранном шарде
        await self._create_tenant_database(shard_id, database_name)
        
        # Применяем миграции
        await self._run_tenant_migrations(shard_id, database_name, tenant_id)
        
        # Создаем конфигурацию
        config = TenantConfig(
            tenant_id=tenant_id,
            shard_id=shard_id,
            database_name=database_name,
            created_at=datetime.now()
        )
        
        # Сохраняем в Redis
        if self.redis_client is None:
            raise HTTPException(status_code=503, detail="Redis not initialized")
            
        await self.redis_client.set(
            f"tenant:{tenant_id}",
            config.model_dump_json(),
            ex=3600# 1 час кэширования
        )
        
        # Обновляем счетчик tenants в шарде  
        POSTGRES_SHARDS[shard_id]['current_tenants'] += 1
        
        logger.info(f"Created new tenant {tenant_id} in shard {shard_id}")
        return config
    
    async def _select_optimal_shard(self) -> Optional[str]:
        """Выбор оптимального шарда на основе загрузки"""
        best_shard = None
        min_load = float('inf')
        
        for shard_id, config in POSTGRES_SHARDS.items():
            if config['current_tenants'] < config['max_tenants']:
                load_ratio = config['current_tenants'] / config['max_tenants']
                if load_ratio < min_load:
                    min_load = load_ratio
                    best_shard = shard_id
                    
        # Если все шарды заполнены, нужно создать новый
        if best_shard is None:
            best_shard = await self._create_new_shard()
            
        return best_shard
    
    async def _create_tenant_database(self, shard_id: str, database_name: str):
        """Создание БД для нового клиента"""
        pool = self.shard_pools[shard_id]
        
        async with pool.acquire() as connection:  # type: ignore[misc]
            # Проверяем, существует ли БД
            db_exists = await connection.fetchval(  # type: ignore[misc]
                "SELECT 1 FROM pg_database WHERE datname = $1", 
                database_name
            )
            
            if not db_exists:
                # Создаем БД (нужно делать вне транзакции)
                await connection.execute(f'CREATE DATABASE "{database_name}"')  # type: ignore[misc]
                logger.info(f"Created database {database_name} in shard {shard_id}")
                
    async def _run_tenant_migrations(self, shard_id: str, database_name: str, tenant_id: str):
        """Применение миграций для новой tenant БД"""
        shard_config = POSTGRES_SHARDS[shard_id]
        
        # Создаем новое соединение с tenant БД
        tenant_pool = await asyncpg.create_pool(  # type: ignore[misc]
            host=shard_config['host'],
            port=shard_config['port'], 
            user=shard_config['user'],
            password=shard_config['password'],
            database=database_name,
            min_size=1,
            max_size=2
        )
        
        try:
            async with tenant_pool.acquire() as connection:  # type: ignore[misc]
                # Создаем схему для каждого микросервиса
                await self._create_service_schemas(connection, tenant_id)
                
        finally:
            await tenant_pool.close()  # type: ignore[misc]
    
    async def _create_service_schemas(self, connection: Any, tenant_id: str):
        """Создание схем для каждого микросервиса в tenant БД"""
        
        # Схемы для основных сервисов
        schemas = [
            'user_profiles',
            'transactions', 
            'analytics',
            'compliance',
            'documents',
            'calendar',
            'fraud_detection',
            'business_intelligence'
        ]
        
        for schema in schemas:
            await connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')  # type: ignore[misc]
            
        # Создаем базовые таблицы для каждого сервиса
        await self._create_base_tables(connection, tenant_id)
        
    async def _create_base_tables(self, connection: Any, tenant_id: str):
        """Создание базовых таблиц в tenant БД"""
        
        # User Profiles таблица
        await connection.execute("""  # type: ignore[misc]
            CREATE TABLE IF NOT EXISTS user_profiles.profiles (
                user_id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL DEFAULT $1,
                first_name VARCHAR,
                last_name VARCHAR,
                date_of_birth DATE,
                subscription_plan VARCHAR NOT NULL DEFAULT 'free',
                subscription_status VARCHAR NOT NULL DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """, tenant_id)
        
        # Transactions таблица
        await connection.execute("""  # type: ignore[misc]
            CREATE TABLE IF NOT EXISTS transactions.transactions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR NOT NULL,
                tenant_id VARCHAR NOT NULL DEFAULT $1,
                account_id UUID NOT NULL,
                provider_transaction_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                description VARCHAR NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                currency VARCHAR(3) NOT NULL,
                category VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """, tenant_id)
        
        # Analytics таблица
        await connection.execute("""  # type: ignore[misc]
            CREATE TABLE IF NOT EXISTS analytics.events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id VARCHAR NOT NULL DEFAULT $1,
                user_id VARCHAR NOT NULL,
                event_type VARCHAR NOT NULL,
                event_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """, tenant_id)
        
        # Создаем индексы для производительности
        await self._create_tenant_indexes(connection, tenant_id)
        
    async def _create_tenant_indexes(self, connection: Any, tenant_id: str):
        """Создание индексов для оптимизации tenant queries"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_profiles_tenant ON user_profiles.profiles(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_tenant ON transactions.transactions(tenant_id)", 
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions.transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_tenant ON analytics.events(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics.events(user_id)"
        ]
        
        for index_sql in indexes:
            await connection.execute(index_sql)  # type: ignore[misc]
            
    async def _create_new_shard(self) -> Optional[str]:
        """Создание нового шарда при превышении лимитов"""
        new_shard_id = f"shard_{len(POSTGRES_SHARDS) + 1}"
        
        # В production здесь будет вызов к Kubernetes/Docker API
        # для создания новых PostgreSQL инстансов
        logger.warning(f"Need to create new shard {new_shard_id} - auto-scaling needed")
        
        # Пока возвращаем None, что вызовет ошибку 503
        return None
        
    def _build_database_url(self, config: TenantConfig) -> str:
        """Формирование URL для подключения к tenant БД"""
        shard_config = POSTGRES_SHARDS[config.shard_id]
        
        return (f"postgresql+asyncpg://{shard_config['user']}:"
                f"{shard_config['password']}@{shard_config['host']}:"
                f"{shard_config['port']}/{config.database_name}")
    
    async def get_tenant_health(self, tenant_id: str) -> Dict[str, Any]:
        """Получение health метрик для конкретного tenant"""
        if self.redis_client is None:
            raise HTTPException(status_code=503, detail="Redis not initialized")
            
        config_data = await self.redis_client.get(f"tenant:{tenant_id}")
        
        if not config_data:
            raise HTTPException(status_code=404, detail="Tenant not found")
            
        config = TenantConfig.model_validate_json(config_data)
        shard_config = POSTGRES_SHARDS[config.shard_id]
        
        try:
            pool = self.shard_pools[config.shard_id]
            async with pool.acquire() as _connection:  # type: ignore[misc]
                # Создаем соединение с tenant БД
                tenant_conn = await asyncpg.connect(  # type: ignore[misc]
                    host=shard_config['host'],
                    port=shard_config['port'],
                    user=shard_config['user'], 
                    password=shard_config['password'],
                    database=config.database_name
                )
                
                try:
                    # Получаем метрики
                    db_size = await tenant_conn.fetchval(  # type: ignore[misc]
                        "SELECT pg_size_pretty(pg_database_size(current_database()))"
                    )
                    
                    table_count = await tenant_conn.fetchval(  # type: ignore[misc]
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog')"
                    )
                    
                    return {
                        "tenant_id": tenant_id,
                        "shard_id": config.shard_id,
                        "database_size": db_size,
                        "table_count": table_count,
                        "created_at": config.created_at,
                        "status": "healthy"
                    }
                    
                finally:
                    await tenant_conn.close()  # type: ignore[misc]
                    
        except Exception as e:
            logger.error(f"Health check failed for tenant {tenant_id}: {e}")
            return {
                "tenant_id": tenant_id,
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """Полное удаление tenant (для GDPR compliance)"""
        if self.redis_client is None:
            raise HTTPException(status_code=503, detail="Redis not initialized")
            
        config_data = await self.redis_client.get(f"tenant:{tenant_id}")
        
        if not config_data:
            return False
            
        config = TenantConfig.model_validate_json(config_data)
        
        try:
            # Удаляем БД
            pool = self.shard_pools[config.shard_id]
            async with pool.acquire() as connection:  # type: ignore[misc]
                await connection.execute(f'DROP DATABASE IF EXISTS "{config.database_name}"')  # type: ignore[misc]
                
            # Удаляем из Redis
            await self.redis_client.delete(f"tenant:{tenant_id}")  # type: ignore[misc]
            
            # Уменьшаем счетчик
            POSTGRES_SHARDS[config.shard_id]['current_tenants'] -= 1
            
            logger.info(f"Deleted tenant {tenant_id} completely")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            return False

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events"""
    # Startup
    await tenant_router.initialize()
    logger.info("Tenant Router Service started")
    yield
    # Shutdown - cleanup if needed
    pass

# FastAPI app
app = FastAPI(
    title="Tenant Router Service", 
    version="1.0.0", 
    lifespan=lifespan
)
tenant_router = TenantRouter()

@app.get("/tenant/{tenant_id}/database-url")
async def get_tenant_database_url(tenant_id: str):
    """Получить URL БД для конкретного клиента"""
    try:
        url = await tenant_router.get_tenant_database_url(tenant_id)
        return {"tenant_id": tenant_id, "database_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tenant/{tenant_id}/health")      
async def get_tenant_health(tenant_id: str):
    """Получить health статус tenant"""
    return await tenant_router.get_tenant_health(tenant_id)

@app.delete("/tenant/{tenant_id}")
async def delete_tenant(tenant_id: str):
    """Удалить tenant полностью (GDPR)"""
    success = await tenant_router.delete_tenant(tenant_id)
    if success:
        return {"message": f"Tenant {tenant_id} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Tenant not found")

@app.get("/shards/status")
async def get_shards_status() -> Dict[str, Any]:
    """Статус всех шардов"""
    return {
        "shards": POSTGRES_SHARDS,
        "total_shards": len(POSTGRES_SHARDS),
        "total_tenants": sum(s['current_tenants'] for s in POSTGRES_SHARDS.values())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # type: ignore[misc]