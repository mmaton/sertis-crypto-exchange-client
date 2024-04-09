import asyncio
from typing import List, Tuple, Optional, Set

import heapq
import logging

from scec.exchanges import CryptocurrencyExchange, OrderAction
from scec.exchanges.base import MarketOrder
from scec.exchanges.exceptions import ExchangeLiquidityError


class Broker:
    def __init__(
        self,
        exchanges: Optional[Set[CryptocurrencyExchange]] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.exchanges: Set[CryptocurrencyExchange] = exchanges or set()
        self.logger = logger if logger else logging.getLogger(__name__)

    def add_exchange(self, exchange_instance: CryptocurrencyExchange) -> None:
        """
        Method to connect a new exchange to the broker. It is possible to add two separate
        instances of the same exchange, but this is not recommended and would lead to rate-limiting.

        # TODO: Prevent two of the same exchanges from being added, by checking the or `name` or `__name__`

        :param `CryptocurrencyExchange` exchange_instance: The exchange instance to connect to the broker
        :returns None:
        """
        self.exchanges.add(exchange_instance)

    async def get_estimated_market_buy_price(
        self,
        exchange: CryptocurrencyExchange,
        symbol: str,
        order_size: float | int,
    ) -> float:
        """
        Method to estimate the market buy price for a given order size on a particular exchange.

        :param `CryptocurrencyExchange` exchange: The exchange to get the estimated market buy price from
        :param str symbol: The trading pair to get the estimated market buy price for
        :param float order_size: The size of the order to estimate the market buy price for
        :returns float: The estimated market buy price for the order size
        """
        order_book = exchange.get_order_book(symbol)
        fill_amounts_at_price: List[Tuple[float, float]] = []

        # Calculate the estimated market price based on the order size and the current bids/asks in the orderbook
        while order_size > 0 and order_book.asks:
            ask = order_book.asks.pop(0)  # TODO: OrderBook asks/bids as a `Deque` for faster `popleft`
            if ask.quantity >= order_size:
                fill_amounts_at_price.append((ask.price, order_size))
                order_size = 0
            else:
                fill_amounts_at_price.append((ask.price, ask.quantity))
                order_size -= ask.quantity

        if order_size > 0:
            raise ExchangeLiquidityError("Insufficient liquidity in orderbook to fill order")

        price_sum = sum([price * amount for price, amount in fill_amounts_at_price])
        amount_sum = sum([amount for _, amount in fill_amounts_at_price])
        market_price = price_sum / amount_sum
        self.logger.debug(f"Got estimated market buy price for '{symbol}' on '{exchange.name}': {market_price:.4f}")
        return market_price

    async def get_lowest_market_buy_price(
        self,
        symbol: str,
        amount: float | int,
    ) -> Tuple[float, CryptocurrencyExchange]:
        """
        Return the exchange with the lowest estimated market buy price for a given cryptocurrency.

        :param str symbol: The symbol of the cryptocurrency to get the lowest market price for
        :param float amount: The amount of the cryptocurrency to get the lowest market price for
        :returns `CryptocurrencyExchange`: The exchange with the lowest estimated market buy price
        """
        exchange_prices: List[Tuple[float, CryptocurrencyExchange]] = []

        # Use asyncio.gather to get prices concurrently
        prices = await asyncio.gather(
            *[self.get_estimated_market_buy_price(exchange, symbol, amount) for exchange in self.exchanges]
        )
        for price, exchange in zip(prices, self.exchanges):
            heapq.heappush(exchange_prices, (price, exchange))

        if exchange_prices:
            best_price, best_exchange = heapq.heappop(exchange_prices)
            return best_price, best_exchange

        raise RuntimeError("No exchanges available to get lowest market price")

    async def execute_market_buy_for_lowest_price(self, symbol: str, amount: float | int) -> MarketOrder:
        """
        Execute a market buy for the lowest estimated market buy price for a given cryptocurrency.

        :param str symbol: The symbol of the cryptocurrency to execute the market order for
        :param float amount: The amount of the cryptocurrency to execute the market order for
        :returns str: The order ID of the executed market order
        """
        _, best_exchange = await self.get_lowest_market_buy_price(symbol, amount)
        return best_exchange.execute_market_order(pair=symbol, order_size=amount, action=OrderAction.BUY)
