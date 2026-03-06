# Testing Notes

To keep test runs hermetic and avoid failures from auto-loaded external pytest plugins (for example pytest-flask pulling in Jinja2), root tests now set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` in `conftest.py`. This change only affects test execution and does not touch application runtime.

How to run root tests reliably:

1. Activate the project virtual environment:
   - PowerShell: `& .venv\Scripts\Activate.ps1`
2. Run pytest (root suite):
   - `python -m pytest tests/ -v`

Integration tests (tests/integration) are skipped by default. To run them against a running stack (docker-compose up), set `RUN_INTEGRATION_TESTS=1` and optionally override `API_GATEWAY_URL`.

Service-specific tests can still be run from each service directory with the same commands. No additional environment variables are required beyond those already set in the service tests.
