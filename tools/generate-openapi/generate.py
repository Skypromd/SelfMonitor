import json
import os
import importlib.util
from fastapi.openapi.utils import get_openapi
import yaml

# This script is a placeholder for a utility that would auto-generate
# OpenAPI schemas from FastAPI application instances.

def generate_schema_for_service(service_name: str):
    """
    Dynamically imports a FastAPI app from a service and generates its OpenAPI schema.
    """
    print(f"Attempting to generate OpenAPI schema for '{service_name}'...")

    app_path = f"../../services/{service_name}/app/main.py"
    if not os.path.exists(app_path):
        print(f"Error: Path not found - {app_path}")
        return

    # Dynamically import the 'app' object from the service's main.py
    try:
        spec = importlib.util.spec_from_file_location("service_app", app_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = getattr(module, "app", None)
    except Exception as e:
        print(f"Error importing module for {service_name}: {e}")
        return

    if not app:
        print(f"Error: Could not find a FastAPI 'app' instance in {app_path}")
        return

    # Generate the schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Save the schema to the service's directory
    output_path = f"../../services/{service_name}/openapi.yaml"
    try:
        with open(output_path, 'w') as f:
            yaml.dump(openapi_schema, f, sort_keys=False)
        print(f"Schema for '{service_name}' generated successfully and saved to: {output_path}")
    except Exception as e:
        print(f"Error writing schema file for {service_name}: {e}")


if __name__ == "__main__":
    # Example usage:
    generate_schema_for_service("auth-service")
    generate_schema_for_service("transactions-service")
