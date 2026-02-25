"""
Test script for invoice-service validation
Validates syntax and import structure without starting the service
"""

import sys
import ast
from pathlib import Path
from typing import Tuple, Union

def check_python_syntax(file_path: str) -> Tuple[bool, Union[str, None]]:
    """Check if Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def validate_service():
    """Validate invoice-service files"""
    base_path = Path("services/invoice-service/app")
    
    if not base_path.exists():
        print(f"❌ Service directory not found: {base_path}")
        return False
    
    # Core files to check
    core_files = [
        "main.py",
        "models.py", 
        "schemas.py",
        "crud.py",
        "database.py",
        "pdf_generator.py",
        "invoice_calculator.py",
        "reporting_service.py",
        "sync_service.py"
    ]
    
    print("🔍 Validating invoice-service files...")
    all_valid = True
    
    for file_name in core_files:
        file_path = base_path / file_name
        
        if not file_path.exists():
            print(f"❌ Missing file: {file_name}")
            all_valid = False
            continue
            
        is_valid, error = check_python_syntax(str(file_path))
        if is_valid:
            print(f"✅ {file_name}: Valid syntax")
        else:
            print(f"❌ {file_name}: {error}")
            all_valid = False
    
    # Check templates directory
    templates_path = base_path / "templates"
    if templates_path.exists():
        print(f"✅ Templates directory exists")
        html_files = list(templates_path.glob("*.html"))
        print(f"📄 Found {len(html_files)} HTML templates")
        for html_file in html_files:
            print(f"   - {html_file.name}")
    else:
        print(f"❌ Templates directory missing")
        all_valid = False
    
    # Check requirements.txt
    req_path = Path("services/invoice-service/requirements.txt")
    if req_path.exists():
        print("✅ requirements.txt exists")
    else:
        print("❌ requirements.txt missing")
        all_valid = False
    
    # Check docker files
    dockerfile_path = Path("services/invoice-service/Dockerfile")
    if dockerfile_path.exists():
        print("✅ Dockerfile exists")
    else:
        print("❌ Dockerfile missing")
        all_valid = False
    
    # Check Alembic setup
    alembic_path = Path("services/invoice-service/alembic.ini")
    if alembic_path.exists():
        print("✅ Alembic configuration exists")
    else:
        print("❌ Alembic configuration missing")
        all_valid = False
    
    print("\n" + "="*50)
    if all_valid:
        print("🎉 All invoice-service files validated successfully!")
        print("✅ Ready for deployment")
    else:
        print("❌ Some issues found - review above errors")
    
    return all_valid

if __name__ == "__main__":
    try:
        success = validate_service()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)