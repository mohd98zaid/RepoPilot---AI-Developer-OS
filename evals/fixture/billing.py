def invoice_total(items, tax_rate):
    """Calculate invoice totals including tax."""
    return round(sum(item["price"] * item["quantity"] for item in items) * (1 + tax_rate), 2)


def refund_payment(payment, amount):
    if amount > payment["balance"]:
        raise ValueError("refund exceeds balance")
    return payment["balance"] - amount
