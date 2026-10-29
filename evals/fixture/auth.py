import hashlib


def authenticate_user(username, password, stored_hash):
    """Verify login credentials against a stored password digest."""
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash and bool(username)


def revoke_session(sessions, session_id):
    return sessions.pop(session_id, None)
