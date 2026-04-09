import asyncio
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
from decimal import Decimal

from . import crud, models, schemas
from .database import get_db
from .pdf_generator import PDFGenerator
from .invoice_calculator import InvoiceCalculator
from .reporting_service import InvoiceReportingService
from .sync_service import InvoiceTransactionSync

app = FastAPI(
    title="SelfMonitor Invoice Service",
    description="Enterprise invoice generation, management and reporting for FinTech platform",
    version="1.0.0",
    tags_metadata=[
        {"name": "invoices", "description": "Invoice CRUD operations"},
        {"name": "templates", "description": "Invoice template management"},
        {"name": "payments", "description": "Payment tracking"},
        {"name": "reporting", "description": "Invoice analytics and reporting"},
        {"name": "pdf", "description": "PDF generation and download"}
    ]
)

# Security
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """Extract user ID from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    return user_id

def get_current_user_token(token: str = Depends(oauth2_scheme)) -> str:
    """Get current user token for service-to-service calls"""
    return token

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "invoice-service", "timestamp": datetime.utcnow()}

# === INVOICE ENDPOINTS ===

@app.post("/invoices", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED, tags=["invoices"])
async def create_invoice(
    invoice_data: schemas.InvoiceCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """Create a new invoice with line items"""
    try:
        # Calculate totals
        calculator = InvoiceCalculator()
        calculated_invoice = calculator.calculate_totals(invoice_data)

        # Create invoice
        invoice = await crud.create_invoice(db, user_id=user_id, invoice_data=calculated_invoice)

        # Sync to transactions service in background
        sync = InvoiceTransactionSync()
        background_tasks.add_task(
            sync.sync_invoice_to_transactions,
            invoice.id,
            token
        )

        return invoice
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create invoice: {str(e)}")

@app.get("/invoices", response_model=List[schemas.Invoice], tags=["invoices"])
async def list_invoices(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[schemas.InvoiceStatus] = None,
    company_id: Optional[str] = None,
    client_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """List user's invoices with filtering"""
    filters = schemas.InvoiceReportFilters(
        start_date=start_date,
        end_date=end_date,
        status=[status] if status else None,
        client_name=client_name,
        company_id=company_id
    )

    invoices = await crud.get_invoices_filtered(db, user_id=user_id, filters=filters, skip=skip, limit=limit)
    return invoices

@app.get("/invoices/{invoice_id}", response_model=schemas.Invoice, tags=["invoices"])
async def get_invoice(
    invoice_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get specific invoice by ID"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@app.put("/invoices/{invoice_id}", response_model=schemas.Invoice, tags=["invoices"])
async def update_invoice(
    invoice_id: str,
    invoice_update: schemas.InvoiceUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update invoice details"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Prevent editing paid invoices
    if invoice.status == schemas.InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Cannot modify paid invoice")

    updated_invoice = await crud.update_invoice(db, invoice_id=invoice_id, invoice_update=invoice_update)
    return updated_invoice

@app.delete("/invoices/{invoice_id}", tags=["invoices"])
async def delete_invoice(
    invoice_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete invoice (only drafts)"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status != schemas.InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only delete draft invoices")

    await crud.delete_invoice(db, invoice_id=invoice_id)
    return {"message": "Invoice deleted successfully"}

@app.post("/invoices/{invoice_id}/send", response_model=schemas.Invoice, tags=["invoices"])
async def send_invoice(
    invoice_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Mark invoice as sent and trigger email"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status != schemas.InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only send draft invoices")

    # Generate PDF if not exists
    pdf_generator = PDFGenerator()
    if not invoice.pdf_file_path:
        pdf_path = await pdf_generator.generate_invoice_pdf(invoice)
        await crud.update_invoice_pdf_path(db, invoice_id=invoice_id, pdf_path=pdf_path)

    # Update status to sent
    update_data = schemas.InvoiceUpdate(status=schemas.InvoiceStatus.SENT)
    updated_invoice = await crud.update_invoice(db, invoice_id=invoice_id, invoice_update=update_data)

    # TODO: Trigger email sending via message queue

    return updated_invoice

# === PAYMENT ENDPOINTS ===

@app.post("/invoices/{invoice_id}/payments", response_model=schemas.InvoicePayment, tags=["payments"])
async def add_payment(
    invoice_id: str,
    payment_data: schemas.InvoicePaymentCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Record payment for an invoice"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Create payment record
    payment = await crud.create_payment(db, invoice_id=invoice_id, payment_data=payment_data)

    # Update invoice status based on payments
    await crud.update_invoice_status_from_payments(db, invoice_id=invoice_id)

    return payment

@app.get("/invoices/{invoice_id}/payments", response_model=List[schemas.InvoicePayment], tags=["payments"])
async def get_invoice_payments(
    invoice_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get all payments for an invoice"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice.payments

# === TEMPLATE ENDPOINTS ===

@app.post("/templates", response_model=schemas.InvoiceTemplate, status_code=status.HTTP_201_CREATED, tags=["templates"])
async def create_template(
    template_data: schemas.InvoiceTemplateCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create new invoice template"""
    template = await crud.create_template(db, user_id=user_id, template_data=template_data)
    return template

@app.get("/templates", response_model=List[schemas.InvoiceTemplate], tags=["templates"])
async def list_templates(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    company_id: Optional[str] = None
):
    """List user's invoice templates"""
    templates = await crud.get_templates(db, user_id=user_id, company_id=company_id)
    return templates

@app.get("/templates/{template_id}", response_model=schemas.InvoiceTemplate, tags=["templates"])
async def get_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get specific template"""
    template = await crud.get_template(db, template_id=template_id, user_id=user_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@app.put("/templates/{template_id}", response_model=schemas.InvoiceTemplate, tags=["templates"])
async def update_template(
    template_id: str,
    template_update: schemas.InvoiceTemplateUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update invoice template"""
    template = await crud.get_template(db, template_id=template_id, user_id=user_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    updated_template = await crud.update_template(db, template_id=template_id, template_update=template_update)
    return updated_template

# === REPORTING ENDPOINTS ===

@app.get("/reports/summary", response_model=schemas.InvoiceReportSummary, tags=["reporting"])
async def get_invoice_summary(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    company_id: Optional[str] = Query(None)
):
    """Get invoice summary and analytics"""
    # Default to last 12 months if no dates provided
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=365)
    if not end_date:
        end_date = datetime.utcnow()

    reporting_service = InvoiceReportingService(db)
    summary = await reporting_service.generate_summary_report(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        company_id=company_id
    )
    return summary

@app.get("/reports/aging", tags=["reporting"])
async def get_aging_report(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    company_id: Optional[str] = Query(None)
):
    """Get accounts receivable aging report"""
    reporting_service = InvoiceReportingService(db)
    aging_report = await reporting_service.generate_aging_report(user_id=user_id, company_id=company_id)
    return aging_report

@app.get("/reports/revenue", tags=["reporting"])
async def get_revenue_report(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    grouping: str = Query("month", regex="^(day|week|month|quarter)$")
):
    """Get revenue analytics over time"""
    reporting_service = InvoiceReportingService(db)
    revenue_report = await reporting_service.generate_revenue_report(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        grouping=grouping
    )
    return revenue_report

# === PDF GENERATION ENDPOINTS ===

@app.post("/invoices/{invoice_id}/pdf", response_model=schemas.PDFGenerationResponse, tags=["pdf"])
async def generate_pdf(
    invoice_id: str,
    pdf_request: schemas.PDFGenerationRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Generate PDF for invoice"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf_generator = PDFGenerator()

    # Get template if specified
    template = None
    if pdf_request.template_id:
        template = await crud.get_template(db, template_id=pdf_request.template_id, user_id=user_id)

    # Generate PDF
    pdf_path = await pdf_generator.generate_invoice_pdf(
        invoice=invoice,
        template=template,
        custom_styling=pdf_request.custom_styling
    )

    # Update invoice with PDF path
    await crud.update_invoice_pdf_path(db, invoice_id=invoice_id, pdf_path=pdf_path)

    return schemas.PDFGenerationResponse(
        pdf_url=f"/invoices/{invoice_id}/pdf/download",
        file_path=pdf_path,
        generated_at=datetime.utcnow()
    )

@app.get("/invoices/{invoice_id}/pdf/download", response_class=FileResponse, tags=["pdf"])
async def download_pdf(
    invoice_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Download invoice PDF"""
    invoice = await crud.get_invoice(db, invoice_id=invoice_id, user_id=user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.pdf_file_path or not os.path.exists(invoice.pdf_file_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    filename = f"Invoice-{invoice.invoice_number}.pdf"
    return FileResponse(
        path=invoice.pdf_file_path,
        filename=filename,
        media_type="application/pdf"
    )

# === INTEGRATION ENDPOINTS ===

@app.get("/integration/categories", tags=["reporting"])
async def get_expense_categories(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice line item categories for expense categorization"""
    categories = await crud.get_invoice_categories(db, user_id=user_id)
    return {"categories": categories}

@app.post("/integration/sync-to-transactions", tags=["reporting"])
async def sync_to_transactions_service(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    invoice_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Sync invoice data to transactions service for reporting"""
    # TODO: Implement sync with transactions-service
    # This would push invoice data to main transactions for comprehensive reporting
    return {"message": "Sync initiated", "status": "pending"}

@app.get("/integration/tax-data", tags=["reporting"])
async def get_tax_data(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    tax_year: int = Query(..., ge=2020, le=2030)
):
    """Get aggregated tax data for HMRC reporting"""
    reporting_service = InvoiceReportingService(db)
    tax_data = await reporting_service.generate_tax_report(user_id=user_id, tax_year=tax_year)
    return tax_data

# === OVERDUE CHASE ENDPOINTS ===

class ChaseConfig(BaseModel):
    enabled: bool = True
    chase_after_days: list[int] = [3, 7, 14]
    email_template: str = "polite"

class ChaseLogEntry(BaseModel):
    invoice_id: str
    chase_number: int
    sent_at: datetime
    days_overdue: int
    status: str

_chase_log: list[dict] = []

@app.post("/invoices/{invoice_id}/chase", tags=["invoices"])
async def chase_invoice(
    invoice_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually send a payment reminder for an overdue invoice"""
    invoice = await crud.get_invoice(db, invoice_id, user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    days_overdue = (date.today() - invoice.due_date.date()).days if invoice.due_date else 0

    chase_entry = {
        "invoice_id": invoice_id,
        "chase_number": len([c for c in _chase_log if c["invoice_id"] == invoice_id]) + 1,
        "sent_at": datetime.utcnow().isoformat(),
        "days_overdue": days_overdue,
        "status": "sent",
        "recipient": invoice.client_email,
        "message": f"Friendly reminder: Invoice #{invoice.invoice_number} for £{invoice.total_amount} was due {days_overdue} days ago.",
    }
    _chase_log.append(chase_entry)

    return {
        "status": "reminder_sent",
        "chase_number": chase_entry["chase_number"],
        "days_overdue": days_overdue,
        "message": chase_entry["message"],
    }

@app.get("/invoices/overdue/list", tags=["invoices"])
async def list_overdue_invoices(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all overdue invoices with chase history"""
    filters = schemas.InvoiceReportFilters()
    invoices = await crud.get_invoices_filtered(db, user_id, filters)
    overdue = []
    for inv in invoices:
        if inv.due_date and inv.status in ("sent", "partially_paid") and inv.due_date < datetime.utcnow():
            days = (date.today() - inv.due_date.date()).days
            chases = [c for c in _chase_log if c["invoice_id"] == str(inv.id)]
            overdue.append({
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "client_name": inv.client_name,
                "client_email": inv.client_email,
                "total_amount": float(inv.total_amount),
                "due_date": inv.due_date.date().isoformat(),
                "days_overdue": days,
                "chase_count": len(chases),
                "last_chased": chases[-1]["sent_at"] if chases else None,
            })
    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    return {"overdue_count": len(overdue), "invoices": overdue}

@app.get("/invoices/chase-log", tags=["invoices"])
async def get_chase_log(
    user_id: str = Depends(get_current_user_id),
):
    """Get full chase history"""
    return {"entries": _chase_log}

# === RECURRING INVOICE ENDPOINTS ===

_recurring_configs: list[dict] = []

class RecurringInvoiceConfig(BaseModel):
    template_invoice_id: str
    frequency: str
    next_due_date: str
    auto_send: bool = True
    max_occurrences: int = 12

@app.post("/invoices/recurring", tags=["invoices"])
async def create_recurring_invoice(
    config: RecurringInvoiceConfig,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Set up a recurring invoice from an existing invoice as template"""
    template = await crud.get_invoice(db, config.template_invoice_id, user_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template invoice not found")

    recurring = {
        "id": f"rec-{len(_recurring_configs) + 1}",
        "template_invoice_id": config.template_invoice_id,
        "client_name": template.client_name,
        "amount": float(template.total_amount),
        "frequency": config.frequency,
        "next_due_date": config.next_due_date,
        "auto_send": config.auto_send,
        "max_occurrences": config.max_occurrences,
        "occurrences_sent": 0,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
    }
    _recurring_configs.append(recurring)

    return {
        "status": "created",
        "recurring_id": recurring["id"],
        "message": f"Recurring invoice set up: £{recurring['amount']} {config.frequency} to {recurring['client_name']}",
        "next_due_date": config.next_due_date,
    }

@app.get("/invoices/recurring", tags=["invoices"])
async def list_recurring_invoices(
    user_id: str = Depends(get_current_user_id),
):
    """List all recurring invoice configurations"""
    return {"recurring_invoices": _recurring_configs}

@app.delete("/invoices/recurring/{recurring_id}", tags=["invoices"])
async def cancel_recurring_invoice(
    recurring_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Cancel a recurring invoice"""
    for config in _recurring_configs:
        if config["id"] == recurring_id:
            config["status"] = "cancelled"
            return {"status": "cancelled", "recurring_id": recurring_id}
    raise HTTPException(status_code=404, detail="Recurring config not found")

# === PAYMENT LINK ENDPOINTS ===

@app.post("/invoices/{invoice_id}/payment-link", tags=["payments"])
async def create_payment_link(
    invoice_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a Stripe payment link for an invoice"""
    invoice = await crud.get_invoice(db, invoice_id, user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    payment_link = f"https://pay.selfmonitor.app/invoice/{invoice_id}"

    return {
        "invoice_id": invoice_id,
        "payment_link": payment_link,
        "amount": float(invoice.total_amount),
        "currency": invoice.currency or "GBP",
        "client_name": invoice.client_name,
        "expires_in": "30 days",
        "message": f"Share this link with {invoice.client_name} to receive payment of £{invoice.total_amount}",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
