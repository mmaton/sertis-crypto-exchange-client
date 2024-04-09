<a id="__init__"></a>

# \_\_init\_\_

<a id="broker"></a>

# broker

<a id="broker.Broker"></a>

## Broker Objects

```python
class Broker()
```

<a id="broker.Broker.add_exchange"></a>

#### add\_exchange

```python
def add_exchange(exchange_instance: CryptocurrencyExchange) -> None
```

Method to connect a new exchange to the broker. It is possible to add two separate

instances of the same exchange, but this is not recommended and would lead to rate-limiting.

# TODO: Prevent two of the same exchanges from being added, by checking the or `name` or `__name__`

**Arguments**:

- `exchange_instance` (``CryptocurrencyExchange``): The exchange instance to connect to the broker

**Returns**:

`None`: 

<a id="broker.Broker.get_estimated_market_buy_price"></a>

#### get\_estimated\_market\_buy\_price

```python
async def get_estimated_market_buy_price(exchange: CryptocurrencyExchange,
                                         symbol: str,
                                         order_size: float | int) -> float
```

Method to estimate the market buy price for a given order size on a particular exchange.

**Arguments**:

- `exchange` (``CryptocurrencyExchange``): The exchange to get the estimated market buy price from
- `symbol` (`str`): The trading pair to get the estimated market buy price for
- `order_size` (`float`): The size of the order to estimate the market buy price for

**Returns**:

`float`: The estimated market buy price for the order size

<a id="broker.Broker.get_lowest_market_buy_price"></a>

#### get\_lowest\_market\_buy\_price

```python
async def get_lowest_market_buy_price(
        symbol: str,
        amount: float | int) -> Tuple[float, CryptocurrencyExchange]
```

Return the exchange with the lowest estimated market buy price for a given cryptocurrency.

**Arguments**:

- `symbol` (`str`): The symbol of the cryptocurrency to get the lowest market price for
- `amount` (`float`): The amount of the cryptocurrency to get the lowest market price for

**Returns**:

``CryptocurrencyExchange``: The exchange with the lowest estimated market buy price

<a id="broker.Broker.execute_market_buy_for_lowest_price"></a>

#### execute\_market\_buy\_for\_lowest\_price

```python
async def execute_market_buy_for_lowest_price(
        symbol: str, amount: float | int) -> MarketOrder
```

Execute a market buy for the lowest estimated market buy price for a given cryptocurrency.

**Arguments**:

- `symbol` (`str`): The symbol of the cryptocurrency to execute the market order for
- `amount` (`float`): The amount of the cryptocurrency to execute the market order for

**Returns**:

`str`: The order ID of the executed market order

<a id="exchanges"></a>

# exchanges

<a id="exchanges.kraken_futures"></a>

# exchanges.kraken\_futures

<a id="exchanges.kraken_futures.KrakenFutures"></a>

## KrakenFutures Objects

```python
class KrakenFutures(CryptocurrencyExchange)
```

<a id="exchanges.kraken_futures.KrakenFutures.handle_response"></a>

#### handle\_response

```python
def handle_response(response: Response) -> dict
```

Handle the response from the Kraken Futures API, checking for errors and returning the JSON response.

**Arguments**:

- `response` (`Response`): The response from the Kraken Futures API

**Returns**:

`dict`: The JSON response from the Kraken Futures API

<a id="exchanges.kraken_futures.KrakenFutures.make_request"></a>

#### make\_request

```python
def make_request(request: Request,
                 authenticated: Optional[bool] = False) -> dict
```

Make an authenticated request to exchange endpoint, verify HTTP response code and return response JSON

:see: https://docs.futures.kraken.com/`http`-api-http-api-introduction-authentication

TODO: Handle rate limiting errors, adding exponential backoff and retry logic.

<a id="exchanges.kraken_futures.KrakenFutures.load_exchange_pairs"></a>

#### load\_exchange\_pairs

```python
def load_exchange_pairs() -> List[Pair]
```

Kraken futures calls BTC XBT, so we need to convert it to BTC
Only support Perpetual Linear Multi-Collateral Futures for now

:see: https://docs.futures.kraken.com/`http`-api-trading-v3-api-market-data-get-tickers

<a id="exchanges.kraken_futures.KrakenFutures.get_order_book"></a>

#### get\_order\_book

```python
def get_order_book(pair: str, *args, **kwargs) -> OrderBook
```

:see: https://docs.futures.kraken.com/`http`-api-trading-v3-api-market-data-get-orderbook

<a id="exchanges.kraken_futures.KrakenFutures.execute_market_order"></a>

#### execute\_market\_order

```python
def execute_market_order(pair: str,
                         order_size: float | int,
                         action: OrderAction = OrderAction.BUY) -> MarketOrder
```

Execute a spot market order for a given trading pair and order size.

Kraken futures market orders are executed in contracts, not the base asset. Market orders are also protected
from a 1% price slippage so orders may not be filled if the market does not have enough liquidity.

**Arguments**:

- `pair` (`str`): The trading pair to execute the market order for
- `order_size` (`float`): How much of the asset to buy
- `action` (`[OrderAction]`): The action to take, defaults to `OrderAction.BUY`

**Returns**:

`str`: The order ID of the executed market order

<a id="exchanges.exceptions"></a>

# exchanges.exceptions

<a id="exchanges.exceptions.DocDefaultException"></a>

## DocDefaultException Objects

```python
class DocDefaultException(ExchangeException)
```

Subclass exceptions use docstring as default message

<a id="exchanges.exceptions.ExchangeAuthenticationError"></a>

## ExchangeAuthenticationError Objects

```python
class ExchangeAuthenticationError(DocDefaultException)
```

There was a problem authenticating with this exchange

<a id="exchanges.exceptions.ExchangeBadResponseError"></a>

## ExchangeBadResponseError Objects

```python
class ExchangeBadResponseError(ExchangeException)
```

The exchange returned a bad response

<a id="exchanges.exceptions.ExchangeRateLimitExceededError"></a>

## ExchangeRateLimitExceededError Objects

```python
class ExchangeRateLimitExceededError(ExchangeException)
```

The exchange's API rate limit was exceeded

<a id="exchanges.exceptions.ExchangeInsufficientFundsError"></a>

## ExchangeInsufficientFundsError Objects

```python
class ExchangeInsufficientFundsError(DocDefaultException)
```

Insufficient funds in account to execute order

<a id="exchanges.exceptions.ExchangeLiquidityError"></a>

## ExchangeLiquidityError Objects

```python
class ExchangeLiquidityError(DocDefaultException)
```

Insufficient liquidity in orderbook to fill order

<a id="exchanges.exceptions.ExchangePairDoesNotExistError"></a>

## ExchangePairDoesNotExistError Objects

```python
class ExchangePairDoesNotExistError(DocDefaultException)
```

The pair does not exist on this exchange

<a id="exchanges.base"></a>

# exchanges.base

<a id="exchanges.base.Pair"></a>

## Pair Objects

```python
@dataclass
class Pair()
```

A cryptocurrency trading pair, normalized to the base and quote symbols, with the symbol
to use when querying the `CryptoCurrencyExchange` API.

<a id="exchanges.base.MarketOrder"></a>

## MarketOrder Objects

```python
@dataclass
class MarketOrder()
```

<a id="exchanges.base.MarketOrder.fills"></a>

#### fills

(price, quantity)

<a id="exchanges.base.OrderBook"></a>

## OrderBook Objects

```python
@dataclass
class OrderBook()
```

Represents an exchange orderbook with orders on the buy (bids) and sell (asks) sides.

The orderbook is useful when trying to determine the market price of an asset. Without which the
order could suffer from slippage, where the price of the order is not what was expected due to the
lack of liquidity.

<a id="exchanges.base.CryptocurrencyExchange"></a>

## CryptocurrencyExchange Objects

```python
class CryptocurrencyExchange(ABC)
```

Base class for cryptocurrency exchange API clients.

<a id="exchanges.base.CryptocurrencyExchange.__init__"></a>

#### \_\_init\_\_

```python
def __init__(api_key: str,
             api_secret: str,
             testnet: bool = False,
             logger: Optional[logging.Logger] = None,
             usd_stablecoin: Optional[str] = None)
```

**Arguments**:

- `api_key` (`str`): Exchange HMAC API key
- `api_secret` (`str`): Exchange HMAC API secret
- `[testnet]` (`bool`): Whether this exchange instance should use the exchange testnet or not
- `logger` (`[logging.Logger]`): Optional logger to use for logging
- `usd_stablecoin` (`[str]`): The stable-coin to use for USD transactions, as some exchanges only support
stable-coins for USD transactions.

<a id="exchanges.base.CryptocurrencyExchange.name"></a>

#### name

```python
@property
@abstractmethod
def name() -> str
```

Friendly name of the exchange - presented to the user.

<a id="exchanges.base.CryptocurrencyExchange.make_request"></a>

#### make\_request

```python
@abstractmethod
def make_request(request: Request,
                 authenticated: Optional[bool] = False) -> dict
```

Prepare and send a request to the exchange API. This method should be used to handle any exchange-specific
requirements for request headers, query parameters, and request bodies.

<a id="exchanges.base.CryptocurrencyExchange.send_request"></a>

#### send\_request

```python
@staticmethod
def send_request(prepared_request: PreparedRequest,
                 callback: Optional[Callable] = None) -> dict
```

Send a prepared request to the exchange API and return the JSON response. Raise an ExchangeException if the

response status code is not 200.

Each exchange will have differing requirements for request headers, query parameters, and request bodies. This
method is used to standardize the process of sending requests to the exchange API, and handle any errors that
may arise. Handling rate limits and exponential backoff should be done in the `CryptocurrencyExchange` subclass.

**Arguments**:

- `prepared_request` (`PreparedRequest`): The request to send to the exchange API
- `callback` (`[Callable]`): Optional callback to check the response for errors before returning its json

**Raises**:

- `None`: `ExchangeException`

**Returns**:

dict

<a id="exchanges.base.CryptocurrencyExchange.load_exchange_pairs"></a>

#### load\_exchange\_pairs

```python
@abstractmethod
def load_exchange_pairs() -> List[Pair]
```

Returns a list of trading pairs available on the exchange. Each pair should have a normalized base and quote.

<a id="exchanges.base.CryptocurrencyExchange.get_order_book"></a>

#### get\_order\_book

```python
@abstractmethod
def get_order_book(pair: str) -> OrderBook
```

**Arguments**:

- `pair` (`str`): The trading pair to get the order book for
- `[depth_limit]` (`int`): Additional arguments to pass to the request

<a id="exchanges.base.CryptocurrencyExchange.execute_market_order"></a>

#### execute\_market\_order

```python
@abstractmethod
def execute_market_order(pair: str,
                         order_size: float | int,
                         action: OrderAction = OrderAction.BUY) -> MarketOrder
```

Execute a spot market order for a given trading pair and order size.

**Arguments**:

- `pair` (`str`): The trading pair to execute the market order for
- `order_size` (`float`): How much of the asset to buy
- `action` (`[OrderAction]`): The action to take, defaults to `OrderAction.BUY`

**Returns**:

`str`: The order ID of the executed market order

<a id="exchanges.base.CryptocurrencyExchange.get_pair"></a>

#### get\_pair

```python
def get_pair(symbol: str) -> Pair
```

Get a trading pair by symbol, or base + quote symbols. This is helpful if an exchange has non-standard symbols
for a market - for example Kraken Futures which uses "pi_xbtusd" for the BTCUSD trading pair.

TODO:
    This could be optimized to O(1) by using dicts to store the pairs, just iterate over the list now.
    - Store two dicts:
        - symbol as the key and the Pair object as the value.
        - base + quote as the key and the Pair object as the value.

<a id="exchanges.binance"></a>

# exchanges.binance

<a id="exchanges.binance.Binance"></a>

## Binance Objects

```python
class Binance(CryptocurrencyExchange)
```

<a id="exchanges.binance.Binance.make_request"></a>

#### make\_request

```python
def make_request(request: Request,
                 authenticated: Optional[bool] = False) -> dict
```

Make an optionally authenticated request to exchange endpoint, verify HTTP response code

and return response JSON.

**Arguments**:

- `request` (`Request`): The request to make, with a URL, method, and any data or headers
- `authenticated` (`[bool]`): Whether the request should be authenticated with the API key and secret

**Returns**:

`dict`: The JSON response from the exchange
TODO: Handle generic rate limit errors, adding exponential backoff and retry logic.

<a id="exchanges.binance.Binance.get_order_book"></a>

#### get\_order\_book

```python
def get_order_book(pair: str, *args, **kwargs) -> OrderBook
```

:see: https://binance-docs.github.io/apidocs/spot/en/`order`-book

<a id="exchanges.binance.Binance.execute_market_order"></a>

#### execute\_market\_order

```python
def execute_market_order(pair: str,
                         order_size: float,
                         action: OrderAction = OrderAction.BUY) -> MarketOrder
```

Execute a spot market order for a given trading pair and order size.

**Arguments**:

- `pair` (`str`): The trading pair to execute the market order for
- `order_size` (`float`): How much of the asset to buy
- `action` (`[OrderAction]`): The action to take, defaults to `OrderAction.BUY`

**Returns**:

`str`: The order ID of the executed market order

