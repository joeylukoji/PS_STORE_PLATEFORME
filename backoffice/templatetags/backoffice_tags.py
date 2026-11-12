from django import template

from backoffice.permissions import is_admin, is_employee

register = template.Library()


@register.filter
def admin_user(user):
    return is_admin(user)


@register.filter
def staff_user(user):
    return is_employee(user)
