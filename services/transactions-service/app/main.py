import os
import uuid
from typing import Annotated, List
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import get_db
from .telemetry import setup_telemetry

# Import Kafka event streaming
import sys
import logging
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

class TransactionsServiceApp(FastAPI, EventStreamingMixin if KAFKA_ENABLED else object):
    """Enhanced Transactions Service with Kafka event streaming"""
    pass

app = TransactionsServiceApp(
    title="SelfMonitor Transactions Service",
    description="Handle financial transactions with real-time event streaming",
    version="1.0.0",
    lifespan=lifespan
)

# Instrument the app for OpenTelemetry
setup_telemetry(app)

# --- Security ---
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
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


@app.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_transactions(
    request: schemas.TransactionImportRequest, 
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Imports a batch of transactions for an account into the database."""
    imported_count = await crud.create_transactions(
        db, 
        user_id=user_id, 
        account_id=request.account_id, 
        transactions=request.transactions,
        auth_token=auth_token,
    )
    
    # Emit transaction import event
    if KAFKA_ENABLED and hasattr(app, 'emit_event'):
        try:
            await app.emit_event(
                topic="transaction.events",
                event_type="transaction_batch_imported",
                data={
                    "account_id": str(request.account_id),
                    "imported_count": imported_count,
                    "total_transactions": len(request.transactions),
                    "source": "import_endpoint"
                },
                user_id=user_id,
                correlation_id=f"import_{uuid.uuid4()}"
            )
        except Exception as e:
            logger.warning(f"Failed to emit transaction import event: {str(e)}")
    
    return {"message": "Import request accepted", "imported_count": imported_count}

@app.get("/accounts/{account_id}/transactions", response_model=List[schemas.Transaction])
async def get_transactions_for_account(
    account_id: uuid.UUID, 
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for a specific account belonging to the user from the database."""
    transactions = await crud.get_transactions_by_account(db, user_id=user_id, account_id=account_id)
    
    # Emit analytics event for transaction access
    if KAFKA_ENABLED and hasattr(app, 'emit_event') and transactions:
        try:
            await app.emit_event(
                topic="analytics.events",
                event_type="transaction_data_accessed",
                data={
                    "metric_name": "transaction_retrieval",
                    "metric_value": len(transactions),
                    "account_id": str(account_id),
                    "access_type": "account_specific",
                    "result_count": len(transactions)
                },
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to emit transaction access event: {str(e)}")
    
    return transactions

@app.get("/transactions/me", response_model=List[schemas.Transaction])
async def get_all_my_transactions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for the authenticated user across all accounts."""
    transactions = await crud.get_transactions_by_user(db, user_id=user_id)
    
    # Emit analytics event for comprehensive transaction access
    if KAFKA_ENABLED and hasattr(app, 'emit_event') and transactions:
        try:
            await app.emit_event(
                topic="analytics.events",
                event_type="transaction_data_accessed", 
                data={
                    "metric_name": "comprehensive_transaction_view",
                    "metric_value": len(transactions),
                    "access_type": "all_accounts",
                    "result_count": len(transactions),
                    "unique_accounts": len(set(str(t.account_id) for t in transactions if hasattr(t, 'account_id')))
                },
                user_id=user_id
            )
            
            # Also track user engagement
            await app.emit_event(
                topic="user.events",
                event_type="user_transaction_overview_accessed",
                data={
                    "total_transactions": len(transactions),
                    "access_timestamp": int(uuid.uuid1().time),
                    "feature": "transaction_overview"
                },
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to emit transaction overview events: {str(e)}")
    
    return transactions

@app.patch("/transactions/{transaction_id}", response_model=schemas.Transaction)
async def update_transaction_category(
    transaction_id: uuid.UUID,
    update_request: schemas.TransactionUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Updates the category of a single transaction in the database."""
    updated_transaction = await crud.update_transaction_category(
        db, 
        user_id=user_id, 
        transaction_id=transaction_id, 
        category=update_request.category
    )
    if not updated_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    
    # Emit transaction update event
    if KAFKA_ENABLED and hasattr(app, 'emit_event'):
        try:
            await app.emit_event(
                topic="transaction.events",
                event_type="transaction_category_updated",
                data={
                    "transaction_id": str(transaction_id),
                    "old_category": getattr(updated_transaction, 'previous_category', None),
                    "new_category": update_request.category,
                    "amount": float(updated_transaction.amount) if hasattr(updated_transaction, 'amount') else None,
                    "currency": getattr(updated_transaction, 'currency', 'USD'),
                    "description": getattr(updated_transaction, 'description', ''),
                    "update_source": "manual_categorization"
                },
                user_id=user_id,
                correlation_id=f"category_update_{transaction_id}"
            )
            
            # Also emit analytics event for categorization tracking
            await app.emit_event(
                topic="analytics.events", 
                event_type="transaction_categorized",
                data={
                    "metric_name": "transaction_categorization",
                    "metric_value": 1.0,
                    "transaction_id": str(transaction_id),
                    "category": update_request.category,
                    "user_action": "manual"
                },
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to emit transaction update events: {str(e)}")
    
    return updated_transaction
