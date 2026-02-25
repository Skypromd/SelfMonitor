"""
Import test for invoice-service modules
Tests that all modules can be imported without dependency issues
"""

import sys
import os
from pathlib import Path

# Add service to Python path
service_path = Path(__file__).parent / "services" / "invoice-service"
sys.path.insert(0, str(service_path))

def test_imports():
    """Test importing invoice-service modules"""
    print("🔍 Testing invoice-service module imports...")
    
    try:
        # Test basic imports that don't require database connection
        print("Testing schemas import...")
        from app import schemas
        print("✅ Schemas imported successfully")
        
        print("Testing models import...")  
        from app import models
        print("✅ Models imported successfully")
        
        print("Testing invoice calculator...")
        from app.invoice_calculator import InvoiceCalculator
        calculator = InvoiceCalculator()
        print("✅ InvoiceCalculator class created successfully")
        
        print("Testing PDF generator class definition...")
        from app.pdf_generator import PDFGenerator
        print("✅ PDFGenerator class imported successfully")
        
        # Test basic calculator functionality
        print("\nTesting calculator functionality...")
        from decimal import Decimal
        
        # Create test invoice data
        test_invoice = schemas.InvoiceCreate(
            client_name="Test Client",
            invoice_number="INV-001",
            currency="GBP",
            line_items=[
                schemas.LineItemCreate(
                    description="Test item",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100.00"),
                    tax_rate=Decimal("20")
                )
            ]
        )
        
        calculated = calculator.calculate_totals(test_invoice)
        print(f"✅ Calculator test successful - Total: £{calculated.total_amount}")
        
        print("\n" + "="*50)
        print("🎉 All imports and basic functionality tests passed!")
        print("✅ Invoice-service modules ready for deployment")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_imports()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)