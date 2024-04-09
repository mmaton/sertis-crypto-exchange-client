from enum import Enum
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple

import tenacity
from requests import codes, Session, PreparedRequest, Request

from scec.exchanges.exceptions import ExchangeBadResponseError, ExchangePairDoesNotExistError


class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Pair:
    """
    A cryptocurrency trading pair, normalized to the base and quote symbols, with the symbol
    to use when querying the `CryptoCurrencyExchange` API.
    """
    base: str
    quote: str
    symbol: str


@dataclass
class MarketOrder:
    id: str
    pair: str
    action: OrderAction
    fills: List[Tuple[float, float]]  # (price, quantity)
    quantity: float
    filled: float
    status: str
    exchange: "CryptocurrencyExchange"

    @property
    def average_fill_price(self) -> float:
        # Calculate total quantity purchased
        total_quantity = sum(quantity for price, quantity in self.fills)

        # Calculate weighted sum of fill prices
        weighted_sum = sum(price * quantity for price, quantity in self.fills)

        # Calculate average fill price
        return weighted_sum / total_quantity



@dataclass
class OrderBookOrder:
    price: float
    quantity: float


@dataclass
class OrderBook:
    """
    Represents an exchange orderbook with orders on the buy (bids) and sell (asks) sides.

    The orderbook is useful when trying to determine the market price of an asset. Without which the
    order could suffer from slippage, where the price of the order is not what was expected due to the
    lack of liquidity.
    """
    bids: List[OrderBookOrder]
    asks: List[OrderBookOrder]


class CryptocurrencyExchange(ABC):
    """
    Base class for cryptocurrency exchange API clients.
    """
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        logger: Optional[logging.Logger] = None,
        usd_stablecoin: Optional[str] = None,
    ):
        """
        :param str api_key: Exchange HMAC API key
        :param str api_secret: Exchange HMAC API secret
        :param bool [testnet]: Whether this exchange instance should use the exchange testnet or not
        :param [logging.Logger] logger: Optional logger to use for logging
        :param [str] usd_stablecoin: The stable-coin to use for USD transactions, as some exchanges only support
        stable-coins for USD transactions.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = self.prod_api_url if testnet is False else self.demo_api_url
        self.logger = logger or logging.getLogger(__name__)
        self.usd_stablecoin = usd_stablecoin or "USD"

        # Initialise pairs
        self.pairs = self.load_exchange_pairs()

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Friendly name of the exchange - presented to the user.
        """
        ...

    @property
    @abstractmethod
    def prod_api_url(self) -> str:
        ...

    @property
    @abstractmethod
    def demo_api_url(self) -> str:
        ...

    @abstractmethod
    def make_request(self, request: Request, authenticated: Optional[bool] = False) -> dict:
        """
        Prepare and send a request to the exchange API. This method should be used to handle any exchange-specific
        requirements for request headers, query parameters, and request bodies.
        """
        req = request.prepare()
        return self.send_request(req)

    @staticmethod
    def send_request(prepared_request: PreparedRequest, callback: Optional[Callable] = None) -> dict:
        """
        Send a prepared request to the exchange API and return the JSON response. Raise an ExchangeException if the
        response status code is not 200.

        Each exchange will have differing requirements for request headers, query parameters, and request bodies. This
        method is used to standardize the process of sending requests to the exchange API, and handle any errors that
        may arise. Handling rate limits and exponential backoff should be done in the `CryptocurrencyExchange` subclass.

        :param PreparedRequest prepared_request: The request to send to the exchange API
        :param [Callable] callback: Optional callback to check the response for errors before returning its json
        :raises: `ExchangeException`
        :return: dict
        """

        @tenacity.retry(
            stop=tenacity.stop_after_attempt(5),
            wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        )
        def _send():
            """Handle network errors and retry the request 5 times."""
            return Session().send(prepared_request)

        response = _send()
        if response.status_code != codes.ok:
            try:
                error_json = response.json()
                msg = error_json["msg"]
            except (ValueError, TypeError):
                msg = response.content  # The error isn't JSON, just return the raw content
            except KeyError:
                msg = "Unknown error occurred."  # The error JSON doesn't have a `msg` key

            raise ExchangeBadResponseError(
                f"Request failed with status code {response.status_code}, error message: {msg}", response=response
            )
        if callback:
            return callback(response)

        return response.json()

    @abstractmethod
    def load_exchange_pairs(self) -> List[Pair]:
        """
        Returns a list of trading pairs available on the exchange. Each pair should have a normalized base and quote.
        """
        ...

    @abstractmethod
    def get_order_book(self, pair: str) -> OrderBook:
        """
        :param str pair: The trading pair to get the order book for
        :keyword int [depth_limit]: Additional arguments to pass to the request
        """

    @abstractmethod
    def execute_market_order(
        self, pair: str, order_size: float | int, action: OrderAction = OrderAction.BUY,
    ) -> MarketOrder:
        """
        Execute a spot market order for a given trading pair and order size.

        :param str pair: The trading pair to execute the market order for
        :param float order_size: How much of the asset to buy
        :param [OrderAction] action: The action to take, defaults to `OrderAction.BUY`
        :returns str: The order ID of the executed market order
        """
        ...

    def get_pair(self, symbol: str) -> Pair:
        """
        Get a trading pair by symbol, or base + quote symbols. This is helpful if an exchange has non-standard symbols
        for a market - for example Kraken Futures which uses "pi_xbtusd" for the BTCUSD trading pair.

        TODO:
            This could be optimized to O(1) by using dicts to store the pairs, just iterate over the list now.
            - Store two dicts:
                - symbol as the key and the Pair object as the value.
                - base + quote as the key and the Pair object as the value.
        """
        for pair in self.pairs:
            if pair.symbol == symbol or pair.base + pair.quote == symbol:
                return pair

        raise ExchangePairDoesNotExistError(f"Trading pair '{symbol}' not found on '{self.name}'")