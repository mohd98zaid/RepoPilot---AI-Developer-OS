def format_notification(name, subject):
    """Format the email notification greeting and subject."""
    return f"Hello {name}, {subject}"


def unsubscribe(subscribers, address):
    return [item for item in subscribers if item != address]
