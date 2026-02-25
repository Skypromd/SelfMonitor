#!/usr/bin/env python3
"""
Enterprise Database Monitor Entrypoint
"""

import os
import sys
from db_monitor import DatabaseMonitor

if __name__ == "__main__":
    try:
        monitor = DatabaseMonitor()
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Monitor failed to start: {e}")
        sys.exit(1)