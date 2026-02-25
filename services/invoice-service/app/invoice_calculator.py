from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from datetime import datetime, date

from . import schemas

class InvoiceCalculator:
    """Handles invoice calculations - tax, totals, discounts, currency conversion"""
    
    # UK VAT rates
    VAT_RATES = {
        "standard": Decimal("0.20"),  # 20%
        "reduced": Decimal("0.05"),   # 5%
        "zero": Decimal("0.00"),      # 0%
        "exempt": Decimal("0.00")     # Exempt
    }
    
    # Currency conversion rates (simplified - in production would use live rates)
    CURRENCY_RATES = {
        "GBP": Decimal("1.00"),
        "USD": Decimal("1.27"),
        "EUR": Decimal("1.16")
    }
    
    def calculate_totals(self, invoice_data: schemas.InvoiceCreate) -> schemas.InvoiceCreate:
        """Calculate all invoice totals and tax amounts"""
        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        
        # Calculate line item totals
        for line_item in invoice_data.line_items:
            line_total = self.calculate_line_total(line_item)
            line_tax = self.calculate_line_tax(line_item)
            
            # Update line item with calculated values
            line_item.total_amount = line_total
            line_item.tax_amount = line_tax
            
            subtotal += line_total
            total_tax += line_tax
        
        # Apply invoice-level discount
        discount_amount = Decimal("0.00")
        if invoice_data.discount_percentage and invoice_data.discount_percentage > 0:
            discount_amount = subtotal * (invoice_data.discount_percentage / 100)
            subtotal -=oscount_amount
        
        # Calculate final total
        total_amount = subtotal + total_tax
        
        # Update invoice totals
        invoice_data.subtotal = self.round_currency(subtotal)
        invoice_data.tax_amount = self.round_currency(total_tax)
        invoice_data.total_amount = self.round_currency(total_amount)
        invoice_data.discount_amount = self.round_currency(discount_amount)
        
        return invoice_data
    
    def calculate_line_total(self, line_item: schemas.InvoiceLineItemCreate) -> Decimal:
        """Calculate total for a single line item (quantity * unit_price)"""
        if not line_item.unit_price or not line_item.quantity:
            return Decimal("0.00")
        
        total = Decimal(str(line_item.unit_price)) * Decimal(str(line_item.quantity))
        return self.round_currency(total)
    
    def calculate_line_tax(self, line_item: schemas.InvoiceLineItemCreate) -> Decimal:
        """Calculate VAT/tax for a single line item"""
        line_total = self.calculate_line_total(line_item)
        
        if not line_item.tax_rate:
            return Decimal("0.00")
        
        tax_rate = Decimal(str(line_item.tax_rate)) / 100
        tax_amount = line_total * tax_rate
        
        return self.round_currency(tax_amount)
    
    def get_vat_rate(self, vat_type: str) -> Decimal:
        """Get UK VAT rate by type"""
        return self.VAT_RATES.get(vat_type.lower(), Decimal("0.20"))
    
    def convert_currency(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """Convert amount between currencies"""
        if from_currency == to_currency:
            return amount
        
        from_rate = self.CURRENCY_RATES.get(from_currency, Decimal("1.00"))
        to_rate = self.CURRENCY_RATES.get(to_currency, Decimal("1.00"))
        
        # Convert to GBP first, then to target currency
        gbp_amount = amount / from_rate
        converted_amount = gbp_amount * to_rate
        
        return self.round_currency(converted_amount)
    
    def round_currency(self, amount: Decimal) -> Decimal:
        """Round to 2 decimal places for currency"""
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_payment_terms_due_date(self, invoice_date: date, payment_terms: int) -> date:
        """Calculate due date based on payment terms (net days)"""
        from datetime import timedelta
        return invoice_date + timedelta(days=payment_terms)
    
    def calculate_late_fees(self, invoice: schemas.Invoice, as_of_date: Optional[date] = None) -> Decimal:
        """Calculate late payment fees if invoice is overdue"""
        if not as_of_date:
            as_of_date = date.today()
        
        if not invoice.due_date or as_of_date <= invoice.due_date:
            return Decimal("0.00")
        
        if invoice.status in [schemas.InvoiceStatus.PAID, schemas.InvoiceStatus.CANCELLED]:
            return Decimal("0.00")
        
        # Calculate days overdue
        days_overdue = (as_of_date - invoice.due_date).days
        
        if days_overdue <= 0:
            return Decimal("0.00")
        
        # UK statutory interest rate (8% + base rate, simplified to 8.5%)
        annual_rate = Decimal("0.085")
        daily_rate = annual_rate / 365
        
        outstanding_amount = invoice.total_amount - (invoice.paid_amount or Decimal("0.00"))
        late_fee = outstanding_amount * daily_rate * days_overdue
        
        return self.round_currency(late_fee)
    
    def validate_invoice_data(self, invoice_data: schemas.InvoiceCreate) -> List[str]:
        """Validate invoice data before creation"""
        errors = []
        
        # Basic validations
        if not invoice_data.client_name or not invoice_data.client_name.strip():
            errors.append("Client name is required")
        
        if not invoice_data.line_items:
            errors.append("At least one line item is required")
        
        # Validate line items
        for i, line_item in enumerate(invoice_data.line_items):
            if not line_item.description or not line_item.description.strip():
                errors.append(f"Line item {i+1}: Description is required")
            
            if not line_item.unit_price or line_item.unit_price <= 0:
                errors.append(f"Line item {i+1}: Unit price must be greater than 0")
            
            if not line_item.quantity or line_item.quantity <= 0:
                errors.append(f"Line item {i+1}: Quantity must be greater than 0")
            
            if line_item.tax_rate and (line_item.tax_rate < 0 or line_item.tax_rate > 100):
                errors.append(f"Line item {i+1}: Tax rate must be between 0 and 100")
        
        # Validate dates
        if invoice_data.due_date and invoice_data.invoice_date:
            if invoice_data.due_date < invoice_data.invoice_date:
                errors.append("Due date cannot be before invoice date")
        
        # Validate discount
        if invoice_data.discount_percentage:
            if invoice_data.discount_percentage < 0 or invoice_data.discount_percentage > 100:
                errors.append("Discount percentage must be between 0 and 100")
        
        return errors
    
    def calculate_recurring_dates(self, start_date: date, frequency: str, occurrences: int) -> List[date]:
        """Calculate future dates for recurring invoices"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        dates = [start_date]
        current_date = start_date
        
        for _ in range(occurrences - 1):
            if frequency == "weekly":
                current_date += timedelta(weeks=1)
            elif frequency == "monthly":
                current_date += relativedelta(months=1)
            elif frequency == "quarterly":
                current_date += relativedelta(months=3)
            elif frequency == "yearly":
                current_date += relativedelta(years=1)
            else:
                break
            
            dates.append(current_date)
        
        return dates
    
    def get_invoice_aging_bucket(self, invoice: schemas.Invoice, as_of_date: Optional[date] = None) -> str:
        """Determine which aging bucket an invoice falls into"""
        if not as_of_date:
            as_of_date = date.today()
        
        if invoice.status == schemas.InvoiceStatus.PAID:
            return "paid"
        
        if not invoice.due_date:
            return "current"
        
        days_overdue = (as_of_date - invoice.due_date).days
        
        if days_overdue <= 0:
            return "current"
        elif days_overdue <= 30:
            return "1-30_days"
        elif days_overdue <= 60:
            return "31-60_days"
        elif days_overdue <= 90:
            return "61-90_days"
        else:
            return "90+_days"