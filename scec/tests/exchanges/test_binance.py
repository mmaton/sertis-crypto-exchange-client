from unittest.mock import patch

import pytest
from requests import Request

from scec.exchanges import Pair, Binance, OrderBookOrder, OrderAction, MarketOrder
from scec.exchanges.exceptions import ExchangePairDoesNotExistError


class TestBinance:
    @patch("scec.exchanges.binance.Binance.make_request")
    async def test_loading_exchange_pairs(self, mock_make_request):
        mock_make_request.return_value = {
            "symbols": [
                {"baseAsset": "BTC", "quoteAsset": "USDT", "symbol": "BTCUSDT"},
                {"baseAsset": "ADA", "quoteAsset": "EUR", "symbol": "ADAEUR"},
            ]
        }
        binance = Binance(api_key="foo", api_secret="dGVzdA==")
        assert mock_make_request.call_count == 1
        request = mock_make_request.call_args.kwargs["request"]
        assert request.url == binance.api_url + "exchangeInfo"
        assert request.method == "GET"
        assert binance.pairs == [
            Pair(base="BTC", quote="USDT", symbol="BTCUSDT"),
            Pair(base="ADA", quote="EUR", symbol="ADAEUR")
        ]

    @patch("scec.exchanges.binance.Binance.make_request")
    async def test_loading_exchange_pairs_with_stablecoin_adds_additional_pairs(self, mock_make_request):
        mock_make_request.return_value = {
            "symbols": [
                {"baseAsset": "BTC", "quoteAsset": "USDT", "symbol": "BTCUSDT"},
                {"baseAsset": "ADA", "quoteAsset": "EUR", "symbol": "ADAEUR"},
            ]
        }
        binance = Binance(api_key="foo", api_secret="dGVzdA==", usd_stablecoin="USDT")
        assert binance.pairs == [
            Pair(base="BTC", quote="USDT", symbol="BTCUSDT"),
            Pair(base="BTC", quote="USD", symbol="BTCUSDT"),
            Pair(base="ADA", quote="EUR", symbol="ADAEUR")
        ]

    async def test_get_order_book(self, binance, mock_binance_orderbook):
        order_book = binance.get_order_book("ADAEUR")
        assert mock_binance_orderbook.call_count == 1
        request = mock_binance_orderbook.call_args.kwargs["request"]
        assert request.url == binance.api_url + "depth"

        # From test data in `mock_binance_orderbook`
        assert len(order_book.bids) == 14
        assert len(order_book.asks) == 15
        assert order_book.bids[0] == OrderBookOrder(price=0.5475, quantity=5751.0)
        assert order_book.asks[0] == OrderBookOrder(price=0.5481, quantity=822.0)

    async def test_get_order_book_for_nonexistent_pair_throws_handy_error(self, binance):
        with pytest.raises(ExchangePairDoesNotExistError) as e:
            binance.get_order_book("DOGEUSD")

        assert str(e.value) == "Trading pair 'DOGEUSD' not found on 'Binance'"

    async def test_get_order_book_with_custom_depth_limit(self, binance, mock_binance_orderbook):
        binance.get_order_book("ADAEUR", depth_limit=100)
        assert mock_binance_orderbook.call_count == 1
        request = mock_binance_orderbook.call_args.kwargs["request"]
        assert request.url == binance.api_url + "depth"
        assert request.params == {"symbol": "ADAEUR", "limit": 100}

    @patch("scec.exchanges.base.CryptocurrencyExchange.send_request")
    async def test_authenticated_requests_are_signed(self, mock_send_request, binance):
        binance.make_request(
            request=Request(method="GET", url=binance.api_url + "account"),
            authenticated=True,
        )
        call_args = mock_send_request.call_args[0]
        assert "signature" in call_args[0].url
        assert "timestamp" in call_args[0].url
        assert mock_send_request.call_args.args[0].headers == {"X-MBX-APIKEY": binance.api_key}

    @patch("scec.exchanges.binance.Binance.make_request")
    async def test_execute_market_order(self, mock_make_request, binance):
        mock_make_request.return_value = {
            "orderId": "12345",
            "side": "BUY",
            "origQty": "100",
            "executedQty": "100",
            "status": "FILLED",
            "fills": [{"price": "0.5481", "qty": "100"}]
        }
        market_order = binance.execute_market_order("ADAEUR", 100, OrderAction.BUY)
        assert market_order == MarketOrder(
            id="12345",
            pair="ADAEUR",
            action=OrderAction.BUY,
            fills=[(0.5481, 100.0)],
            filled=100.0,
            quantity=100,
            status="FILLED",
            exchange=binance,
        )
        assert market_order.average_fill_price == 0.5481
