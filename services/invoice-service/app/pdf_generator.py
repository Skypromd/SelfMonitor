import os
import jinja2
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from weasyprint import HTML, CSS
from pathlib import Path

from . import schemas

class PDFGenerator:
    """Generate professional PDF invoices with customizable templates"""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent / "templates"
        self.static_dir = Path(__file__).parent / "static"
        self.output_dir = Path(os.getenv("PDF_OUTPUT_DIR", "/tmp/invoices"))
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.jinja_env.filters['currency'] = self._format_currency
        self.jinja_env.filters['date'] = self._format_date
        self.jinja_env.filters['percentage'] = self._format_percentage
    
    async def generate_invoice_pdf(
        self,
        invoice: schemas.Invoice,
        template: Optional[schemas.InvoiceTemplate] = None,
        custom_styling: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate PDF for invoice and return file path"""
        
        # Prepare template context
        context = self._prepare_template_context(invoice, template)
        
        # Select template
        template_name = "default_invoice.html"
        if template and template.template_content:
            # Use custom template (would need to be saved as file)
            template_name = f"custom_{template.id}.html"
        
        # Render HTML
        html_content = self._render_template(template_name, context, custom_styling)
        
        # Generate PDF
        pdf_path = await self._generate_pdf_from_html(html_content, invoice.invoice_number)
        
        return str(pdf_path)
    
    def _prepare_template_context(self, invoice: schemas.Invoice, template: Optional[schemas.InvoiceTemplate]) -> Dict[str, Any]:
        """Prepare context data for template rendering"""
        
        # Calculate aging if overdue
        aging_days = 0
        if invoice.due_date:
            aging_days = max(0, (datetime.now().date() - invoice.due_date).days)
        
        # Company information (would come from user profile in real app)
        company_info = {
            "name": "Your Company Ltd",
            "address": "123 Business Street",
            "city": "London",
            "postal_code": "SW1A 1AA",
            "country": "United Kingdom",
            "phone": "+44 20 7946 0958",
            "email": "hello@yourcompany.com",
            "website": "www.yourcompany.com",
            "vat_number": "GB123456789",
            "company_number": "12345678"
        }
        
        # Override with template company info if available
        if template and template.company_details:
            company_info.update(template.company_details)
        
        return {
            "invoice": invoice,
            "company": company_info,
            "generated_at": datetime.utcnow(),
            "aging_days": aging_days,
            "is_overdue": aging_days > 0,
            "payment_url": f"https://pay.selfmonitor.com/invoice/{invoice.id}",
            "qr_code_url": f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://pay.selfmonitor.com/invoice/{invoice.id}"
        }
    
    def _render_template(self, template_name: str, context: Dict[str, Any], custom_styling: Optional[Dict[str, Any]] = None) -> str:
        """Render HTML template with context"""
        try:
            template = self.jinja_env.get_template(template_name)
        except jinja2.TemplateNotFound:
            # Fallback to default template
            template = self.jinja_env.get_template("default_invoice.html")
        
        # Add custom styling to context
        if custom_styling:
            context['custom_styling'] = custom_styling
        
        return template.render(**context)
    
    async def _generate_pdf_from_html(self, html_content: str, invoice_number: str) -> Path:
        """Convert HTML to PDF using WeasyPrint"""
        
        # Output file path
        filename = f"invoice-{invoice_number}-{int(datetime.utcnow().timestamp())}.pdf"
        pdf_path = self.output_dir / filename
        
        # CSS styling
        css_content = self._get_default_css()
        
        # Generate PDF
        html_doc = HTML(string=html_content, base_url=str(self.template_dir))
        css_doc = CSS(string=css_content)
        
        html_doc.write_pdf(str(pdf_path), stylesheets=[css_doc])
        
        return pdf_path
    
    def _get_default_css(self) -> str:
        """Get default CSS styling for invoice PDFs"""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Helvetica', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
        }
        
        .header {
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
        }
        
        .company-info {
            text-align: right;
        }
        
        .company-name {
            font-size: 20pt;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .invoice-title {
            font-size: 28pt;
            font-weight: bold;
            color: #e74c3c;
            margin-bottom: 20px;
        }
        
        .invoice-details {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }
        
        .client-info {
            max-width: 45%;
        }
        
        .invoice-meta {
            text-align: right;
        }
        
        .invoice-meta table {
            margin-left: auto;
        }
        
        .invoice-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }
        
        .invoice-table th {
            background-color: #34495e;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: bold;
        }
        
        .invoice-table td {
            padding: 10px 8px;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .invoice-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .text-right {
            text-align: right;
        }
        
        .text-center {
            text-align: center;
        }
        
        .totals-table {
            width: 300px;
            margin-left: auto;
            margin-bottom: 30px;
        }
        
        .totals-table td {
            padding: 8px 12px;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .total-row {
            background-color: #34495e;
            color: white;
            font-weight: bold;
            font-size: 12pt;
        }
        
        .payment-info {
            background-color: #f8f9fa;
            padding: 20px;
            border-left: 4px solid #3498db;
            margin-bottom: 20px;
        }
        
        .overdue-notice {
            background-color: #fff5f5;
            border: 2px solid #e74c3c;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #34495e;
            font-size: 9pt;
            color: #666;
        }
        
        .qr-code {
            float: right;
            margin-left: 20px;
        }
        
        .currency {
            font-family: 'Courier New', monospace;
        }
        """
    
    def _format_currency(self, value: Decimal, currency: str = "GBP") -> str:
        """Format decimal as currency"""
        if currency == "GBP":
            return f"£{value:,.2f}"
        elif currency == "USD":
            return f"${value:,.2f}"
        elif currency == "EUR":
            return f"€{value:,.2f}"
        else:
            return f"{value:,.2f} {currency}"
    
    def _format_date(self, value, format_string: str = "%d %B %Y") -> str:
        """Format date"""
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value.strftime(format_string)
    
    def _format_percentage(self, value: Decimal) -> str:
        """Format decimal as percentage"""
        return f"{value:.1f}%"
    
    def create_default_template(self) -> str:
        """Create and return the default invoice template HTML"""
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice {{ invoice.invoice_number }}</title>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="logo">
            {% if company.logo_url %}
                <img src="{{ company.logo_url }}" alt="{{ company.name }}" style="max-height: 80px;">
            {% endif %}
        </div>
        <div class="company-info">
            <div class="company-name">{{ company.name }}</div>
            <div>{{ company.address }}</div>
            <div>{{ company.city }}, {{ company.postal_code }}</div>
            <div>{{ company.country }}</div>
            {% if company.phone %}<div>Tel: {{ company.phone }}</div>{% endif %}
            {% if company.email %}<div>Email: {{ company.email }}</div>{% endif %}
            {% if company.vat_number %}<div>VAT: {{ company.vat_number }}</div>{% endif %}
        </div>
    </div>
    
    <!-- Invoice Title -->
    <div class="invoice-title">INVOICE</div>
    
    <!-- Overdue Notice -->
    {% if is_overdue %}
    <div class="overdue-notice">
        <strong>OVERDUE NOTICE:</strong> This invoice is {{ aging_days }} days overdue. Please arrange payment immediately.
    </div>
    {% endif %}
    
    <!-- Invoice Details -->
    <div class="invoice-details">
        <div class="client-info">
            <h3>Bill To:</h3>
            <strong>{{ invoice.client_name }}</strong><br>
            {% if invoice.client_email %}{{ invoice.client_email }}<br>{% endif %}
            {% if invoice.client_address %}
                {{ invoice.client_address | nl2br }}
            {% endif %}
        </div>
        <div class="invoice-meta">
            <table>
                <tr><td><strong>Invoice Number:</strong></td><td>{{ invoice.invoice_number }}</td></tr>
                <tr><td><strong>Invoice Date:</strong></td><td>{{ invoice.invoice_date | date }}</td></tr>
                {% if invoice.due_date %}<tr><td><strong>Due Date:</strong></td><td>{{ invoice.due_date | date }}</td></tr>{% endif %}
                {% if invoice.po_number %}<tr><td><strong>PO Number:</strong></td><td>{{ invoice.po_number }}</td></tr>{% endif %}
                <tr><td><strong>Status:</strong></td><td>{{ invoice.status.value.title() }}</td></tr>
            </table>
        </div>
    </div>
    
    <!-- Line Items -->
    <table class="invoice-table">
        <thead>
            <tr>
                <th>Description</th>
                <th class="text-center">Qty</th>
                <th class="text-right">Unit Price</th>
                <th class="text-right">Tax Rate</th>
                <th class="text-right">Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for item in invoice.line_items %}
            <tr>
                <td>
                    {{ item.description }}
                    {% if item.category %}<br><small>{{ item.category }}</small>{% endif %}
                </td>
                <td class="text-center">{{ item.quantity }}</td>
                <td class="text-right currency">{{ item.unit_price | currency(invoice.currency) }}</td>
                <td class="text-right">{% if item.tax_rate %}{{ item.tax_rate | percentage }}{% else %}-{% endif %}</td>
                <td class="text-right currency">{{ item.total_amount | currency(invoice.currency) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <!-- Totals -->
    <table class="totals-table">
        <tr>
            <td>Subtotal:</td>
            <td class="text-right currency">{{ invoice.subtotal | currency(invoice.currency) }}</td>
        </tr>
        {% if invoice.discount_amount and invoice.discount_amount > 0 %}
        <tr>
            <td>Discount ({{ invoice.discount_percentage }}%):</td>
            <td class="text-right currency">-{{ invoice.discount_amount | currency(invoice.currency) }}</td>
        </tr>
        {% endif %}
        <tr>
            <td>Tax:</td>
            <td class="text-right currency">{{ invoice.tax_amount | currency(invoice.currency) }}</td>
        </tr>
        <tr class="total-row">
            <td>Total:</td>
            <td class="text-right currency">{{ invoice.total_amount | currency(invoice.currency) }}</td>
        </tr>
        {% if invoice.paid_amount and invoice.paid_amount > 0 %}
        <tr>
            <td>Paid:</td>
            <td class="text-right currency">-{{ invoice.paid_amount | currency(invoice.currency) }}</td>
        </tr>
        <tr class="total-row">
            <td>Balance Due:</td>
            <td class="text-right currency">{{ (invoice.total_amount - invoice.paid_amount) | currency(invoice.currency) }}</td>
        </tr>
        {% endif %}
    </table>
    
    <!-- Payment Information -->
    <div class="payment-info">
        <h3>Payment Information</h3>
        <p><strong>Payment Terms:</strong> {% if invoice.payment_terms %}Net {{ invoice.payment_terms }} days{% else %}Due on receipt{% endif %}</p>
        {% if company.bank_details %}
        <p><strong>Bank Transfer:</strong><br>
        {{ company.bank_details | nl2br }}
        </p>
        {% endif %}
        <p><strong>Online Payment:</strong> <a href="{{ payment_url }}">{{ payment_url }}</a></p>
        
        <div class="qr-code">
            <img src="{{ qr_code_url }}" alt="QR Code for payment" style="width: 100px; height: 100px;">
        </div>
    </div>
    
    <!-- Notes -->
    {% if invoice.notes %}
    <div style="margin-bottom: 30px;">
        <h3>Notes</h3>
        <p>{{ invoice.notes | nl2br }}</p>
    </div>
    {% endif %}
    
    <!-- Footer -->
    <div class="footer">
        <p>Thank you for your business!</p>
        <p>Generated on {{ generated_at | date("%d %B %Y at %H:%M") }}</p>
    </div>
</body>
</html>
"""
        return template_content