"""
WeasyPrint needs GTK/Pango on the host; CI and Windows dev often lack them.
Stub the module so FastAPI app imports for API tests without PDF rendering.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

if "weasyprint" not in sys.modules:
    _wp = ModuleType("weasyprint")
    _wp.HTML = MagicMock()
    _wp.CSS = MagicMock()
    sys.modules["weasyprint"] = _wp
