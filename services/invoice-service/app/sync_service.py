"""
Real-time sync integration between invoice-service and transactions-service
This module handles automatic synchronization of invoice data to create
corresponding transaction records for comprehensive financial reporting
"""

import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal
import logging

from . import models, schemas

logger = logging.getLogger(__name__)

class InvoiceTransactionSync:
    """Handles synchronization between invoice-service and transactions-service"""
    
    def __init__(self, transactions_service_url: str = "http://transactions-service:80"):
        self.transactions_service_url = transactions_service_url
        self.timeout = 30.0
    
    async def sync_invoice_to_transactions(
        self, 
        invoice: models.Invoice, 
        auth_token: str,
        sync_type: str = "created"
    ) -> Dict[str, Any]:
        """
        Sync invoice data to transactions service
        
        Args:
            invoice: Invoice model instance
            auth_token: JWT token for authentication
            sync_type: Type of sync (created, updated, paid, cancelled)
        
        Returns:
            Sync result with status and transaction_id
        """
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
            
            # Create transaction payload for invoice
            transaction_payload = self._create_transaction_payload(invoice, sync_type)
            
            async with httpx.AsyncClient() as client:
                # Check if transaction already exists
                existing_transaction = await self._find_existing_transaction(
                    client, headers, invoice.id
                )
                
                if existing_transaction:
                    # Update existing transaction
                    response = await client.put(
                        f"{self.transactions_service_url}/transactions/{existing_transaction['id']}",
                        headers=headers,
                        json=transaction_payload,
                        timeout=self.timeout
                    )
                    operation = "updated"
                else:
                    # Create new transaction
                    response = await client.post(
                        f"{self.transactions_service_url}/transactions",
                        headers=headers,
                        json=transaction_payload,
                        timeout=self.timeout
                    )
                    operation = "created"
                
                response.raise_for_status()
                transaction_data = response.json()
                
                logger.info(f"Invoice {invoice.id} successfully synced as transaction {transaction_data.get('id')}")
                
                return {
                    "status": "success",
                    "operation": operation,
                    "transaction_id": transaction_data.get("id"),
                    "sync_type": sync_type,
                    "invoice_id": invoice.id
                }
        
        except httpx.RequestError as e:
            logger.error(f"Network error syncing invoice {invoice.id}: {e}")
            return {
                "status": "error",
                "error_type": "network",
                "message": str(e),
                "invoice_id": invoice.id
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error syncing invoice {invoice.id}: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error", 
                "error_type": "http",
                "status_code": e.response.status_code,
                "message": e.response.text,
                "invoice_id": invoice.id
            }
        except Exception as e:
            logger.error(f"Unexpected error syncing invoice {invoice.id}: {e}")
            return {
                "status": "error",
                "error_type": "unknown",
                "message": str(e),
                "invoice_id": invoice.id
            }
    
    def _create_transaction_payload(self, invoice: models.Invoice, sync_type: str) -> Dict[str, Any]:
        """Create transaction payload from invoice data"""
        
        # Base transaction data
        transaction = {
            "user_id": invoice.user_id,
            "amount": float(invoice.total_amount),
            "currency": invoice.currency,
            "description": f"Invoice {invoice.invoice_number} - {invoice.client_name}",
            "date": invoice.invoice_date.isoformat(),
            "type": "income",
            "category": "Business Income",
            "subcategory": "Professional Services",
            "account": "Business Account",
            "metadata": {
                "source": "invoice_service",
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client_name,
                "invoice_status": invoice.status.value,
                "sync_type": sync_type,
                "line_items_count": len(invoice.line_items or []),
                "payment_terms": invoice.payment_terms,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "tax_amount": float(invoice.tax_amount or 0),
                "subtotal": float(invoice.subtotal or 0)
            }
        }
        
        # Adjust transaction based on invoice status  
        if invoice.status == schemas.InvoiceStatus.PAID:
            transaction["status"] = "completed"
            transaction["metadata"]["payment_confirmed"] = True
        elif invoice.status == schemas.InvoiceStatus.PARTIALLY_PAID:
            transaction["amount"] = float(invoice.paid_amount or 0)
            transaction["status"] = "pending"
            transaction["metadata"]["partial_payment"] = True
            transaction["metadata"]["remaining_balance"] = float(invoice.total_amount - (invoice.paid_amount or 0))
        elif invoice.status == schemas.InvoiceStatus.SENT:
            transaction["status"] = "pending"
            transaction["metadata"]["invoice_sent"] = True
        elif invoice.status == schemas.InvoiceStatus.CANCELLED:
            transaction["status"] = "cancelled"
            transaction["amount"] = 0
        else:
            transaction["status"] = "draft"
        
        # Add line item details for categorization
        if invoice.line_items:
            line_items_data = []
            for item in invoice.line_items:
                line_items_data.append({
                    "description": item.description,
                    "category": item.category,
                    "amount": float(item.total_amount),
                    "quantity": float(item.quantity),
                    "unit_price": float(item.unit_price)
                })
            transaction["metadata"]["line_items"] = line_items_data
            
            # Use primary line item category if available
            if invoice.line_items[0].category:
                transaction["subcategory"] = invoice.line_items[0].category
        
        return transaction
    
    async def _find_existing_transaction(
        self, 
        client: httpx.AsyncClient, 
        headers: Dict[str, str], 
        invoice_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find existing transaction for this invoice"""
        try:
            response = await client.get(
                f"{self.transactions_service_url}/transactions",
                headers=headers,
                params={"metadata.invoice_id": invoice_id, "limit": 1},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                transactions = response.json()
                return transactions[0] if transactions else None
        except Exception as e:
            logger.warning(f"Could not search for existing transaction: {e}")
        
        return None
    
    async def sync_payment_update(
        self, 
        invoice: models.Invoice, 
        payment: models.InvoicePayment,
        auth_token: str
    ) -> Dict[str, Any]:
        """Sync payment information as a separate transaction"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
            
            # Create payment transaction
            payment_transaction = {
                "user_id": invoice.user_id,
                "amount": float(payment.amount),
                "currency": invoice.currency,
                "description": f"Payment received for Invoice {invoice.invoice_number}",
                "date": payment.payment_date.isoformat(),
                "type": "income",
                "category": "Payment Received",
                "subcategory": "Invoice Payment",
                "account": "Business Account",
                "status": "completed",
                "metadata": {
                    "source": "invoice_payment",
                    "invoice_id": invoice.id,
                    "payment_id": payment.id,
                    "invoice_number": invoice.invoice_number,
                    "payment_method": payment.payment_method.value,
                    "reference_number": payment.reference_number,
                    "client_name": invoice.client_name
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.transactions_service_url}/transactions",
                    headers=headers,
                    json=payment_transaction,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                transaction_data = response.json()
                
                # Also update the main invoice transaction
                await self.sync_invoice_to_transactions(invoice, auth_token, "payment_received")
                
                return {
                    "status": "success",
                    "payment_transaction_id": transaction_data.get("id"),
                    "payment_amount": payment.amount,
                    "invoice_id": invoice.id
                }
                
        except Exception as e:
            logger.error(f"Error syncing payment {payment.id}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "payment_id": payment.id
            }
    
    async def bulk_sync_invoices(
        self, 
        invoices: List[models.Invoice], 
        auth_token: str
    ) -> Dict[str, Any]:
        """Bulk sync multiple invoices"""
        results = {
            "total_invoices": len(invoices),
            "successful_syncs": 0,
            "failed_syncs": 0,
            "errors": []
        }
        
        # Process in batches to avoid overwhelming the service
        batch_size = 10
        for i in range(0, len(invoices), batch_size):
            batch = invoices[i:i+batch_size]
            
            # Process batch concurrently
            tasks = [
                self.sync_invoice_to_transactions(invoice, auth_token, "bulk_sync")
                for invoice in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed_syncs"] += 1
                    results["errors"].append(str(result))
                elif result.get("status") == "success":
                    results["successful_syncs"] += 1
                else:
                    results["failed_syncs"] += 1
                    results["errors"].append(result.get("message", "Unknown error"))
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        return results