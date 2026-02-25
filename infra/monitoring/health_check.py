#!/usr/bin/env python3
"""
Health check script for monitoring container
"""

import sys
import requests

def check_health():
    try:
        # Check if metrics server is running
        response = requests.get('http://localhost:8000', timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

if __name__ == "__main__":
    if check_health():
        sys.exit(0)
    else:
        sys.exit(1)