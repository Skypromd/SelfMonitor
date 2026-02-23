"""
Logging configuration for SelfMonitor Recommendation Engine
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any, Dict

from app.core.config import settings


def setup_logging():
    """Setup logging configuration."""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Logging configuration
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s | %(name)s | %(message)s"
            },
            "json": {
                "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "simple",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": "logs/recommendation_engine.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "metrics_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": "logs/metrics.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file"]
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"]
            },
            "uvicorn.error": {
                "level": "INFO"
            },
            "uvicorn.access": {
                "level": "INFO"
            },
            "recommendation_engine": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "metrics": {
                "level": "INFO",
                "handlers": ["metrics_file"],
                "propagate": False
            }
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(logging_config)
    
    # Set specific loggers to appropriate levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    
    # Create application logger
    logger = logging.getLogger("recommendation_engine")
    logger.info(f"🔧 Logging configured with level: {settings.LOG_LEVEL}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"recommendation_engine.{name}")


def log_performance(func_name: str, execution_time: float, **kwargs: Any) -> None:
    """Log performance metrics."""
    metrics_logger = logging.getLogger("metrics")
    metrics_data: Dict[str, Any] = {
        "type": "performance",
        "function": func_name,
        "execution_time": execution_time,
        **kwargs
    }
    metrics_logger.info(str(metrics_data))


def log_recommendation_event(user_id: str, event_type: str, **kwargs: Any) -> None:
    """Log recommendation events for analytics."""
    metrics_logger = logging.getLogger("metrics")
    event_data: Dict[str, Any] = {
        "type": "recommendation_event",
        "user_id": user_id,
        "event_type": event_type,
        **kwargs
    }
    metrics_logger.info(str(event_data))