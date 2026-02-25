"""
SelfMonitor Demo Server
Демонстрационный сервис, показывающий ключевые возможности платформы
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
from jose import JWTError, jwt

# Настройки
SECRET_KEY = "demo_secret_key_for_selfmonitor_platform"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer()

# Модели данных
class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    first_name: str
    last_name: str
    business_type: str = "freelancer"
    subscription_plan: str = "free"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    amount: float
    description: str
    category: Optional[str] = "uncategorized"
    tax_category: Optional[str] = None
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    business_use_percent: Optional[float] = 0.0

class TaxCalculation(BaseModel):
    income: float
    expenses: float
    tax_free_allowance: float = 12570.0
    estimated_tax: float
    ni_contributions: float
    total_liability: float

class DashboardStats(BaseModel):
    total_transactions: int
    total_income: float
    total_expenses: float
    net_profit: float
    tax_readiness_score: int
    upcoming_deadlines: List[Dict[str, Any]]

# Создание FastAPI приложения
app = FastAPI(
    title="SelfMonitor Demo Platform",
    description="🚀 Демонстрация возможностей SelfMonitor FinTech платформы для самозанятых",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Мок-данные для демонстрации
demo_users: Dict[str, UserProfile] = {}
demo_transactions: Dict[str, List[Transaction]] = {}

# Функции аутентификации
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode: Dict[str, Any] = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta  # Fix deprecated utcnow
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)  # Fix deprecated utcnow
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Извлечение ID пользователя из JWT токена"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# API Endpoints

@app.get("/", tags=["Demo"])
async def welcome() -> Dict[str, Any]:
    """Добро пожаловать в SelfMonitor Demo!"""
    return {
        "message": "🎉 Добро пожаловать в SelfMonitor FinTech Platform!",
        "description": "Полная платформа для управления финансами самозанятых",
        "features": [
            "📊 Автоматический учет доходов и расходов",
            "💰 Расчет налогов и НИ взносов",
            "📈 Аналитика и отчеты",
            "🤖 AI-помощник для финансового планирования",
            "📱 Мобильное приложение",
            "🔒 Банковская безопасность"
        ],
        "demo_endpoints": {
            "authentication": "/auth/demo-login",
            "dashboard": "/dashboard",
            "transactions": "/transactions",
            "tax_calculation": "/tax/calculate",
            "api_docs": "/docs"
        },
        "version": "2.0.0"
    }

@app.post("/auth/demo-login", tags=["Authentication"])
async def demo_login(email: str = "demo@selfmonitor.uk", name: str = "Demo User") -> Dict[str, Any]:
    """Демо-аутентификация для тестирования"""
    user_id = str(uuid.uuid4())
    
    # Создание демо-пользователя
    demo_user = UserProfile(
        id=user_id,
        email=email,
        first_name=name.split()[0],
        last_name=name.split()[-1] if len(name.split()) > 1 else "User"
    )
    demo_users[user_id] = demo_user
    
    # Создание демо-транзакций
    demo_transactions[user_id] = [
        Transaction(amount=2500.0, description="Freelance consulting - Web development", category="income", tax_category="turnover", business_use_percent=100.0),
        Transaction(amount=1800.0, description="Design project - Mobile app", category="income", tax_category="turnover", business_use_percent=100.0),
        Transaction(amount=-45.99, description="Adobe Creative Suite subscription", category="software", tax_category="office", business_use_percent=100.0),
        Transaction(amount=-89.50, description="Coworking space rental", category="workspace", tax_category="premises", business_use_percent=100.0),
        Transaction(amount=-15.80, description="Coffee meeting with client", category="meals", tax_category="client_entertainment", business_use_percent=50.0),
        Transaction(amount=3200.0, description="Monthly retainer - SEO consulting", category="income", tax_category="turnover", business_use_percent=100.0),
        Transaction(amount=-156.00, description="Professional development course", category="education", tax_category="legal_professional", business_use_percent=100.0)
    ]
    
    # Создание JWT токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": demo_user,
        "message": "🎉 Успешная авторизация в SelfMonitor Demo!",
        "instructions": "Используйте этот токен в заголовке Authorization: Bearer <token>"
    }

@app.get("/dashboard", response_model=DashboardStats, tags=["Dashboard"])
async def get_dashboard(user_id: str = Depends(get_current_user_id)):
    """📊 Получение данных для дашборда"""
    if user_id not in demo_transactions:
        raise HTTPException(status_code=404, detail="User transactions not found")
    
    transactions = demo_transactions[user_id]
    
    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
    net_profit = total_income - total_expenses
    
    # Расчет готовности к налогам
    categorized = sum(1 for t in transactions if t.tax_category)
    tax_readiness_score = int((categorized / len(transactions)) * 100) if transactions else 0
    
    upcoming_deadlines: List[Dict[str, Any]] = [
        {
            "title": "📅 Подача налоговой декларации Self Assessment",
            "date": "2026-01-31",
            "days_left": 340,
            "priority": "high"
        },
        {
            "title": "💰 Уплата подоходного налога (1-й платеж)",
            "date": "2026-01-31", 
            "days_left": 340,
            "priority": "high"
        },
        {
            "title": "📊 Квартальная отчетность НДС",
            "date": "2026-04-07",
            "days_left": 41,
            "priority": "medium"
        }
    ]
    
    return DashboardStats(
        total_transactions=len(transactions),
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
        tax_readiness_score=tax_readiness_score,
        upcoming_deadlines=upcoming_deadlines
    )

@app.get("/transactions", response_model=List[Transaction], tags=["Transactions"])
async def get_transactions(user_id: str = Depends(get_current_user_id)) -> List[Any]:
    """💳 Получение всех транзакций пользователя"""
    if user_id not in demo_transactions:
        return []
    return demo_transactions[user_id]

@app.post("/transactions", response_model=Transaction, tags=["Transactions"])
async def create_transaction(transaction: Transaction, user_id: str = Depends(get_current_user_id)):
    """➕ Создание новой транзакции"""
    if user_id not in demo_transactions:
        demo_transactions[user_id] = []
    
    new_transaction = Transaction(**transaction.model_dump())  # Fix deprecated .dict()
    demo_transactions[user_id].append(new_transaction)
    
    return new_transaction

@app.post("/tax/calculate", response_model=TaxCalculation, tags=["Tax Engine"])
async def calculate_tax(user_id: str = Depends(get_current_user_id)):
    """🧮 Расчет налогов и НИ взносов для UK"""
    if user_id not in demo_transactions:
        raise HTTPException(status_code=404, detail="User transactions not found")
    
    transactions = demo_transactions[user_id]
    
    # Расчет доходов и расходов
    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
    
    # Налогооблагаемая прибыль
    taxable_profit = max(0, total_income - total_expenses)
    
    # Персональная льгота на 2024/25 = £12,570
    tax_free_allowance = 12570.0
    taxable_income = max(0, taxable_profit - tax_free_allowance)
    
    # Основная ставка подоходного налога 20% до £37,700
    basic_rate_limit = 37700.0
    basic_rate_tax = min(taxable_income, basic_rate_limit) * 0.20
    
    # Повышенная ставка 40% свыше £37,700
    higher_rate_tax = max(0, taxable_income - basic_rate_limit) * 0.40
    
    estimated_tax = basic_rate_tax + higher_rate_tax
    
    # National Insurance Class 2 и Class 4
    # Class 2: £3.45/неделя если прибыль > £6,725
    class2_ni = 52 * 3.45 if taxable_profit > 6725 else 0
    
    # Class 4: 9% с £12,570 до £50,270, потом 2%
    class4_lower = max(0, min(taxable_profit, 50270) - 12570) * 0.09
    class4_upper = max(0, taxable_profit - 50270) * 0.02
    class4_ni = class4_lower + class4_upper
    
    ni_contributions = class2_ni + class4_ni
    total_liability = estimated_tax + ni_contributions
    
    return TaxCalculation(
        income=total_income,
        expenses=total_expenses,
        tax_free_allowance=tax_free_allowance,
        estimated_tax=estimated_tax,
        ni_contributions=ni_contributions,
        total_liability=total_liability
    )

@app.get("/analytics/insights", tags=["AI Analytics"])
async def get_ai_insights(user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """🤖 AI-анализ финансов с рекомендациями"""
    if user_id not in demo_transactions:
        raise HTTPException(status_code=404, detail="User transactions not found")
    
    transactions = demo_transactions[user_id]
    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
    
    # AI-инсайты на основе данных
    expense_ratio = total_expenses / total_income if total_income > 0 else 0
    
    insights: Dict[str, Any] = {
        "financial_health_score": 85,  # Оценка финансового здоровья
        "expense_ratio": expense_ratio,
        "recommendations": [
            "💡 Отличная работа! Ваши расходы составляют только {:.1%} от дохода".format(expense_ratio),
            "📈 Рекомендуем отложить 20% прибыли на налоги",
            "🎯 Создайте резервный фонд в размере 3-6 месячных расходов",
            "📊 Рассмотрите инвестирование в пенсионную схему для налоговых льгот"
        ],
        "predicted_monthly_income": total_income * 1.1,  # Прогноз роста на 10%
        "tax_optimization_tips": [
            "💼 Используйте максимум деловых расходов",
            "🏠 Рассмотрите расходы на домашний офис", 
            "🚗 Учитывайте автомобильные расходы по ставке £0.45/миля",
            "📚 Инвестируйте в профессиональное развитие"
        ],
        "growth_opportunities": [
            "🚀 Средний доход фрилансеров в вашей сфере: £45,000/год",
            "📱 84% клиентов готовы платить больше за мобильную оптимизацию",
            "💻 Повышение навыков AI может увеличить доход на 40%"
        ]
    }
    
    return insights

@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """💚 Проверка состояния системы"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "services": {
            "user_service": "✅ online",
            "transaction_service": "✅ online", 
            "tax_engine": "✅ online",
            "ai_analytics": "✅ online"
        },
        "version": "2.0.0"
    }

if __name__ == "__main__":
    print("🚀 Запуск SelfMonitor Demo Server...")
    print("📖 API документация доступна по адресу: http://localhost:8000/docs")
    print("🎯 Главная страница: http://localhost:8000")
    print("")
    print("Для запуска используйте команду:")
    print("uvicorn demo_server:app --host 0.0.0.0 --port 8000 --reload")