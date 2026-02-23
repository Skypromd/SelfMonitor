"""
OpenTelemetry configuration for SelfMonitor microservices
Production-ready distributed tracing setup
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.jaeger import JaegerPropagator

logger = logging.getLogger(__name__)

class TelemetryConfig:
    """OpenTelemetry configuration for SelfMonitor services"""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        
        # Environment configuration
        self.jaeger_endpoint = os.getenv(
            "JAEGER_ENDPOINT", 
            "http://jaeger-collector:14268/api/traces"
        )
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.enable_tracing = os.getenv("ENABLE_TRACING", "true").lower() == "true"
        
        # Sampling configuration
        self.trace_sample_rate = float(os.getenv("TRACE_SAMPLE_RATE", "0.1"))  # 10% sampling
        
    def setup_tracing(self) -> None:
        """Initialize OpenTelemetry tracing for the service"""
        
        if not self.enable_tracing:
            logger.info("Tracing disabled via ENABLE_TRACING=false")
            return
            
        try:
            # Create resource with service information
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "service.environment": self.environment,
                "service.namespace": "selfmonitor"
            })
            
            # Configure tracer provider
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)
            
            # Configure Jaeger exporter
            jaeger_exporter = JaegerExporter(
                collector_endpoint=self.jaeger_endpoint,
            )
            
            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            # Set up propagators for cross-service tracing
            set_global_textmap(CompositeHTTPPropagator([
                B3MultiFormat(),
                JaegerPropagator()
            ]))
            
            logger.info(f"OpenTelemetry tracing initialized for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")
            
    def instrument_fastapi(self, app) -> None:
        """Instrument FastAPI application with auto-tracing"""
        if self.enable_tracing:
            FastAPIInstrumentor.instrument_app(
                app, 
                tracer_provider=trace.get_tracer_provider(),
                excluded_urls="/health,/metrics"  # Don't trace health checks
            )
            logger.info("FastAPI instrumentation enabled")
            
    def instrument_libraries(self) -> None:
        """Instrument common libraries for automatic tracing"""
        if not self.enable_tracing:
            return
            
        try:
            # HTTP client instrumentation
            HTTPXClientInstrumentor().instrument()
            
            # Redis instrumentation  
            RedisInstrumentor().instrument()
            
            # SQLAlchemy instrumentation
            SQLAlchemyInstrumentor().instrument()
            
            logger.info("Library instrumentation completed")
            
        except Exception as e:
            logger.error(f"Failed to instrument libraries: {e}")

def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for manual span creation"""
    return trace.get_tracer(name)

def trace_function(operation_name: str):
    """Decorator to automatically trace function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not trace.get_tracer_provider():
                return func(*args, **kwargs)
                
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Example usage for async functions
def trace_async_function(operation_name: str):
    """Decorator to automatically trace async function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not trace.get_tracer_provider():
                return await func(*args, **kwargs)
                
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(operation_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

# Utility for adding custom attributes to spans
def add_span_attributes(**attributes):
    """Add custom attributes to the current span"""
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)