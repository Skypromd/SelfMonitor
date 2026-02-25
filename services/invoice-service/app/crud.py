from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload
from uuid import uuid4

from . import models, schemas
from .invoice_calculator import InvoiceCalculator

# === INVOICE CRUD OPERATIONS ===

async def create_invoice(
    db: AsyncSession, 
    user_id: str, 
    invoice_data: schemas.InvoiceCreate
) -> models.Invoice:
    """Create new invoice with line items"""
    
    # Generate invoice number if not provided
    if not invoice_data.invoice_number:
        invoice_data.invoice_number = await generate_invoice_number(db, user_id)
    
    # Create invoice object
    db_invoice = models.Invoice(
        id=str(uuid4()),
        user_id=user_id,
        company_id=invoice_data.company_id,
        invoice_number=invoice_data.invoice_number,
        client_name=invoice_data.client_name,
        client_email=invoice_data.client_email,
        client_address=invoice_data.client_address,
        invoice_date=invoice_data.invoice_date or date.today(),
        due_date=invoice_data.due_date,
        payment_terms=invoice_data.payment_terms,
        po_number=invoice_data.po_number,
        subtotal=invoice_data.subtotal,
        tax_amount=invoice_data.tax_amount,
        total_amount=invoice_data.total_amount,
        discount_percentage=invoice_data.discount_percentage,
        discount_amount=invoice_data.discount_amount,
        currency=invoice_data.currency or "GBP",
        notes=invoice_data.notes,
        status=schemas.InvoiceStatus.DRAFT
    )
    
    db.add(db_invoice)
    await db.flush()  # Get the ID
    
    # Add line items
    for line_item_data in invoice_data.line_items:
        db_line_item = models.InvoiceLineItem(
            id=str(uuid4()),
            invoice_id=db_invoice.id,
            description=line_item_data.description,
            category=line_item_data.category,
            quantity=line_item_data.quantity,
            unit_price=line_item_data.unit_price,
            total_amount=line_item_data.total_amount,
            tax_rate=line_item_data.tax_rate,
            tax_amount=line_item_data.tax_amount
        )
        db.add(db_line_item)
    
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice

async def get_invoice(db: AsyncSession, invoice_id: str, user_id: str) -> Optional[models.Invoice]:
    """Get invoice by ID for specific user"""
    result = await db.execute(
        select(models.Invoice)
        .options(
            selectinload(models.Invoice.line_items),
            selectinload(models.Invoice.payments)
        )
        .where(and_(
            models.Invoice.id == invoice_id,
            models.Invoice.user_id == user_id
        ))
    )
    return result.scalar_one_or_none()

async def get_invoices_filtered(
    db: AsyncSession, 
    user_id: str, 
    filters: schemas.InvoiceReportFilters,
    skip: int = 0, 
    limit: int = 50
) -> List[models.Invoice]:
    """Get filtered list of invoices"""
    query = select(models.Invoice).where(models.Invoice.user_id == user_id)
    
    # Apply filters
    if filters.start_date:
        query = query.where(models.Invoice.invoice_date >= filters.start_date)
    
    if filters.end_date:
        query = query.where(models.Invoice.invoice_date <= filters.end_date)
    
    if filters.status:
        query = query.where(models.Invoice.status.in_(filters.status))
    
    if filters.client_name:
        query = query.where(models.Invoice.client_name.ilike(f"%{filters.client_name}%"))
    
    if filters.company_id:
        query = query.where(models.Invoice.company_id == filters.company_id)
    
    # Add pagination and ordering
    query = query.order_by(desc(models.Invoice.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

async def update_invoice(
    db: AsyncSession, 
    invoice_id: str, 
    invoice_update: schemas.InvoiceUpdate
) -> models.Invoice:
    """Update invoice"""
    result = await db.execute(
        select(models.Invoice).where(models.Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        return None
    
    # Update fields
    update_data = invoice_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)
    
    await db.commit()
    await db.refresh(invoice)
    return invoice

async def delete_invoice(db: AsyncSession, invoice_id: str) -> bool:
    """Delete invoice and related records"""
    result = await db.execute(
        select(models.Invoice).where(models.Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        return False
    
    await db.delete(invoice)
    await db.commit()
    return True

async def update_invoice_pdf_path(db: AsyncSession, invoice_id: str, pdf_path: str):
    """Update invoice PDF file path"""
    result = await db.execute(
        select(models.Invoice).where(models.Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if invoice:
        invoice.pdf_file_path = pdf_path
        await db.commit()

async def generate_invoice_number(db: AsyncSession, user_id: str) -> str:
    """Generate next invoice number for user"""
    # Get current year
    current_year = datetime.now().year
    
    # Find highest invoice number for current year
    result = await db.execute(
        select(func.max(models.Invoice.invoice_number))
        .where(and_(
            models.Invoice.user_id == user_id,
            models.Invoice.invoice_number.like(f"INV-{current_year}-%")
        ))
    )
    last_number = result.scalar() or f"INV-{current_year}-0000"
    
    # Extract sequence number and increment
    try:
        sequence = int(last_number.split("-")[2]) + 1
    except (IndexError, ValueError):
        sequence = 1
    
    return f"INV-{current_year}-{sequence:04d}"

# === PAYMENT OPERATIONS ===

async def create_payment(
    db: AsyncSession, 
    invoice_id: str, 
    payment_data: schemas.InvoicePaymentCreate
) -> models.InvoicePayment:
    """Create payment record"""
    db_payment = models.InvoicePayment(
        id=str(uuid4()),
        invoice_id=invoice_id,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date or date.today(),
        payment_method=payment_data.payment_method,
        reference_number=payment_data.reference_number,
        notes=payment_data.notes
    )
    
    db.add(db_payment)
    await db.commit()
    await db.refresh(db_payment)
    return db_payment

async def update_invoice_status_from_payments(db: AsyncSession, invoice_id: str):
    """Update invoice status based on payments received"""
    # Get invoice with payments
    result = await db.execute(
        select(models.Invoice)
        .options(selectinload(models.Invoice.payments))
        .where(models.Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        return
    
    # Calculate total payments
    total_paid = sum(payment.amount for payment in invoice.payments)
    invoice.paid_amount = total_paid
    
    # Update status
    if total_paid >= invoice.total_amount:
        invoice.status = schemas.InvoiceStatus.PAID
    elif total_paid > 0:
        invoice.status = schemas.InvoiceStatus.PARTIALLY_PAID
    
    await db.commit()

# === TEMPLATE OPERATIONS ===

async def create_template(
    db: AsyncSession, 
    user_id: str, 
    template_data: schemas.InvoiceTemplateCreate
) -> models.InvoiceTemplate:
    """Create invoice template"""
    db_template = models.InvoiceTemplate(
        id=str(uuid4()),
        user_id=user_id,
        name=template_data.name,
        description=template_data.description,
        template_type=template_data.template_type,
        template_content=template_data.template_content,
        default_line_items=template_data.default_line_items,
        company_details=template_data.company_details,
        styling_options=template_data.styling_options,
        is_default=template_data.is_default or False
    )
    
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)
    return db_template

async def get_templates(
    db: AsyncSession, 
    user_id: str, 
    company_id: Optional[str] = None
) -> List[models.InvoiceTemplate]:
    """Get user's invoice templates"""
    query = select(models.InvoiceTemplate).where(
        or_(
            models.InvoiceTemplate.user_id == user_id,
            models.InvoiceTemplate.is_system_template == True
        )
    )
    
    result = await db.execute(query.order_by(asc(models.InvoiceTemplate.name)))
    return result.scalars().all()

async def get_template(
    db: AsyncSession, 
    template_id: str, 
    user_id: str
) -> Optional[models.InvoiceTemplate]:
    """Get specific template"""
    result = await db.execute(
        select(models.InvoiceTemplate).where(
            and_(
                models.InvoiceTemplate.id == template_id,
                or_(
                    models.InvoiceTemplate.user_id == user_id,
                    models.InvoiceTemplate.is_system_template == True
                )
            )
        )
    )
    return result.scalar_one_or_none()

async def update_template(
    db: AsyncSession, 
    template_id: str, 
    template_update: schemas.InvoiceTemplateUpdate
) -> models.InvoiceTemplate:
    """Update template"""
    result = await db.execute(
        select(models.InvoiceTemplate).where(models.InvoiceTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        return None
    
    # Update fields
    update_data = template_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    return template

# === REPORTING AND ANALYTICS ===

async def get_invoice_categories(db: AsyncSession, user_id: str) -> List[str]:
    """Get unique categories used in invoices"""
    result = await db.execute(
        select(models.InvoiceLineItem.category)
        .join(models.Invoice)
        .where(models.Invoice.user_id == user_id)
        .where(models.InvoiceLineItem.category.isnot(None))
        .distinct()
    )
    return [row[0] for row in result.fetchall()]

async def get_invoice_summary_stats(
    db: AsyncSession, 
    user_id: str, 
    start_date: date, 
    end_date: date
) -> Dict[str, Any]:
    """Get summary statistics for invoices"""
    
    # Total invoices and amounts
    result = await db.execute(
        select(
            func.count(models.Invoice.id).label('total_invoices'),
            func.sum(models.Invoice.total_amount).label('total_amount'),
            func.sum(models.Invoice.paid_amount).label('total_paid')
        )
        .where(
            and_(
                models.Invoice.user_id == user_id,
                models.Invoice.invoice_date >= start_date,
                models.Invoice.invoice_date <= end_date
            )
        )
    )
    summary = result.first()
    
    # Status breakdown
    status_result = await db.execute(
        select(
            models.Invoice.status,
            func.count(models.Invoice.id).label('count'),
            func.sum(models.Invoice.total_amount).label('amount')
        )
        .where(
            and_(
                models.Invoice.user_id == user_id,
                models.Invoice.invoice_date >= start_date,
                models.Invoice.invoice_date <= end_date
            )
        )
        .group_by(models.Invoice.status)
    )
    
    status_breakdown = {}
    for row in status_result.fetchall():
        status_breakdown[row.status] = {
            'count': row.count,
            'amount': float(row.amount or 0)
        }
    
    return {
        'total_invoices': summary.total_invoices or 0,
        'total_amount': float(summary.total_amount or 0),
        'total_paid': float(summary.total_paid or 0),
        'outstanding_amount': float((summary.total_amount or 0) - (summary.total_paid or 0)),
        'status_breakdown': status_breakdown
    }

# === SYSTEM TEMPLATE INITIALIZATION ===

async def create_system_templates(db: AsyncSession):
    """Create default system templates for self-employed users"""
    
    templates = [
        {
            "name": "Фрилансер - IT Услуги",
            "description": "Шаблон для IT фрилансеров (программирование, веб-разработка)",
            "template_type": "freelancer_it",
            "default_line_items": [
                {
                    "description": "Разработка веб-приложения",
                    "category": "Веб-разработка",
                    "quantity": 1,
                    "unit_price": 50.00,
                    "tax_rate": 20.0
                }
            ]
        },
        {
            "name": "Консультант", 
            "description": "Шаблон для консультационных услуг",
            "template_type": "consultant",
            "default_line_items": [
                {
                    "description": "Консультационные услуги",
                    "category": "Консалтинг",
                    "quantity": 1,
                    "unit_price": 100.00,
                    "tax_rate": 20.0
                }
            ]
        },
        {
            "name": "Дизайнер",
            "description": "Шаблон для дизайнерских услуг",
            "template_type": "designer",
            "default_line_items": [
                {
                    "description": "Дизайн логотипа",
                    "category": "Графический дизайн",
                    "quantity": 1,
                    "unit_price": 300.00,
                    "tax_rate": 20.0
                }
            ]
        },
        {
            "name": "Переводчик",
            "description": "Шаблон для переводческих услуг",
            "template_type": "translator",
            "default_line_items": [
                {
                    "description": "Перевод документов",
                    "category": "Переводческие услуги",
                    "quantity": 1000,
                    "unit_price": 0.05,
                    "tax_rate": 20.0
                }
            ]
        },
        {
            "name": "Маркетолог",
            "description": "Шаблон для маркетинговых услуг",
            "template_type": "marketer", 
            "default_line_items": [
                {
                    "description": "Маркетинговая стратегия",
                    "category": "Маркетинг",
                    "quantity": 1,
                    "unit_price": 500.00,
                    "tax_rate": 20.0
                }
            ]
        }
    ]
    
    for template_data in templates:
        # Check if template already exists
        existing = await db.execute(
            select(models.InvoiceTemplate).where(
                and_(
                    models.InvoiceTemplate.name == template_data["name"],
                    models.InvoiceTemplate.is_system_template == True
                )
            )
        )
        
        if not existing.scalar_one_or_none():
            template = models.InvoiceTemplate(
                id=str(uuid4()),
                user_id=None,  # System template
                name=template_data["name"],
                description=template_data["description"],
                template_type=template_data["template_type"],
                default_line_items=template_data["default_line_items"],
                is_system_template=True,
                is_default=False
            )
            db.add(template)
    
    await db.commit()