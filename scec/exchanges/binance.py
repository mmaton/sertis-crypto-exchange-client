import hashlib
import hmac
from datetime import datetime, timezone
from typing import List, Optional

from requests import Request

from scec.exchanges import CryptocurrencyExchange
from scec.exchanges.base import OrderBook, OrderBookOrder, Pair, OrderAction, MarketOrder


class Binance(CryptocurrencyExchange):
    name: str = "Binance"
    prod_api_url: str = "https://api.binance.com/api/v3/"
    demo_api_url: str = "https://testnet.binance.vision/api/v3/"

    # TODO: Use values when expanding search for liquidity, validate `get_order_book` arguments
    order_book_min_limit: int = 1
    order_book_max_limit: int = 5000

    def make_request(self, request: Request, authenticated: Optional[bool] = False) -> dict:
        """
        Make an optionally authenticated request to exchange endpoint, verify HTTP response code
        and return response JSON.

        :param Request request: The request to make, with a URL, method, and any data or headers
        :param [bool] authenticated: Whether the request should be authenticated with the API key and secret
        :returns dict: The JSON response from the exchange

        TODO: Handle generic rate limit errors, adding exponential backoff and retry logic.
        """
        if authenticated:
            params = getattr(request, "params", {})
            # https://github.com/binance/binance-spot-api-docs/blob/master/testnet/rest-api.md#signed-trade-and-user_data-endpoint-security
            timestamp_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
            params.update({"timestamp": timestamp_ms})

            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            signature = hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
            params.update({"signature": signature})
            request.params = params

        req = request.prepare()

        req.headers.update({"X-MBX-APIKEY": self.api_key})
        return super().send_request(req)

    def load_exchange_pairs(self) -> List[Pair]:
        self.logger.debug(f"Loading {self.name} exchange pairs...")
        symbols = self.make_request(
            request=Request(
                method="GET",
                url=self.api_url + "exchangeInfo",
            )
        )["symbols"]
        self.logger.debug(f"Loaded {len(symbols)} trading pairs from {self.name}")
        pairs = []
        for symbol in symbols:
            pairs.append(Pair(base=symbol["baseAsset"], quote=symbol["quoteAsset"], symbol=symbol["symbol"]))

            # Binance does not use USD as a quote asset, but uses stablecoins like USDT, USDC etc.
            # To support trading across multiple exchanges, we can elect to treat one of these coins as USD.
            if symbol["quoteAsset"] == self.usd_stablecoin and symbol["quoteAsset"] != "USD":
                pairs.append(Pair(base=symbol["baseAsset"], quote="USD", symbol=symbol["symbol"]))
        return pairs

    def get_order_book(self, pair: str, *args, **kwargs) -> OrderBook:
        """
        :see: https://binance-docs.github.io/apidocs/spot/en/#order-book
        """
        depth_limit = kwargs.get("depth_limit", 1000)
        symbol = self.get_pair(pair).symbol
        orders_resp = self.make_request(
            request=Request(
                method="GET",
                url=self.api_url + "depth",
                params={
                    "symbol": symbol,
                    "limit": depth_limit,
                }
            )
        )
        order_book = OrderBook(
            bids=[OrderBookOrder(*[float(b) for b in bids]) for bids in orders_resp["bids"]],
            asks=[OrderBookOrder(*[float(a) for a in asks]) for asks in orders_resp["asks"]],
        )
        return order_book

    def execute_market_order(
        self, pair: str, order_size: float, action: OrderAction = OrderAction.BUY,
    ) -> MarketOrder:
        """
        Execute a spot market order for a given trading pair and order size.

        :see: https://binance-docs.github.io/apidocs/spot/en/#new-order-trade
        :param str pair: The trading pair to execute the market order for
        :param float order_size: How much of the asset to buy
        :param [OrderAction] action: The action to take, defaults to `OrderAction.BUY`
        :returns str: The order ID of the executed market order
        """
        symbol = self.get_pair(pair).symbol
        self.logger.info(f"Executing market order for {order_size} {symbol}")
        response = self.make_request(
            request=Request(
                method="POST",
                url=self.api_url + "order",
                params={
                    "symbol": symbol,
                    "side": action.value,
                    "type": "MARKET",
                    "quantity": order_size,
                }
            ),
            authenticated=True,
        )
        return MarketOrder(
            id=response["orderId"],
            pair=symbol,
            action=OrderAction.BUY if response["side"] == "BUY" else OrderAction.SELL,
            fills=[(float(fill["price"]), float(fill["qty"])) for fill in response["fills"]],
            quantity=float(response["origQty"]),
            filled=float(response["executedQty"]),
            status=response["status"],
            exchange=self,
        )
