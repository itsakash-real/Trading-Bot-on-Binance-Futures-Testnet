import argparse
import sys

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from trading_bot.bot.client import BinanceClient
from trading_bot.bot.logging_config import get_logger
from trading_bot.bot.orders import (
    format_order_response,
    place_limit_order,
    place_market_order,
)
from trading_bot.bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

console = Console()


def _prompt_with_validation(prompt_text: str, validator, choices: list[str] | None = None) -> str:
    while True:
        value = Prompt.ask(f"[bold cyan]{prompt_text}[/]").strip()
        try:
            validator(value)
            return value
        except ValueError as e:
            console.print(f"  [red]{e}[/]")


def _interactive_mode() -> dict:
    console.print(Panel("Interactive Trading Bot", style="bold green"))
    console.print("Enter order details below:\n")

    symbol = _prompt_with_validation(
        "Symbol (e.g. BTCUSDT)", validate_symbol
    )
    side = _prompt_with_validation(
        "Side [BUY/SELL]", validate_side, ["BUY", "SELL"]
    ).upper()
    order_type = _prompt_with_validation(
        "Order type [MARKET/LIMIT]", validate_order_type, ["MARKET", "LIMIT"]
    ).upper()
    quantity = _prompt_with_validation(
        "Quantity", validate_quantity
    )

    price = None
    if order_type == "LIMIT":
        price = _prompt_with_validation(
            "Price", validate_price
        )

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }


def _run_order(args_or_params: dict) -> None:
    logger = get_logger()

    symbol = args_or_params["symbol"]
    side = args_or_params["side"]
    order_type = args_or_params["order_type"]
    quantity = args_or_params["quantity"]
    price = args_or_params.get("price")

    summary = (
        f"symbol   = {symbol}\n"
        f"side     = {side}\n"
        f"type     = {order_type}\n"
        f"quantity = {quantity}\n"
        + (f"price    = {price}" if price else "")
    )
    console.print(Panel(summary, title="Request Summary", style="bold cyan"))

    try:
        client = BinanceClient()
        if order_type == "MARKET":
            response = place_market_order(client, symbol, side, quantity)
        else:
            response = place_limit_order(client, symbol, side, quantity, price)
        format_order_response(response)
    except ValueError as e:
        logger.error("Validation error: %s", e)
        console.print(Panel(f"[bold red]Validation Error:[/] {e}", style="red"))
    except requests.HTTPError as e:
        logger.error("API error: %s", e)
        msg = f"API returned {e.response.status_code}: {e.response.json().get('msg', str(e))}"
        console.print(Panel(f"[bold red]API Error:[/] {msg}", style="red"))
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(Panel(f"[bold red]Unexpected Error:[/] {e}", style="red"))


def main() -> None:
    is_interactive = len(sys.argv) == 1

    if is_interactive:
        params = _interactive_mode()
        _run_order(params)
        return

    parser = argparse.ArgumentParser(
        description="Trading Bot for Binance Futures Testnet (USDT-M)"
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, help="BUY or SELL")
    parser.add_argument("--type", required=True, dest="order_type", help="MARKET or LIMIT")
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", default=None, help="Limit price (required for LIMIT orders)")

    args = parser.parse_args()

    try:
        validate_symbol(args.symbol)
        validate_side(args.side)
        validate_order_type(args.order_type)
        validate_quantity(args.quantity)
        if args.order_type.upper() == "LIMIT":
            if args.price is None:
                parser.error("--price is required for LIMIT orders")
            validate_price(args.price)
    except ValueError as e:
        parser.error(str(e))

    _run_order({
        "symbol": args.symbol,
        "side": args.side.upper(),
        "order_type": args.order_type.upper(),
        "quantity": args.quantity,
        "price": args.price,
    })


if __name__ == "__main__":
    main()
