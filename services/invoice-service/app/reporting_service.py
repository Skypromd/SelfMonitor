from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract
from dataclasses import dataclass
import httpx  # For external service integration

from . import models, schemas, crud

@dataclass
class RevenueDataPoint:
    period: str
    revenue: Decimal
    invoice_count: int
    avg_invoice_value: Decimal

class InvoiceReportingService:
    """Service for generating invoice reports and analytics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_summary_report(
        self, 
        user_id: str, 
        start_date: date, 
        end_date: date,
        company_id: Optional[str] = None
    ) -> schemas.InvoiceReportSummary:
        """Generate comprehensive invoice summary report"""
        
        # Base query filter
        base_filter = and_(
            models.Invoice.user_id == user_id,
            models.Invoice.invoice_date >= start_date,
            models.Invoice.invoice_date <= end_date
        )
        
        if company_id:
            base_filter = and_(base_filter, models.Invoice.company_id == company_id)
        
        # Get basic statistics
        stats_result = await self.db.execute(
            select(
                func.count(models.Invoice.id).label('total_invoices'),
                func.sum(models.Invoice.total_amount).label('total_billed'),
                func.sum(models.Invoice.paid_amount).label('total_collected'),
                func.avg(models.Invoice.total_amount).label('avg_invoice_value')
            )
            .where(base_filter)
        )
        stats = stats_result.first()
        
        # Status breakdown
        status_result = await self.db.execute(
            select(
                models.Invoice.status,
                func.count(models.Invoice.id).label('count'),
                func.sum(models.Invoice.total_amount).label('amount')
            )
            .where(base_filter)
            .group_by(models.Invoice.status)
        )
        
        status_summary = {}
        for row in status_result.fetchall():
            status_summary[row.status.value] = {
                'count': row.count,
                'amount': float(row.amount or 0)
            }
        
        # Category breakdown
        category_result = await self.db.execute(
            select(
                models.InvoiceLineItem.category,
                func.sum(models.InvoiceLineItem.total_amount).label('total_amount'),
                func.count(models.InvoiceLineItem.id).label('item_count')
            )
            .join(models.Invoice)
            .where(base_filter)
            .where(models.InvoiceLineItem.category.isnot(None))
            .group_by(models.InvoiceLineItem.category)
        )
        
        category_breakdown = {}
        for row in category_result.fetchall():
            category_breakdown[row.category] = {
                'total_amount': float(row.total_amount or 0),
                'item_count': row.item_count
            }
        
        # Top clients
        client_result = await self.db.execute(
            select(
                models.Invoice.client_name,
                func.count(models.Invoice.id).label('invoice_count'),
                func.sum(models.Invoice.total_amount).label('total_amount')
            )
            .where(base_filter)
            .group_by(models.Invoice.client_name)
            .order_by(func.sum(models.Invoice.total_amount).desc())
            .limit(10)
        )
        
        top_clients = []
        for row in client_result.fetchall():
            top_clients.append({
                'client_name': row.client_name,
                'invoice_count': row.invoice_count,
                'total_amount': float(row.total_amount or 0)
            })
        
        return schemas.InvoiceReportSummary(
            period_start=start_date,
            period_end=end_date,
            total_invoices=stats.total_invoices or 0,
            total_billed=float(stats.total_billed or 0),
            total_collected=float(stats.total_collected or 0),
            outstanding_amount=float((stats.total_billed or 0) - (stats.total_collected or 0)),
            avg_invoice_value=float(stats.avg_invoice_value or 0),
            status_summary=status_summary,
            category_breakdown=category_breakdown,
            top_clients=top_clients
        )
    
    async def generate_aging_report(
        self, 
        user_id: str, 
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate accounts receivable aging report"""
        
        # Get all unpaid/partially paid invoices
        base_filter = and_(
            models.Invoice.user_id == user_id,
            models.Invoice.status.in_([
                schemas.InvoiceStatus.SENT,
                schemas.InvoiceStatus.PARTIALLY_PAID,
                schemas.InvoiceStatus.OVERDUE
            ])
        )
        
        if company_id:
            base_filter = and_(base_filter, models.Invoice.company_id == company_id)
        
        result = await self.db.execute(
            select(models.Invoice)
            .where(base_filter)
            .order_by(models.Invoice.due_date.asc())
        )
        
        invoices = result.scalars().all()
        
        aging_buckets = {
            'current': {'count': 0, 'amount': 0},
            '1-30_days': {'count': 0, 'amount': 0},
            '31-60_days': {'count': 0, 'amount': 0}, 
            '61-90_days': {'count': 0, 'amount': 0},
            '90+_days': {'count': 0, 'amount': 0}
        }
        
        today = date.today()
        
        for invoice in invoices:
            outstanding = invoice.total_amount - (invoice.paid_amount or Decimal(0))
            
            if not invoice.due_date or invoice.due_date >= today:
                bucket = 'current'
            else:
                days_overdue = (today - invoice.due_date).days
                if days_overdue <= 30:
                    bucket = '1-30_days'
                elif days_overdue <= 60:
                    bucket = '31-60_days'
                elif days_overdue <= 90:
                    bucket = '61-90_days'
                else:
                    bucket = '90+_days'
            
            aging_buckets[bucket]['count'] += 1
            aging_buckets[bucket]['amount'] += float(outstanding)
        
        return {
            'generated_at': datetime.now(timezone.utc),
            'aging_buckets': aging_buckets,
            'total_outstanding': sum(bucket['amount'] for bucket in aging_buckets.values())
        }
    
    async def generate_revenue_report(
        self, 
        user_id: str, 
        start_date: date, 
        end_date: date,
        grouping: str = "month"
    ) -> List[Dict[str, Any]]:
        """Generate revenue analytics over time"""
        
        if grouping == "day":
            date_trunc = func.date(models.Invoice.invoice_date)
            date_format = "%Y-%m-%d"
        elif grouping == "week":
            date_trunc = func.date_trunc('week', models.Invoice.invoice_date)
            date_format = "Week of %Y-%m-%d"
        elif grouping == "quarter":
            date_trunc = func.date_trunc('quarter', models.Invoice.invoice_date) 
            date_format = "Q%q %Y"
        else:  # month
            date_trunc = func.date_trunc('month', models.Invoice.invoice_date)
            date_format = "%B %Y"
        
        result = await self.db.execute(
            select(
                date_trunc.label('period'),
                func.sum(models.Invoice.total_amount).label('revenue'),
                func.count(models.Invoice.id).label('invoice_count'),
                func.avg(models.Invoice.total_amount).label('avg_invoice_value')
            )
            .where(
                and_(
                    models.Invoice.user_id == user_id,
                    models.Invoice.invoice_date >= start_date,
                    models.Invoice.invoice_date <= end_date
                )
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        
        revenue_data = []
        for row in result.fetchall():
            period_date = row.period
            if isinstance(period_date, str):
                period_str = period_date
            else:
                period_str = period_date.strftime(date_format)
            
            revenue_data.append({
                'period': period_str,
                'revenue': float(row.revenue or 0),
                'invoice_count': row.invoice_count,
                'avg_invoice_value': float(row.avg_invoice_value or 0)
            })
        
        return revenue_data
    
    async def generate_tax_report(
        self, 
        user_id: str, 
        tax_year: int
    ) -> Dict[str, Any]:
        """Generate tax report for HMRC filing"""
        
        start_date = date(tax_year, 4, 6)  # UK tax year starts April 6th
        end_date = date(tax_year + 1, 4, 5)
        
        # Get all tax data for the year
        result = await self.db.execute(
            select(
                func.sum(models.Invoice.subtotal).label('total_income'),
                func.sum(models.Invoice.tax_amount).label('total_vat_charged')
            )
            .where(
                and_(
                    models.Invoice.user_id == user_id,
                    models.Invoice.invoice_date >= start_date,
                    models.Invoice.invoice_date <= end_date,
                    models.Invoice.status.in_([
                        schemas.InvoiceStatus.SENT,
                        schemas.InvoiceStatus.PAID,
                        schemas.InvoiceStatus.PARTIALLY_PAID
                    ])
                )
            )
        )
        
        tax_summary = result.first()
        
        # VAT breakdown by rate
        vat_breakdown_result = await self.db.execute(
            select(
                models.InvoiceLineItem.tax_rate,
                func.sum(models.InvoiceLineItem.total_amount).label('net_amount'),
                func.sum(models.InvoiceLineItem.tax_amount).label('vat_amount')
            )
            .join(models.Invoice)
            .where(
                and_(
                    models.Invoice.user_id == user_id,
                    models.Invoice.invoice_date >= start_date,
                    models.Invoice.invoice_date <= end_date,
                    models.Invoice.status.in_([
                        schemas.InvoiceStatus.SENT,
                        schemas.InvoiceStatus.PAID,
                        schemas.InvoiceStatus.PARTIALLY_PAID
                    ])
                )
            )
            .group_by(models.InvoiceLineItem.tax_rate)
        )
        
        vat_breakdown = {}
        for row in vat_breakdown_result.fetchall():
            rate = row.tax_rate or 0
            vat_breakdown[f"{rate}%"] = {
                'net_amount': float(row.net_amount or 0),
                'vat_amount': float(row.vat_amount or 0)
            }
        
        return {
            'tax_year': f"{tax_year}/{tax_year + 1}",
            'period_start': start_date,
            'period_end': end_date,
            'total_income': float(tax_summary.total_income or 0),
            'total_vat_charged': float(tax_summary.total_vat_charged or 0),
            'vat_breakdown': vat_breakdown,
            'generated_at': datetime.utcnow()
        }
    
    async def sync_to_transactions_service(self, user_id: str, invoice_id: Optional[str] = None) -> Dict[str, Any]:
        """Sync invoice data to main transactions service for comprehensive reporting"""
        
        base_filter = models.Invoice.user_id == user_id
        if invoice_id:
            base_filter = and_(base_filter, models.Invoice.id == invoice_id)
        
        # Get invoices to sync
        invoices_result = await self.db.execute(
            select(models.Invoice)
            .options(
                selectinload(models.Invoice.line_items),
                selectinload(models.Invoice.payments)
            )
            .where(base_filter)
        )
        
        invoices = invoices_result.scalars().all()
        
        sync_data = []
        for invoice in invoices:
            # Convert invoice to transaction format
            transaction_data = {
                'id': f"invoice-{invoice.id}",
                'user_id': user_id,
                'type': 'income',
                'category': 'Business Income',
                'subcategory': 'Invoice Payment',
                'amount': float(invoice.total_amount),
                'description': f"Invoice {invoice.invoice_number} - {invoice.client_name}",
                'date': invoice.invoice_date.isoformat(),
                'metadata': {
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'client_name': invoice.client_name,
                    'status': invoice.status.value,
                    'currency': invoice.currency
                }
            }
            
            # Add detailed line items
            for line_item in invoice.line_items:
                line_transaction = {
                    'id': f"invoice-line-{line_item.id}",
                    'user_id': user_id,
                    'type': 'income',
                    'category': line_item.category or 'Business Income',
                    'subcategory': line_item.description,
                    'amount': float(line_item.total_amount),
                    'description': f"{line_item.description} (Invoice {invoice.invoice_number})",
                    'date': invoice.invoice_date.isoformat(),
                    'metadata': {
                        'invoice_id': invoice.id,
                        'line_item_id': line_item.id,
                        'quantity': float(line_item.quantity),
                        'unit_price': float(line_item.unit_price),
                        'tax_rate': float(line_item.tax_rate or 0)
                    }
                }
                sync_data.append(line_transaction)
        
        # TODO: Send to transactions service via HTTP API
        # For now, return the sync payload
        return {
            'status': 'prepared',
            'invoice_count': len(invoices),
            'transaction_count': len(sync_data),
            'sync_data': sync_data
        }
    
    async def generate_self_employment_report(self, user_id: str, tax_year: int) -> Dict[str, Any]:
        """Generate comprehensive report for self-employed tax filing"""
        
        start_date = date(tax_year, 4, 6)
        end_date = date(tax_year + 1, 4, 5)
        
        # Get invoice summary
        summary = await self.generate_summary_report(user_id, start_date, end_date)
        
        # Get category breakdown for expense categorization
        category_result = await self.db.execute(
            select(
                models.InvoiceLineItem.category,
                func.sum(models.InvoiceLineItem.total_amount).label('total'),
                func.count(models.InvoiceLineItem.id).label('count')
            )
            .join(models.Invoice)
            .where(
                and_(
                    models.Invoice.user_id == user_id,
                    models.Invoice.invoice_date >= start_date,
                    models.Invoice.invoice_date <= end_date
                )
            )
            .group_by(models.InvoiceLineItem.category)
        )
        
        income_by_category = {}
        for row in category_result.fetchall():
            if row.category:
                income_by_category[row.category] = {
                    'total': float(row.total),
                    'count': row.count
                }
        
        return {
            'tax_year': f"{tax_year}/{tax_year + 1}",
            'summary': summary,
            'income_by_category': income_by_category,
            'recommended_actions': [
                'Ensure all business expenses are recorded in the expense tracker',
                'Review and update client contact information',
                'Set up recurring invoices for regular clients',
                'Consider quarterly VAT returns if applicable'
            ]
        }