import base64
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional, List

from requests import Request, Response

from scec.exchanges import CryptocurrencyExchange, Pair, OrderAction, MarketOrder
from scec.exchanges.base import OrderBook, OrderBookOrder
from scec.exchanges.exceptions import (
    ExchangeRateLimitExceededError,
    ExchangeBadResponseError,
    ExchangeAuthenticationError,
    ExchangeInsufficientFundsError,
)


class KrakenFutures(CryptocurrencyExchange):
    name: str = "Kraken Futures"
    prod_api_url: str = "https://futures.kraken.com/derivatives/api/v3/"
    demo_api_url: str = "https://demo-futures.kraken.com/derivatives/api/v3/"

    error_mapping: dict = {
        'apiLimitExceeded': ExchangeRateLimitExceededError,
        'requiredArgumentMissing': ExchangeBadResponseError,
        'unavailable': ExchangeBadResponseError,
        'authenticationError': ExchangeAuthenticationError,
        'insufficientFunds': ExchangeInsufficientFundsError,
        'Bad Request': ExchangeBadResponseError,
        'Json Parse Error': ExchangeBadResponseError,
        'nonceBelowThreshold': ExchangeAuthenticationError,
        'Server Error': ExchangeBadResponseError,
        'unknownError': ExchangeBadResponseError,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.warning(
            "Kraken Futures API executes orders in contracts, not the base asset. It is advisable to read up on "
            "futures and leverage trading before using this exchange. "
            "This exchange only supports Perpetual Linear Multi-Collateral Futures currently."
            "More info: https://support.kraken.com/hc/en-us/articles/4844359082772-Linear-Multi-Collateral-Perpetual-Contract-Specifications"
        )

    def handle_response(self, response: Response) -> dict:
        """
        Handle the response from the Kraken Futures API, checking for errors and returning the JSON response.

        :param Response response: The response from the Kraken Futures API
        :returns dict: The JSON response from the Kraken Futures API
        """
        response_json = response.json()
        if "result" not in response_json:
            raise ExchangeBadResponseError(f"Kraken Futures API error: {response_json}")

        if "error" in response_json and response_json["error"] in self.error_mapping.keys():
            raise self.error_mapping[response_json["error"]](response_json["error"])

        return response_json

    def make_request(self, request: Request, authenticated: Optional[bool] = False) -> dict:
        """
        Make an authenticated request to exchange endpoint, verify HTTP response code and return response JSON

        :see: https://docs.futures.kraken.com/#http-api-http-api-introduction-authentication

        TODO: Handle rate limiting errors, adding exponential backoff and retry logic.
        """
        extra_headers = {}
        if authenticated:
            params = getattr(request, "params", {})
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])

            # As per recommendation, time in ms is used for a nonce as it's always incrementing
            nonce = int(datetime.now(tz=timezone.utc).timestamp() * 1000)

            endpoint_path = request.url.split("/derivatives")[-1]

            encoded = (query_string + str(nonce) + endpoint_path).encode()
            message = hashlib.sha256(encoded).digest()
            signature = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
            sigdigest = base64.b64encode(signature.digest())
            extra_headers = {"APIKey": str(self.api_key), "Authent": str(sigdigest), "Nonce": str(nonce)}

        req = request.prepare()
        req.headers.update(extra_headers)

        return super().send_request(prepared_request=req, callback=self.handle_response)

    def load_exchange_pairs(self) -> List[Pair]:
        """
        Kraken futures calls BTC XBT, so we need to convert it to BTC
        Only support Perpetual Linear Multi-Collateral Futures for now

        :see: https://docs.futures.kraken.com/#http-api-trading-v3-api-market-data-get-tickers
        """
        self.logger.debug(f"Loading {self.name} exchange pairs...")
        tickers = self.make_request(request=Request(method="GET", url=self.api_url + "tickers"))["tickers"]

        pairs = []
        for ticker in tickers:
            if not (ticker.get("tag") == "perpetual" and ticker.get("symbol").startswith("PF_")):
                continue
            base, quote = ticker["pair"].split(":")
            pairs.append(Pair(base=base, quote=quote, symbol=ticker["symbol"]))

            # Conditional logic to add BTC pairs, typically this would be extensible but XBT is an exception.
            if base == "XBT":
                pairs.append(Pair(base="BTC", quote=quote, symbol=ticker["symbol"]))

        self.logger.debug(f"Loaded {len(tickers)} trading pairs from {self.name}")
        return pairs

    def get_order_book(self, pair: str, *args, **kwargs) -> OrderBook:
        """
        :see: https://docs.futures.kraken.com/#http-api-trading-v3-api-market-data-get-orderbook
        """
        symbol = self.get_pair(pair).symbol
        orders_resp = self.make_request(
            request=Request(
                method="GET",
                url=self.api_url + "orderbook",
                params={"symbol": symbol}
            )
        )
        orders_resp = orders_resp["orderBook"]
        order_book = OrderBook(
            bids=[OrderBookOrder(*[float(b) for b in bids]) for bids in orders_resp["bids"]],
            asks=[OrderBookOrder(*[float(a) for a in asks]) for asks in orders_resp["asks"]],
        )
        return order_book

    def execute_market_order(
        self, pair: str, order_size: float | int, action: OrderAction = OrderAction.BUY
    ) -> MarketOrder:
        """
        Execute a spot market order for a given trading pair and order size.

        Kraken futures market orders are executed in contracts, not the base asset. Market orders are also protected
        from a 1% price slippage so orders may not be filled if the market does not have enough liquidity.

        :see: https://docs.futures.kraken.com/#http-api-trading-v3-api-order-management-send-order
        :param str pair: The trading pair to execute the market order for
        :param float order_size: How much of the asset to buy
        :param [OrderAction] action: The action to take, defaults to `OrderAction.BUY`
        :returns str: The order ID of the executed market order
        """
        pass
        symbol = self.get_pair(pair).symbol
        self.logger.info(f"Executing market order for {order_size} {symbol}")
        response = self.make_request(
            request=Request(
                method="POST",
                url=self.api_url + "sendorder",
                params={
                    "symbol": symbol,
                    "side": action.value.lower(),
                    "orderType": "mkt",
                    "size": order_size,
                    "leverage": 1,
                }
            ),
            authenticated=True,
        )
        # If the last event in the orderEvents array is an EXECUTION type then the order is filled, otherwise there
        # was a problem with the order. Potentially not enough liquidity.
        if response["sendStatus"]["orderEvents"][-1]["type"] != "EXECUTION":
            raise ExchangeBadResponseError(f"Failed to fully execute market order for {symbol}: {response}")

        order_events = response["sendStatus"]["orderEvents"]
        return MarketOrder(
            id=response["sendStatus"]["order_id"],
            pair=symbol,
            action=action,
            fills=[(float(fill["price"]), float(fill["amount"])) for fill in order_events],
            quantity=order_size,
            filled=sum([float(fill["amount"]) for fill in order_events]),
            # Take the response from the last event in the orderEvents array
            status=response["sendStatus"]["status"],
            exchange=self,
        )