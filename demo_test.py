# demo_test.py
# Run: python demo_test.py
# Expected runtime: ~15-20 seconds

import os
import sys
import time

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

load_dotenv()

from trading_bot.bot.client import BinanceClient
from trading_bot.bot.orders import (
    format_order_response,
    place_limit_order,
    place_market_order,
)
from trading_bot.bot.validators import (
    get_price_precision,
    get_quantity_precision,
    validate_price,
    validate_quantity,
    validate_side,
)

console = Console()
client = BinanceClient()
results: list[tuple[str, bool]] = []


def record(section: str, passed: bool) -> None:
    results.append((section, passed))


# ────────────────────────────────────────────────────────────────
# 1. ENVIRONMENT CHECK
# ────────────────────────────────────────────────────────────────
console.print(Rule("1. ENVIRONMENT CHECK"))
try:
    key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_SECRET_KEY", "")
    if key and secret:
        console.print(
            f"  API Key     : [green]{key[:4]}{'*' * 12}[/]"
        )
        console.print(
            f"  Secret Key  : [green]{secret[:4]}{'*' * 12}[/]"
        )
    else:
        console.print("  [red]API Key or Secret missing in .env[/]")
    console.print(f"  Base URL    : [cyan]{client.base_url}[/]")
    console.print("  [green]OK[/]")
    record("Environment Check", True)
except Exception as e:
    console.print(f"  [red]FAILED: {e}[/]")
    record("Environment Check", False)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 2. CONNECTIVITY CHECK
# ────────────────────────────────────────────────────────────────
console.print(Rule("2. CONNECTIVITY CHECK"))
try:
    resp = client._request("GET", "/fapi/v1/ping")
    if resp == {}:
        console.print("  [green]OK — Ping successful[/]")
        record("Connectivity Check", True)
    else:
        console.print(f"  [red]FAILED — unexpected response: {resp}[/]")
        record("Connectivity Check", False)
except Exception as e:
    console.print(f"  [red]FAILED — {e}[/]")
    record("Connectivity Check", False)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 3. ACCOUNT BALANCE CHECK
# ────────────────────────────────────────────────────────────────
console.print(Rule("3. ACCOUNT BALANCE CHECK"))
try:
    info = client.get_account_info()
    usdt = None
    for asset in info.get("assets", []):
        if asset.get("asset") == "USDT":
            usdt = asset
            break
    table = Table(title="Account Balance")
    table.add_column("Asset", style="cyan")
    table.add_column("Balance", style="white")
    table.add_column("Available", style="white")
    if usdt:
        table.add_row(
            usdt["asset"],
            usdt.get("walletBalance", "0"),
            usdt.get("availableBalance", "0"),
        )
        console.print(table)
        bal = float(usdt.get("availableBalance", 0))
        if bal == 0:
            console.print("  [yellow]WARNING: USDT balance is 0 — orders may fail[/]")
        console.print("  [green]OK[/]")
    else:
        console.print("  [red]USDT balance not found in account info[/]")
        console.print("  [red]FAILED[/]")
        record("Account Balance Check", False)
        raise RuntimeError("skip success")
    record("Account Balance Check", True)
except Exception as e:
    if "skip success" not in str(e):
        console.print(f"  [red]FAILED — {e}[/]")
        record("Account Balance Check", False)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 4. EXCHANGE INFO CHECK
# ────────────────────────────────────────────────────────────────
console.print(Rule("4. EXCHANGE INFO CHECK"))
try:
    info = client.get_exchange_info("BTCUSDT")
    filters = info["filters"]
    step_size = None
    tick_size = None
    for f in filters:
        if f["filterType"] == "LOT_SIZE":
            step_size = f["stepSize"]
        if f["filterType"] == "PRICE_FILTER":
            tick_size = f["tickSize"]
    qty_prec = get_quantity_precision(filters)
    price_prec = get_price_precision(filters)
    console.print(f"  stepSize        : [cyan]{step_size}[/]")
    console.print(f"  tickSize        : [cyan]{tick_size}[/]")
    console.print(f"  Qty Precision   : [cyan]{qty_prec}[/]")
    console.print(f"  Price Precision : [cyan]{price_prec}[/]")
    console.print("  [green]OK[/]")
    record("Exchange Info Check", True)
except Exception as e:
    console.print(f"  [red]FAILED — {e}[/]")
    record("Exchange Info Check", False)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 5. VALIDATOR CHECK
# ────────────────────────────────────────────────────────────────
console.print(Rule("5. VALIDATOR CHECK"))
validator_passed = 0
validator_total = 6

tests = [
    ("validate_side('HOLD') → ValueError", lambda: validate_side("HOLD"), True),
    ("validate_side('BUY') → pass", lambda: validate_side("BUY"), False),
    ("validate_quantity(-5) → ValueError", lambda: validate_quantity("-5"), True),
    ("validate_quantity(0.001) → pass", lambda: validate_quantity("0.001"), False),
    ("validate_price('abc') → ValueError", lambda: validate_price("abc"), True),
    ("validate_price(50000) → pass", lambda: validate_price("50000"), False),
]

for label, fn, expect_error in tests:
    try:
        fn()
        if expect_error:
            console.print(f"  [red]FAIL[/] — {label}")
            validator_passed -= 1
        else:
            console.print(f"  [green]PASS[/] — {label}")
            validator_passed += 1
    except ValueError:
        if expect_error:
            console.print(f"  [green]PASS[/] — {label}")
            validator_passed += 1
        else:
            console.print(f"  [red]FAIL[/] — {label}")
            validator_passed -= 1

validator_all = validator_passed == validator_total
record("Validator Check", validator_all)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 6. MARKET ORDER (LIVE)
# ────────────────────────────────────────────────────────────────
console.print(Rule("6. MARKET ORDER (LIVE)"))
try:
    summary = (
        "symbol   = BTCUSDT\n"
        "side     = BUY\n"
        "type     = MARKET\n"
        "quantity = 0.001\n"
    )
    console.print(Panel(summary, title="Request Summary", style="bold cyan"))
    resp = place_market_order(client, "BTCUSDT", "BUY", "0.001")
    format_order_response(resp)
    console.print("  [green]OK[/]")
    record("Market Order", True)
except Exception as e:
    console.print(f"  [red]FAILED — {e}[/]")
    record("Market Order", False)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 7. LIMIT ORDER (LIVE)
# ────────────────────────────────────────────────────────────────
console.print(Rule("7. LIMIT ORDER (LIVE)"))
try:
    summary = (
        "symbol   = BTCUSDT\n"
        "side     = BUY\n"
        "type     = LIMIT\n"
        "quantity = 0.001\n"
        "price    = 50000\n"
    )
    console.print(Panel(summary, title="Request Summary", style="bold cyan"))
    resp = place_limit_order(client, "BTCUSDT", "BUY", "0.001", "50000")
    format_order_response(resp)
    console.print("  [green]OK[/]")
    record("Limit Order", True)
except Exception as e:
    console.print(f"  [red]FAILED — {e}[/]")
    record("Limit Order", False)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 8. LOG FILE CHECK
# ────────────────────────────────────────────────────────────────
console.print(Rule("8. LOG FILE CHECK"))
try:
    log_path = "logs/trading_bot.log"
    if not os.path.exists(log_path):
        console.print("  [red]Log file not found[/]")
        record("Log File Check", False)
    else:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        tail = "".join(lines[-5:]).rstrip()
        console.print(Panel(tail, title=f"Last 5 of {total} lines"))
        console.print(f"  Total lines: [cyan]{total}[/]")
        console.print("  [green]OK[/]")
        record("Log File Check", True)
except Exception as e:
    console.print(f"  [red]FAILED — {e}[/]")
    record("Log File Check", False)
time.sleep(1)

# ────────────────────────────────────────────────────────────────
# 9. FINAL SUMMARY TABLE
# ────────────────────────────────────────────────────────────────
console.print(Rule("9. FINAL SUMMARY"))

table = Table(title="Demo Test Results")
table.add_column("Check", style="cyan")
table.add_column("Result", style="white")

all_passed = True
for section, passed in results:
    label = "[green]PASS[/]" if passed else "[red]FAIL[/]"
    table.add_row(section, label)
    if not passed:
        all_passed = False

console.print(table)

if all_passed:
    console.print("\n[bold green]Demo complete. All checks passed.[/]")
else:
    failed = [s for s, p in results if not p]
    console.print(f"\n[bold red]Demo complete. Failed checks: {', '.join(failed)}[/]")
