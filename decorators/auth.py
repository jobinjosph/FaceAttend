from functools import wraps

from flask import abort, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    allowed = {role.upper() for role in allowed_roles}

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped_view(*args, **kwargs):
            if session.get("role") not in allowed:
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator
