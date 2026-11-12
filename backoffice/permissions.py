"""PS-18 : rôles contrôlés côté serveur."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMIN_GROUP = "Administrateur"
EMPLOYEE_GROUP = "Employé"


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists())


def is_employee(user):
    return user.is_authenticated and (is_admin(user) or user.groups.filter(name=EMPLOYEE_GROUP).exists())


def role_of(user):
    if is_admin(user):
        return "Administrateur"
    if is_employee(user):
        return "Employé"
    return None


def _require(check):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not check(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


staff_required = _require(is_employee)
admin_required = _require(is_admin)
