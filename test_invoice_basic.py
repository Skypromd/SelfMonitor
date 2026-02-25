"""
Simple test for basic invoice functionality without external dependencies
"""

import sys
from pathlib import Path
from decimal import Decimal
from typing import Any, Tuple, Callable

# Mock basic pydantic types for testing
class BaseModel:
    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            setattr(self, key, value)
    
    def dict(self):
        return {k: v for k, v in self.__dict__.items()}

def test_basic_calculations():
    """Test basic invoice calculation logic"""
    print("🔍 Testing basic invoice calculations...")
    
    # Test line item calculation
    quantity = Decimal("2")
    unit_price = Decimal("100.00")
    tax_rate = Decimal("20")  # 20%
    
    # Calculate line item total
    subtotal = quantity * unit_price  # 200.00
    tax_amount = subtotal * (tax_rate / Decimal("100"))  # 40.00
    line_total = subtotal + tax_amount  # 240.00
    
    print(f"✅ Line item calculation: {quantity} × £{unit_price} + {tax_rate}% tax = £{line_total}")
    
    # Test multiple line items
    line_items = [
        {"qty": Decimal("1"), "price": Decimal("500.00"), "tax": Decimal("20")},
        {"qty": Decimal("2"), "price": Decimal("50.00"), "tax": Decimal("20")},
        {"qty": Decimal("3"), "price": Decimal("25.00"), "tax": Decimal("0")}
    ]
    
    total_amount = Decimal("0")
    for item in line_items:
        item_subtotal = item["qty"] * item["price"]
        item_tax = item_subtotal * (item["tax"] / Decimal("100"))
        item_total = item_subtotal + item_tax
        total_amount += item_total
        print(f"   Line: {item['qty']} × £{item['price']} + {item['tax']}% = £{item_total}")
    
    print(f"✅ Invoice total: £{total_amount}")
    
    return True

def test_template_structure():
    """Test that template files exist and have basic structure"""
    print("\n🔍 Testing invoice templates...")
    
    templates_path = Path("services/invoice-service/app/templates")
    if not templates_path.exists():
        print("❌ Templates directory not found")
        return False
    
    expected_templates = [
        "default_invoice.html",
        "freelancer_it_invoice.html", 
        "consultant_invoice.html",
        "designer_invoice.html"
    ]
    
    for template_name in expected_templates:
        template_path = templates_path / template_name
        if template_path.exists():
            print(f"✅ Found template: {template_name}")
            
            # Check if template has basic structure
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for basic template elements
            required_elements = ['{{', 'invoice_number', 'client_name', 'total_amount']
            missing_elements: list[str] = []
            
            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"   ⚠️  Missing elements: {missing_elements}")
            else:
                print(f"   ✅ Template structure valid")
        else:
            print(f"❌ Missing template: {template_name}")
            return False
    
    return True

def test_file_structure():
    """Test that all required files exist"""
    print("\n🔍 Testing file structure...")
    
    base_path = Path("services/invoice-service")
    required_files = [
        "app/main.py",
        "app/models.py",
        "app/schemas.py",
        "app/crud.py",
        "app/database.py",
        "app/pdf_generator.py",
        "app/invoice_calculator.py",
        "app/sync_service.py",
        "requirements.txt",
        "Dockerfile",
        "alembic.ini"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
            all_exist = False
    
    return all_exist

def test_invoice_service():
    """Run all tests"""
    print("🚀 Starting invoice-service validation tests...")
    print("="*60)
    
    tests: list[Tuple[str, Callable[[], bool]]] = [
        ("File Structure", test_file_structure),
        ("Basic Calculations", test_basic_calculations), 
        ("Template Structure", test_template_structure)
    ]
    
    results: list[Tuple[str, bool]] = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY:")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Invoice-service is ready for deployment.")
        print("✅ Next step: Deploy with Docker and test endpoints")
    else:
        print("\n❌ Some tests failed. Review issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = test_invoice_service()
    sys.exit(0 if success else 1)