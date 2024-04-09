from unittest.mock import patch

import pytest
from requests import Response
from tenacity import RetryError

from scec import Broker
from scec.exchanges.exceptions import ExchangeBadResponseError


@pytest.mark.parametrize(
    "status_code,encoding,_content", [
        (400, "application/text", "Bad Request"),
        (403, "utf-8", "Forbidden"),
        (500, "application/json", b'{"error": "Internal Server Error"}'),
    ]
)
@patch("scec.exchanges.base.Session.send")
async def test_api_non_200_status_code_response_raises_exception_with_response_object(
    mock_send, binance, status_code, encoding, _content
):
    resp = Response()
    resp.status_code = status_code
    resp.encoding = encoding
    resp._content = _content

    mock_send.return_value = resp

    with pytest.raises(ExchangeBadResponseError) as exc_info:
        binance.get_order_book("BTCUSDT")
    assert exc_info.value.response == resp


@patch("scec.exchanges.base.Session.send")
async def test_make_request_retries_on_connection_error(mock_send, binance):
    mock_send.side_effect = ConnectionError("Max retries exceeded, couldn't open socket.")

    with pytest.raises(RetryError) as exc_info:
        binance.get_order_book("BTCUSDT")

    assert type(exc_info.value) is RetryError
    original_error = exc_info.value.last_attempt.exception()
    assert original_error is mock_send.side_effect


@patch("scec.exchanges.base.Session.send")
async def test_get_order_book_with_connection_errors_is_retried(mock_session_send, binance):
    valid_response = Response()
    valid_response.status_code = 200
    valid_response._content = b'{"lastUpdateId": 1113745, "bids": [], "asks": []}'
    valid_response.encoding = "application/json"

    # Send a ConnectionError first, then a successful response
    mock_session_send.side_effect = [
        ConnectionError("Max retries exceeded, couldn't open socket."),
        valid_response
    ]
    binance.get_order_book("ADAEUR")
    assert mock_session_send.call_count == 2
