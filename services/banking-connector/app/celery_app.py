import logging
from celery import Celery
import os
import httpx
import uuid
from typing import List

logger = logging.getLogger(__name__)

# Use os.getenv to read environment variables set by Docker Compose
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8002/import")

celery = Celery(
    __name__,
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

@celery.task
def import_transactions_task(account_id: str, user_id: str, bearer_token: str, transactions_data: List[dict]):
    """
    A Celery task to import transactions by calling the transactions-service.
    This runs in a separate worker process.
    """
    try:
        with httpx.Client() as client: # Use synchronous client inside Celery task
            response = client.post(
                TRANSACTIONS_SERVICE_URL,
                headers={"Authorization": f"Bearer {bearer_token}"},
                json={
                    "account_id": account_id,
                    "transactions": transactions_data
                },
                timeout=10.0
            )
            response.raise_for_status()
        logger.info("Celery task: Successfully imported %d transactions for account %s.", len(transactions_data), account_id)
        return {"status": "success", "imported_count": len(transactions_data)}
    except httpx.RequestError as e:
        logger.error("Celery task error: Could not import transactions for account %s: %s", account_id, e)
        # Celery can be configured to retry tasks on failure.
        raise e
