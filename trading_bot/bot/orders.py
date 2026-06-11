from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from trading_bot.bot.client import BinanceClient
from trading_bot.bot.validators import (
    get_price_precision,
    get_quantity_precision,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


def place_market_order(
    client: BinanceClient, symbol: str, side: str, quantity: str
) -> dict:
    validate_symbol(symbol)
    side = side.upper()
    validate_side(side)
    qty = validate_quantity(quantity)

    info = client.get_exchange_info(symbol)
    qty_precision = get_quantity_precision(info["filters"])
    qty = round(qty, qty_precision)

    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": str(qty),
    }

    return client._request("POST", "/fapi/v1/order", params=params, signed=True)


def place_limit_order(
    client: BinanceClient, symbol: str, side: str, quantity: str, price: str
) -> dict:
    validate_symbol(symbol)
    side = side.upper()
    validate_side(side)
    qty = validate_quantity(quantity)
    prc = validate_price(price)

    info = client.get_exchange_info(symbol)
    filters = info["filters"]
    qty_precision = get_quantity_precision(filters)
    price_precision = get_price_precision(filters)

    qty = round(qty, qty_precision)
    prc = round(prc, price_precision)

    params = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": str(qty),
        "price": str(prc),
    }

    return client._request("POST", "/fapi/v1/order", params=params, signed=True)


def format_order_response(response: dict) -> None:
    console = Console()
    status = response.get("status", "UNKNOWN")

    table = Table(title="Order Response")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    fields = [
        ("orderId", str(response.get("orderId", "N/A"))),
        ("symbol", response.get("symbol", "N/A")),
        ("side", response.get("side", "N/A")),
        ("type", response.get("type", "N/A")),
        ("status", status),
        ("executedQty", response.get("executedQty", "N/A")),
        ("avgPrice", response.get("avgPrice", "N/A")),
    ]

    for field, value in fields:
        table.add_row(field, value)

    console.print(table)

    if status in ("NEW", "FILLED", "PARTIALLY_FILLED"):
        console.print(Panel("Order placed successfully", style="green"))
    else:
        console.print(Panel(f"Order failed — status: {status}", style="red"))
