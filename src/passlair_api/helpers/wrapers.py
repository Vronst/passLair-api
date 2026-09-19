from typing import Callable, ParamSpec, TypeVar
from functools import wraps
from flask import redirect, session, url_for
from werkzeug import Response


P = ParamSpec("P")
R = TypeVar("R")


def login_required(func: Callable[P, R]) -> Callable[P, R | Response]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        if session.get("current_user"):
            return func(*args, **kwargs)

        return redirect(url_for("auth.login"))

    return wrapped
