import json


def record_audit_event(stream, actor, action):
    """Write audit records as JSON lines."""
    stream.write(json.dumps({"actor": actor, "action": action}) + "\n")


def filter_audit_events(events, actor):
    return [event for event in events if event["actor"] == actor]
