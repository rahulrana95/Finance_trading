"""Number formatting shared by messages."""


def inr(value: float) -> str:
    """Whole rupees with Indian grouping: 2000000 -> '20,00,000'."""
    digits = str(abs(round(value)))
    head, tail = digits[:-3], digits[-3:]
    groups: list[str] = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ("-" if value < 0 else "") + ",".join([*groups, tail])
