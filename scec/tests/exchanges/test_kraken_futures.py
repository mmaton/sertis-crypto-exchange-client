from unittest.mock import patch

import pytest
from requests import Request

from scec.exchanges import Pair, KrakenFutures, OrderBookOrder, OrderAction, MarketOrder
from scec.exchanges.exceptions import ExchangePairDoesNotExistError


class TestKrakenFutures:
    @patch("scec.exchanges.kraken_futures.KrakenFutures.make_request")
    async def test_loading_exchange_pairs(self, mock_make_request):
        mock_make_request.return_value = {
            "tickers": [
                {"pair": "XBT:USD", "symbol": "PF_XBTUSD", "tag": "perpetual"},
                {"pair": "ADA:USD", "symbol": "PI_ADAUSD", "tag": "month"},
                {"pair": "ADA:EUR", "symbol": "PF_ADAEUR", "tag": "perpetual"},
            ]
        }
        kraken = KrakenFutures(api_key="foo", api_secret="dGVzdA==")
        assert mock_make_request.call_count == 1
        request = mock_make_request.call_args.kwargs["request"]
        assert request.url == kraken.api_url + "tickers"
        assert request.method == "GET"
        assert kraken.pairs == [
            Pair(base="XBT", quote="USD", symbol="PF_XBTUSD"),
            Pair(base="BTC", quote="USD", symbol="PF_XBTUSD"),
            Pair(base="ADA", quote="EUR", symbol="PF_ADAEUR"),
        ]

    async def test_get_order_book(self, kraken_futures, mock_kraken_futures_orderbook):
        order_book = kraken_futures.get_order_book("BTCUSD")
        assert mock_kraken_futures_orderbook.call_count == 1
        request = mock_kraken_futures_orderbook.call_args.kwargs["request"]
        assert request.url == kraken_futures.api_url + "orderbook"
        assert request.params == {"symbol": "PF_XBTUSD"}

        # From test data in `mock_kraken_futures_orderbook`
        assert len(order_book.bids) == 28
        assert len(order_book.asks) == 10
        assert order_book.bids[0] == OrderBookOrder(price=71725.0, quantity=200.0)
        assert order_book.asks[0] == OrderBookOrder(price=71739.0, quantity=200.0)

    async def test_get_order_book_for_nonexistent_pair_throws_handy_error(self, kraken_futures):
        with pytest.raises(ExchangePairDoesNotExistError) as e:
            kraken_futures.get_order_book("DOGEUSD")

        assert str(e.value) == "Trading pair 'DOGEUSD' not found on 'Kraken Futures'"

    async def test_get_order_book_with_custom_depth_limit(self, kraken_futures, mock_kraken_futures_orderbook):
        kraken_futures.get_order_book("ADAEUR", depth_limit=100)
        assert mock_kraken_futures_orderbook.call_count == 1
        request = mock_kraken_futures_orderbook.call_args.kwargs["request"]
        assert request.url == kraken_futures.api_url + "orderbook"
        assert request.params == {"symbol": "PF_ADAEUR"}

    @patch("scec.exchanges.base.CryptocurrencyExchange.send_request")
    async def test_authenticated_requests_are_signed(self, mock_send_request, kraken_futures):
        kraken_futures.make_request(
            request=Request(method="GET", url=kraken_futures.api_url + "account"),
            authenticated=True,
        )
        prepared_request = mock_send_request.call_args_list[0].kwargs["prepared_request"]
        assert prepared_request.headers["APIKey"] == kraken_futures.api_key
        assert "Authent" in prepared_request.headers
        assert "Nonce" in prepared_request.headers

    @patch("scec.exchanges.kraken_futures.KrakenFutures.make_request")
    async def test_execute_market_order(self, mock_make_request, kraken_futures):
        mock_make_request.return_value = {
            'result': 'success',
            'sendStatus': {
                'order_id': '11ebf140-39c7-4b84-96a3-427ab1e0bd5b',
                'status': 'placed',
                'receivedTime': '2024-04-09T13:30:42.933Z',
                'orderEvents': [
                    {
                        'executionId': '344b43e4-2a41-4f53-9211-50d2f0998537',
                        'price': 70658.0,
                        'amount': 0.001,
                        'orderPriorEdit': None,
                        'takerReducedQuantity': None,
                        'type': 'EXECUTION'
                    }
                ]
            },
        }
        market_order = kraken_futures.execute_market_order("BTCUSD", 0.001, OrderAction.BUY)
        assert market_order == MarketOrder(
            id='11ebf140-39c7-4b84-96a3-427ab1e0bd5b',
            pair='PF_XBTUSD',
            action=OrderAction.BUY,
            fills=[(70658.0, 0.001)],
            quantity=0.001,
            filled=0.001,
            status='placed',
            exchange=kraken_futures
        )
        assert market_order.average_fill_price == 70658.0
