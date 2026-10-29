import os


def load_configuration():
    """Read environment configuration for the service port."""
    return {"port": int(os.getenv("PORT", "8080"))}


def validate_port(port):
    if not 1 <= port <= 65535:
        raise ValueError("port out of range")
