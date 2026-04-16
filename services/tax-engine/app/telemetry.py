import logging

logger = logging.getLogger(__name__)


def setup_telemetry(app):
    """Configures OpenTelemetry when optional instrumentation packages are installed."""
    try:
        from opentelemetry.distro import OpenTelemetryDistro
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError as exc:
        logger.warning("OpenTelemetry skipped (%s).", exc)
        return
    OpenTelemetryDistro().configure()
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
