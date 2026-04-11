import logging

logger = logging.getLogger(__name__)


def setup_telemetry(app):
    """Configures OpenTelemetry when dependencies are installed (optional in tests/minimal venv)."""
    try:
        from opentelemetry.distro import OpenTelemetryDistro
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        OpenTelemetryDistro().configure()
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry instrumentation enabled.")
    except ImportError:
        logger.warning(
            "OpenTelemetry not installed; skipping instrumentation (install opentelemetry-distro for prod)."
        )
