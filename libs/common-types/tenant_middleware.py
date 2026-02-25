"""
Multi-Tenant Middleware - Определение и маршрутизация tenant данных
"""
from fastapi import Request, HTTPException, Depends, Response  
from fastapi.security import HTTPBearer
import jwt  # type: ignore[import-untyped]
import httpx
import asyncio
from typing import Optional, Dict, Callable, Awaitable, Any
import logging
import os

# Configuration
TENANT_ROUTER_URL = os.getenv("TENANT_ROUTER_URL", "http://tenant-router:8001")
JWT_SECRET = os.getenv("JWT_SECRET", "a_secure_random_string_for_jwt_signing_!@#$%^")
JWT_ALGORITHMS = ["HS256"]

logger = logging.getLogger(__name__)
security = HTTPBearer()

class TenantContext:
    """Контекст текущего tenant для request"""
    def __init__(self, tenant_id: str, database_url: str):
        self.tenant_id = tenant_id
        self.database_url = database_url

class TenantMiddleware:
    def __init__(self):
        self.http_client = httpx.AsyncClient()
        self.tenant_cache: Dict[str, str] = {}  # Кэш tenant_id -> database_url
        
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Основной middleware для определения tenant"""
        
        # Пропускаем health checks и системные endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        try:
            # Извлекаем tenant_id из JWT токена
            tenant_id = await self._extract_tenant_id(request)
            
            # Получаем URL базы данных для tenant
            database_url = await self._get_tenant_database_url(tenant_id)
            
            # Добавляем контекст в request state
            request.state.tenant = TenantContext(tenant_id, database_url)
            
            logger.info(f"Request routed to tenant {tenant_id}")
            
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            raise HTTPException(status_code=500, detail="Internal tenant routing error")
    
    async def _extract_tenant_id(self, request: Request) -> str:
        """Извлечение tenant_id из JWT токена"""
        
        # Получаем Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header missing")
            
        # Извлекаем токен
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
            
        # Декодируем JWT
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=JWT_ALGORITHMS)  # type: ignore[misc]
            tenant_id = payload.get("tenant_id")
            
            if not tenant_id:
                raise HTTPException(status_code=401, detail="Tenant ID missing from token")
                
            # Валидация tenant_id
            if not self._is_valid_tenant_id(tenant_id):
                raise HTTPException(status_code=401, detail="Invalid tenant ID format")
                
            return tenant_id
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def _get_tenant_database_url(self, tenant_id: str) -> str:
        """Получение URL базы данных для tenant"""
        
        # Проверяем кэш
        if tenant_id in self.tenant_cache:
            return self.tenant_cache[tenant_id]
            
        # Запрашиваем у Tenant Router
        try:
            response = await self.http_client.get(
                f"{TENANT_ROUTER_URL}/tenant/{tenant_id}/database-url",
                timeout=5.0
            )
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Tenant not found")
            elif response.status_code != 200:
                raise HTTPException(status_code=503, detail="Tenant routing service unavailable")
                
            data = response.json()
            database_url = data["database_url"]
            
            # Кэшируем на 5 минут
            self.tenant_cache[tenant_id] = database_url
            asyncio.create_task(self._clear_cache_after_delay(tenant_id, 300))
            
            return database_url
            
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to tenant router: {e}")
            raise HTTPException(status_code=503, detail="Tenant routing service unavailable")
    
    async def _clear_cache_after_delay(self, tenant_id: str, delay: int):
        """Очистка кэша с задержкой"""
        await asyncio.sleep(delay)
        self.tenant_cache.pop(tenant_id, None)
    
    def _is_valid_tenant_id(self, tenant_id: Optional[str]) -> bool:
        """Валидация формата tenant_id"""
        # Проверяем, что это строка длиной от 3 до 50 символов
        # содержащая только буквы, цифры, тире и подчеркивания
        if not tenant_id:
            return False
        
        if len(tenant_id) < 3 or len(tenant_id) > 50:
            return False
            
        if not tenant_id.replace('-', '').replace('_', '').isalnum():
            return False
            
        return True

# Dependency для получения tenant context в endpoints
async def get_tenant_context(request: Request) -> TenantContext:
    """FastAPI dependency для получения tenant контекста"""
    if not hasattr(request.state, 'tenant'):
        raise HTTPException(status_code=500, detail="Tenant context not available")
    
    return request.state.tenant

# Декоратор для tenant-aware database sessions
class TenantDatabase:
    """Управление соединениями с tenant-specific базами данных"""
    
    def __init__(self):
        self.connection_pools: Dict[str, Any] = {}
    
    async def get_tenant_session(self, tenant_context: TenantContext):
        """Получение сессии базы данных для конкретного tenant"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        tenant_id = tenant_context.tenant_id
        database_url = tenant_context.database_url
        
        # Создаем или получаем connection pool для tenant
        if tenant_id not in self.connection_pools:
            engine = create_async_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False  # True для debug
            )
            
            # AsyncEngine is compatible with sessionmaker
            self.connection_pools[tenant_id] = sessionmaker(  # type: ignore[arg-type, misc]
                bind=engine,  # type: ignore[arg-type]
                class_=AsyncSession, 
                expire_on_commit=False,
                autocommit=False,  # type: ignore[misc]
                autoflush=True   # type: ignore[misc]
            )
            
            logger.info(f"Created connection pool for tenant {tenant_id}")
        
        # Возвращаем сессию
        Session = self.connection_pools[tenant_id]
        async with Session() as session:
            try:
                yield session
            finally:
                await session.close()

# Глобальный экземпляр
tenant_database = TenantDatabase()

async def get_tenant_db_session(tenant_context: TenantContext = Depends(get_tenant_context)):
    """FastAPI dependency для получения tenant database session"""
    async for session in tenant_database.get_tenant_session(tenant_context):
        yield session

# Utility функции для создания JWT токенов с tenant_id
def create_tenant_jwt(user_id: str, tenant_id: str, expires_in: int = 3600) -> str:
    """Создание JWT токена с tenant_id"""
    import time
    
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in
    }
    
    token_bytes = jwt.encode(payload, JWT_SECRET, algorithm="HS256")  # type: ignore[misc]
    # PyJWT 2.0+ returns str directly, older versions returned bytes
    if isinstance(token_bytes, bytes):
        return token_bytes.decode('utf-8')
    return str(token_bytes)  # type: ignore[return-value]

def extract_tenant_from_token(token: str) -> Optional[str]:
    """Извлечение tenant_id из токена без валидации"""
    try:
        # Декодируем без проверки подписи (только для извлечения)
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("tenant_id")
    except:
        return None

# Health check функция для проверки tenant routing
async def check_tenant_routing_health() -> Dict[str, Any]:
    """Health check для tenant routing системы"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TENANT_ROUTER_URL}/shards/status", timeout=5.0)
            
            if response.status_code == 200:
                return {
                    "tenant_routing": "healthy",
                    "shards_data": response.json()
                }
            else:
                return {
                    "tenant_routing": "unhealthy", 
                    "status_code": response.status_code
                }
                
    except Exception as e:
        return {
            "tenant_routing": "unhealthy",
            "error": str(e)
        }