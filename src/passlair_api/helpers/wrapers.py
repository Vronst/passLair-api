from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from werkzeug import Response

from passlair_api.helpers.functions import check_login_redirect

P = ParamSpec("P")
R = TypeVar("R")


def login_required(func: Callable[P, R]) -> Callable[P, R | Response]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        result = check_login_redirect()
        if isinstance(result, Response):
            return result

        return func(*args, **kwargs)

    return wrapped
