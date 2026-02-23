import importlib
import os


def _extend_tests_namespace() -> None:
    root = os.path.dirname(__file__)
    services_dir = os.path.join(root, "services")
    if not os.path.isdir(services_dir):
        return

    try:
        tests_pkg = importlib.import_module("tests")
    except Exception:
        return

    tests_path = getattr(tests_pkg, "__path__", None)
    if tests_path is None:
        return

    for entry in os.listdir(services_dir):
        candidate = os.path.join(services_dir, entry, "tests")
        if os.path.isdir(candidate) and candidate not in tests_path:
            tests_path.append(candidate)


_extend_tests_namespace()
