class ExchangeException(Exception):
    ...


class DocDefaultException(ExchangeException):
    """Subclass exceptions use docstring as default message"""
    def __init__(self, msg=None, *args, **kwargs):
        super().__init__(msg or self.__doc__, *args, **kwargs)


class ExchangeAuthenticationError(DocDefaultException):
    """There was a problem authenticating with this exchange"""


class ExchangeBadResponseError(ExchangeException):
    """The exchange returned a bad response"""
    def __init__(self, msg=None, response=None, *args, **kwargs):
        # So that we can later inspect the response that caused the error, to handle rate limiting, etc.
        super().__init__(msg, *args, **kwargs)
        self.response = response


class ExchangeRateLimitExceededError(ExchangeException):
    """The exchange's API rate limit was exceeded"""


class ExchangeInsufficientFundsError(DocDefaultException):
    """Insufficient funds in account to execute order"""


class ExchangeLiquidityError(DocDefaultException):
    """Insufficient liquidity in orderbook to fill order"""


class ExchangePairDoesNotExistError(DocDefaultException):
    """The pair does not exist on this exchange"""
