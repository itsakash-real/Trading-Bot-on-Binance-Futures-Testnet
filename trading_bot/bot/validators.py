def get_quantity_precision(filters: list[dict]) -> int:
    for f in filters:
        if f["filterType"] == "LOT_SIZE":
            step = f["stepSize"]
            if "." in step:
                return len(step.split(".")[1].rstrip("0"))
            return 0
    raise ValueError("LOT_SIZE filter not found")


def get_price_precision(filters: list[dict]) -> int:
    for f in filters:
        if f["filterType"] == "PRICE_FILTER":
            tick = f["tickSize"]
            if "." in tick:
                return len(tick.split(".")[1].rstrip("0"))
            return 0
    raise ValueError("PRICE_FILTER filter not found")


def validate_symbol(s: str) -> None:
    if not isinstance(s, str) or not s.strip():
        raise ValueError("Symbol must be a non-empty string, e.g. BTCUSDT")
    if not s.strip().isalnum():
        raise ValueError(f"Symbol must be alphanumeric, got: {s}")


def validate_side(s: str) -> None:
    if s.upper() not in ("BUY", "SELL"):
        raise ValueError(f"Side must be BUY or SELL, got: {s}")


def validate_order_type(t: str) -> None:
    if t.upper() not in ("MARKET", "LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"):
        raise ValueError(f"Order type must be MARKET or LIMIT, got: {t}")


def validate_quantity(q: str) -> float:
    try:
        val = float(q)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity must be a number, got: {q}")
    if val <= 0:
        raise ValueError(f"Quantity must be positive, got: {q}")
    return val


def validate_price(p: str) -> float:
    try:
        val = float(p)
    except (TypeError, ValueError):
        raise ValueError(f"Price must be a number, got: {p}")
    if val <= 0:
        raise ValueError(f"Price must be positive, got: {p}")
    return val
