def enqueue_job(queue, payload):
    """Append background jobs to the queue."""
    queue.append({"payload": payload, "attempts": 0})


def retry_job(job, maximum=3):
    if job["attempts"] >= maximum:
        raise RuntimeError("retry budget exhausted")
    return {**job, "attempts": job["attempts"] + 1}
