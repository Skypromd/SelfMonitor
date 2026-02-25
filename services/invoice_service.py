# Invoice service package alias for proper imports
# Alias invoice-service to invoice_service for Python compatibility

import sys
from pathlib import Path

# Get the actual service directory
service_dir = Path(__file__).parent / "invoice-service"

# Add service to path with underscored name for imports
if service_dir.exists():
    sys.modules[__name__ + ".invoice_service"] = sys.modules[__name__]
    
# Re-export the app module
try:
    from .invoice_service import app as invoice_service_app
except ImportError:
    # Fallback for development/testing
    pass