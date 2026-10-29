def paginate(items, page, page_size):
    """Return a page of results using offset pagination."""
    if page < 1 or page_size < 1:
        raise ValueError("invalid pagination bounds")
    start = (page - 1) * page_size
    return items[start : start + page_size]


def cursor_after(rows, identifier):
    return [row for row in rows if row["id"] > identifier]
