def line_amounts(unit_price_minor: int, quantity: int, tax_rate_bps: int) -> tuple[int, int, int]:
    subtotal = unit_price_minor * quantity
    tax = (subtotal * tax_rate_bps + 5000) // 10000
    return subtotal, tax, subtotal + tax


def format_minor(amount_minor: int, currency_code: str = "USD") -> str:
    sign = "-" if amount_minor < 0 else ""
    value = abs(amount_minor)
    return f"{sign}{currency_code} {value // 100}.{value % 100:02d}"
