from opentelemetry.distro import OpenTelemetryDistro
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_telemetry(app):
    """Configures OpenTelemetry for the application."""
    OpenTelemetryDistro().configure()
    FastAPIInstrumentor.instrument_app(app)
    print("OpenTelemetry instrumentation complete.")
