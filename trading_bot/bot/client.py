import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from trading_bot.bot.logging_config import get_logger

load_dotenv()


class BinanceClient:
    RECV_WINDOW: int = 5000

    def __init__(self) -> None:
        self.api_key: str = os.getenv("BINANCE_API_KEY", "")
        self.api_secret: str = os.getenv("BINANCE_SECRET_KEY", "")
        self.base_url: str = "https://testnet.binancefuture.com"
        self.logger = get_logger()

    def _sign(self, params: dict) -> str:
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _get_timestamp() -> int:
        return int(time.time() * 1000)

    def _request(
        self, method: str, endpoint: str, params: dict | None = None, signed: bool = False
    ) -> dict:
        if params is None:
            params = {}

        if signed:
            params["timestamp"] = self._get_timestamp()
            params["recvWindow"] = self.RECV_WINDOW
            params["signature"] = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        headers = {"X-MBX-APIKEY": self.api_key} if signed else {}

        self.logger.info("REQUEST: %s %s | params=%s", method, url, params)

        resp = requests.request(method, url, params=params, headers=headers)
        self.logger.info("RESPONSE: %s | body=%s", resp.status_code, resp.text)

        resp.raise_for_status()
        return resp.json()

    def get_account_info(self) -> dict:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_exchange_info(self, symbol: str) -> dict:
        data = self._request("GET", "/fapi/v1/exchangeInfo")
        for s in data["symbols"]:
            if s["symbol"] == symbol:
                return s
        raise ValueError(f"Symbol {symbol} not found in exchange info")
