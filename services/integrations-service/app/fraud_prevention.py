"""
HMRC Fraud Prevention Headers — mandatory for all MTD API calls.
Spec: https://developer.service.hmrc.gov.uk/guides/fraud-prevention/
"""
import datetime
import os
import platform
import uuid
from typing import Dict


class FraudPreventionHeaders:
    """Generates HMRC-mandated fraud prevention headers."""

    def __init__(self):
        self.vendor_product_name = os.getenv("HMRC_VENDOR_PRODUCT_NAME", "SelfMonitor")
        self.vendor_version = os.getenv("HMRC_VENDOR_VERSION", "1.0.0")

    def generate(
        self,
        *,
        client_ip: str = "",
        client_device_id: str = "",
        user_id: str = "",
        connection_method: str = "DESKTOP_APP_DIRECT",
    ) -> Dict[str, str]:
        """Generate all mandatory fraud prevention headers."""
        headers = {
            "Gov-Client-Connection-Method": connection_method,
            "Gov-Vendor-Product-Name": self.vendor_product_name,
            "Gov-Vendor-Version": f"SelfMonitor={self.vendor_version}",
            "Gov-Vendor-License-IDs": "",
            "Gov-Client-User-IDs": f"selfmonitor={user_id}" if user_id else "",
            "Gov-Client-Timezone": f"UTC+{datetime.datetime.now().astimezone().strftime('%z')[:3]}:00",
            "Gov-Client-Local-IPs": client_ip if client_ip else "",
            "Gov-Client-Device-ID": client_device_id or str(uuid.uuid4()),
            "Gov-Client-User-Agent": f"{platform.system()}/{platform.release()} Python/{platform.python_version()}",
            "Gov-Client-Screens": "width=1920&height=1080&colour-depth=24",
            "Gov-Client-Window-Size": "width=1920&height=1080",
            "Gov-Vendor-Public-IP": "",
            "Gov-Client-Multi-Factor": "",
        }
        return {k: v for k, v in headers.items() if v}
