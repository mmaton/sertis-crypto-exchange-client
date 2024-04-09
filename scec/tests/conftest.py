import pytest

from unittest.mock import patch, MagicMock

from scec.broker import Broker
from scec.exchanges import Binance, KrakenFutures, Pair


@pytest.fixture(autouse=True)
def block_http_requests(monkeypatch):
    """
    Catch any real HTTP requests from being made during test runs, patches a low-level method in urllib3 so that
    we can still mock function calls from the `requests` library.
    """
    def urlopen_mock(self, method, url, *args, **kwargs):
        raise RuntimeError(f"A test was about to {method} {self.scheme}://{self.host}{url}")

    monkeypatch.setattr("urllib3.connectionpool.HTTPConnectionPool.urlopen", urlopen_mock)


@pytest.fixture(autouse=True, scope="session")
def disable_tenacity_sleep():
    """
    Mock the sleep function in the tenacity library to speed up tests which invoke code with retry decorators.
    """
    with patch("tenacity.nap.time.sleep", MagicMock()):
        yield


@pytest.fixture
def binance():
    """
    A handy fixture for testing base class methods.
    :return:
    """
    with patch("scec.exchanges.binance.Binance.load_exchange_pairs") as load_exchange_pairs:
        load_exchange_pairs.return_value = [
            Pair(base="BTC", quote="USDT", symbol="BTCUSDT"),
            Pair(base="BTC", quote="USD", symbol="BTCUSDT"),
            Pair(base="ADA", quote="EUR", symbol="ADAEUR"),
        ]
        yield Binance(api_key="foo", api_secret="dGVzdA==", usd_stablecoin="USDT")


@pytest.fixture
def kraken_futures():
    with patch("scec.exchanges.kraken_futures.KrakenFutures.load_exchange_pairs") as load_exchange_pairs:
        load_exchange_pairs.return_value = [
            Pair(base="XBT", quote="USD", symbol="PF_XBTUSD"),
            Pair(base="BTC", quote="USD", symbol="PF_XBTUSD"),
            Pair(base="ADA", quote="EUR", symbol="PF_ADAEUR"),
        ]
        yield KrakenFutures(api_key="foo", api_secret="dGVzdA==")


@pytest.fixture
def broker(binance):
    broker = Broker()
    broker.add_exchange(binance)
    return broker


@pytest.fixture
def mock_binance_orderbook(binance):
    # I usually prefer to use the `patch` decorator function as it results in less indentation.
    # The context manager however is more declarative and easier to read in some cases.
    with patch("scec.exchanges.binance.Binance.make_request") as mock_make_request:
        mock_make_request.return_value = {
            'lastUpdateId': 1113745,
            'bids': [
                ['0.54750000', '5751.00000000'], ['0.54740000', '759.00000000'],
                ['0.54730000', '722.00000000'], ['0.54710000', '869.00000000'],
                ['0.54700000', '814.00000000'], ['0.54690000', '531.00000000'],
                ['0.54680000', '695.00000000'], ['0.54670000', '842.00000000'],
                ['0.54650000', '705.00000000'], ['0.54640000', '604.00000000'],
                ['0.54370000', '801.00000000'], ['0.54280000', '645.00000000'],
                ['0.52740000', '541.00000000'], ['0.49300000', '579.00000000']
            ],
            'asks': [
                ['0.54810000', '822.00000000'], ['0.54820000', '876.00000000'],
                ['0.54840000', '165.00000000'], ['0.54870000', '912.00000000'],
                ['0.54880000', '711.00000000'], ['0.54890000', '593.00000000'],
                ['0.54900000', '847.00000000'], ['0.54910000', '665.00000000'],
                ['0.54920000', '538.00000000'], ['0.54940000', '501.00000000'],
                ['0.54970000', '455.00000000'], ['0.54980000', '901.00000000'],
                ['0.55040000', '682.00000000'], ['0.55070000', '709.00000000'],
                ['0.56000000', '759.00000000']
            ]
        }
        yield mock_make_request


@pytest.fixture
def mock_kraken_futures_orderbook(kraken_futures):
    with patch("scec.exchanges.kraken_futures.KrakenFutures.make_request") as mock_make_request:
        mock_make_request.return_value = {
            'serverTime': '2024-04-08T14:25:32.736Z',
            'result': 'success',
            'orderBook': {
                'bids': [
                    [71725, 200], [71717.5, 200], [71710.5, 200], [71703.5, 200], [71696, 200],
                    [71689, 200], [71682, 200], [71674.5, 200], [66123, 1600], [66000, 9], [50000, 2500],
                    [43000, 2000], [19385.5, 17188], [12000, 1], [10000, 3], [2000, 9776], [1900, 1],
                    [1500, 1400], [1000, 1008], [200, 212], [130, 3], [100, 23], [30, 30], [20, 1],
                    [10, 11], [5, 11], [2, 16], [1, 20]
                ],
                'asks': [
                    [71739, 200], [71746.5, 200], [71753.5, 200], [71760.5, 200], [71768, 200], [71775, 200],
                    [71782, 200], [71789.5, 200], [84961.5, 78000], [196000, 19]
                ]
            },
        }
        yield mock_make_request
