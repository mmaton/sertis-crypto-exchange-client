import pytest

from scec import Broker
from scec.exchanges.exceptions import ExchangeLiquidityError


async def test_broker_can_add_exchange(binance):
    broker = Broker()
    broker.add_exchange(binance)
    assert broker.exchanges == {binance}


async def test_broker_can_get_estimated_market_buy_price(broker, binance, mock_binance_orderbook):
    estimated_price = await broker.get_estimated_market_buy_price(exchange=binance, symbol="ADAEUR", order_size=100)
    assert estimated_price == 0.5481


async def test_broker_can_get_exchange_with_lowest_estimated_market_price(broker, binance, mock_binance_orderbook):
    assert await broker.get_lowest_market_buy_price(symbol="ADAEUR", amount=100) == (0.5481, binance)


async def test_broker_raises_insufficient_liquidity_on_exchange_exception(broker, binance, mock_binance_orderbook):
    with pytest.raises(ExchangeLiquidityError) as e:
        await broker.get_estimated_market_buy_price(exchange=binance, symbol="ADAEUR", order_size=100_000)

    assert str(e.value) == "Insufficient liquidity in orderbook to fill order"


async def test_broker_gets_lowest_market_price_for_symbol_with_multiple_exchanges(
    broker, binance, kraken_futures, mock_binance_orderbook, mock_kraken_futures_orderbook
):
    broker.add_exchange(kraken_futures)
    _, exchange = await broker.get_lowest_market_buy_price(symbol="ADAEUR", amount=100)
    assert exchange is binance
