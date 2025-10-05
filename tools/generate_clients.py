import subprocess
import os

# A map of service OpenAPI specs to their desired client library output paths
CLIENT_MAP = {
    "transactions-service": "libs/clients/python/transactions_client",
    # We can add more services here in the future
    # "auth-service": "libs/clients/python/auth_client",
}

def generate_clients():
    """
    This script generates typed Python clients from OpenAPI specifications.
    It should be run from the root of the project.
    """
    print("Starting client generation...")
    for service, output_path in CLIENT_MAP.items():
        print(f"Generating client for '{service}'...")

        openapi_spec_path = os.path.join("services", service, "openapi.yaml")

        if not os.path.exists(openapi_spec_path):
            print(f"Warning: OpenAPI spec not found at {openapi_spec_path}. Skipping.")
            continue

        # Ensure the output directory exists
        os.makedirs(output_path, exist_ok=True)

        # Command to generate the client
        # We use --meta=setup to generate a setup.py, making it an installable package
        command = [
            "openapi-python-client",
            "generate",
            "--path",
            openapi_spec_path,
            "--config",
            "tools/client_gen_config.yaml",
            "--meta",
            "setup",
        ]

        try:
            # We need to run this command within the output directory context
            subprocess.run(command, check=True, cwd=output_path)
            print(f"Successfully generated client for '{service}' in {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error generating client for '{service}': {e}")
        except FileNotFoundError:
            print("Error: 'openapi-python-client' command not found.")
            print("Please install it: pip install -r tools/requirements.txt")
            break

if __name__ == "__main__":
    generate_clients()
