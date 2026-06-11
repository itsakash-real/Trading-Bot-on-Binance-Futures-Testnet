## Assignment Analysis: Binance Futures Testnet Trading Bot

### 1. Ambiguities & Missing Details

**API Layer:**
- The assignment offers `python-binance` OR direct REST — no preference stated. This is actually a significant architectural decision (more on this in risks).
- No mention of how API keys should be supplied — hardcoded? `.env` file? CLI flags? The safest assumption is `.env`, but worth clarifying mentally before you start.
- **Leverage and margin mode** — Binance Futures requires these to be set before placing orders. The assignment doesn't mention it at all. You'll need to either assume defaults or handle it silently.

**Order Details:**
- `timeInForce` for LIMIT orders (GTC/IOC/FOK) — not mentioned. You'll need to default to `GTC` and either expose it or note it as an assumption.
- **Quantity precision** — Binance enforces `stepSize` (lot size filter) per symbol. If quantity doesn't conform, the API rejects it. The assignment doesn't mention validation at this level, but ignoring it will cause failures on testnet.
- Similarly **price precision** (`tickSize`) for LIMIT orders.

**Output & Logging:**
- "Log file" — no path or naming convention specified. You get to decide.
- Output format for order response — table? JSON dump? Plain text? The assignment says "clear output" but leaves it open.

**Bonus:**
- They say "choose any one" — the safest and most impactful pick given the 60-minute window is **Enhanced CLI UX** (prompts, validation messages). It adds zero API complexity and makes your submission look polished.

---

### 2. Proposed Folder Structure

Sticking close to their suggested structure but filling the gaps:

```
trading_bot/
│
├── bot/
│   ├── __init__.py
│   ├── client.py          # Raw HTTP layer — signs requests, handles auth
│   ├── orders.py          # Order logic — build payload, call client
│   ├── validators.py      # Input validation (symbol format, qty, price, side)
│   └── logging_config.py  # Logging setup (file + console handlers)
│
├── cli.py                 # CLI entry point (argparse or Typer)
├── .env.example           # Template: BINANCE_API_KEY, BINANCE_SECRET_KEY
├── .gitignore             # Must exclude .env and logs/
├── requirements.txt
├── README.md
│
└── logs/
    └── trading_bot.log    # Generated at runtime
```

The key separation: `client.py` knows nothing about orders — it just signs and fires HTTP requests. `orders.py` knows nothing about HTTP — it builds payloads and delegates to the client. `cli.py` knows nothing about either — it just parses args and calls `orders.py`.

---

### 3. Recommended Tech Stack

| Component | Recommendation | Reason |
|---|---|---|
| HTTP client | **`requests`** (direct REST) | Avoids `python-binance` testnet compatibility issues; shows you understand Binance's HMAC signing mechanism |
| CLI | **`argparse`** (stdlib) | Zero extra dependency, sufficient for this scope; Typer/Click is overkill for a 60-min task |
| Output formatting | **`rich`** | One import, makes tables/colored output trivial — evaluators notice this |
| Env management | **`python-dotenv`** | Industry standard for keeping secrets out of code |
| Logging | **stdlib `logging`** | Exactly what they asked for; `RotatingFileHandler` is a nice touch |

**Why direct REST over `python-binance`?**
The `python-binance` library has had documented issues with Futures Testnet endpoints — wrong base URLs, version mismatches with the API. Writing your own thin client with `requests` + HMAC-SHA256 signing is ~30 lines and far more reliable. It also signals stronger understanding to the evaluator.

---

### 4. Biggest Technical Risks

**Risk 1 — HMAC Signature & Timestamp (Highest Risk)**
Binance signed endpoints require a `timestamp` + `signature` (HMAC-SHA256 of the query string). If your local clock is off by more than 1000ms from Binance's server, every request fails with a timestamp error. You'll need to either sync time or add a `recvWindow` parameter. This is the #1 silent failure point.

**Risk 2 — Quantity/Price Precision Filters**
Binance rejects orders where quantity doesn't match the symbol's `stepSize` or price doesn't match `tickSize`. For example, BTCUSDT might require quantity in increments of `0.001`. If you don't round/truncate to the correct precision, the API returns a filter violation error. You need to either fetch exchange info and apply filters, or document it as an assumption ("user must supply valid precision").

**Risk 3 — Testnet Account State**
Testnet accounts need to be "topped up" with fake USDT. If the account has no balance or an open position blocks a new order, placement fails. This is an environment issue, not a code issue — but it'll waste debugging time if you're not aware.

**Risk 4 — Position Mode (Hedge vs One-Way)**
Testnet defaults to One-Way mode. In One-Way mode, you don't pass `positionSide`. If the account was ever switched to Hedge mode, you must pass `positionSide: BOTH/LONG/SHORT` or the API rejects the order. Worth defaulting to One-Way and noting the assumption.

---

### My Recommendation Before You Confirm

Given the 60-minute estimate, I'd suggest: **direct REST + argparse + rich + python-dotenv**, with the Enhanced CLI UX bonus (input prompts with validation messages rather than pure flag-based). This keeps the scope tight, avoids library rabbit holes, and produces a noticeably polished submission.
