import logging
import os

"""
Import the broker and one or more exchanges to use in the broker.
"""
from scec import Broker  # noqa E402
from scec.exchanges import Binance, KrakenFutures, OrderAction  # noqa E402

# Set logging level to DEBUG to see the logs from the broker and exchange instances
logging.basicConfig(level=logging.DEBUG)

# Instantiate a new broker instance and add the exchange(s) you want to use
broker = Broker()
# Create a testnet binance API key and secret over at https://testnet.binance.vision/
# set your API key and secret with environment variables.
binance = Binance(
    api_key=os.environ.get("BINANCE_API_KEY", "<your binance api key>"),
    api_secret=os.environ.get("BINANCE_API_SECRET", "<your binance api secret>"),
    testnet=True,
    usd_stablecoin="USDT",
)
kraken = KrakenFutures(
    api_key=os.environ.get("KRAKEN_API_KEY", "<your kraken futures api key>"),
    api_secret=os.environ.get("KRAKEN_API_SECRET", "<your kraken futures api secret>"),
    testnet=True,
)
broker.add_exchange(binance)
broker.add_exchange(kraken)


async def main():
    # Get the lowest estimated market price for a given amount of an asset across all exchanges added to the broker
    lowest_price, exchange = await broker.get_lowest_market_buy_price(symbol="ADAUSD", amount=1000)
    print(f"The lowest estimated market price for 500 ADA is {lowest_price} on {exchange.name}")

    # Execute a market order for the lowest price on the exchange with the lowest estimated market price
    market_order = await broker.execute_market_buy_for_lowest_price(symbol="ADAUSD", amount=10)
    print(f"Executed market buy order for 10 ADA at {market_order.average_fill_price} on {market_order.exchange.name}")

    # Sell on an individual exchange, binance in this case
    sell_order_binance = binance.execute_market_order(pair="ADAEUR", order_size=10, action=OrderAction.SELL)
    print(f"Executed market sell order for 10 ADA at {sell_order_binance.average_fill_price} "
          f"on {sell_order_binance.exchange.name}")

    # Buy 0.001 BTC on kraken futures
    buy_order_kraken = kraken.execute_market_order(pair="BTCUSD", order_size=0.001, action=OrderAction.BUY)
    print(f"Executed market buy order for 0.001 BTC at average price of {buy_order_kraken.average_fill_price}")

if __name__ == "__main__":
    # Run the broker example in a asyncio event loop to execute async functions like `get_lowest_market_buy_price` which
    # looks at multiple exchanges concurrently to get the lowest price for an asset.
    import asyncio
    asyncio.run(main())
