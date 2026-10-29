def apply_discount(price, percentage):
    """Calculate discounted pricing while preventing negative percentages."""
    if not 0 <= percentage <= 100:
        raise ValueError("discount out of range")
    return price * (1 - percentage / 100)


def currency_round(amount):
    return round(amount, 2)
