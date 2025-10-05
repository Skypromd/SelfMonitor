from opentelemetry.distro import OpenTelemetryDistro
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_telemetry(app):
    """Configures OpenTelemetry for the application."""
    # This will automatically configure the exporter to send traces to
    # an OTLP collector, which Jaeger is configured to be.
    # Environment variables like OTEL_EXPORTER_OTLP_ENDPOINT can be used for configuration.
    OpenTelemetryDistro().configure()

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    print("OpenTelemetry instrumentation complete.")
