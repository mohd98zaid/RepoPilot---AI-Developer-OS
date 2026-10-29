from pathlib import Path


def resolve_upload(root, filename):
    """Reject upload path traversal outside the storage directory."""
    destination = (Path(root) / filename).resolve()
    if not destination.is_relative_to(Path(root).resolve()):
        raise ValueError("upload path escapes root")
    return destination


def file_checksum(data):
    import hashlib

    return hashlib.sha256(data).hexdigest()
