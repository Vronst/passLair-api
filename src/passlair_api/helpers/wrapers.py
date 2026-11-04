"""Route decorators."""

from collections.abc import Callable
from functools import wraps

from werkzeug import Response

from passlair_api.helpers.functions import check_login_redirect


def login_required[**P, R](  # pylint: disable=invalid-name
    func: Callable[P, R],
) -> Callable[P, R | Response]:
    """Redirects anonymous users to the login page instead of running func."""

    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        result = check_login_redirect()
        if isinstance(result, Response):
            return result

        return func(*args, **kwargs)

    return wrapped
