from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Order, OrderLine, OrderStatusHistory, Product, StockMovement


@transaction.atomic
def place_order(cart, customer_data, user=None):
    """PS-09 : crée la commande, revérifie la disponibilité et réserve le stock à la création."""
    items = cart.items()
    if not items:
        raise ValidationError("Votre panier est vide.")

    ids = [i["product"].pk for i in items]
    locked = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids, is_published=True)}
    errors = []
    for item in items:
        p = locked.get(item["product"].pk)
        if p is None or item["quantity"] > p.stock:
            errors.append(f"« {item['product'].name} » : quantité demandée indisponible "
                          f"({p.stock if p else 0} en stock).")
    if errors:
        raise ValidationError(errors)

    order = Order.objects.create(**customer_data, user=user if user and user.is_authenticated else None)
    total = Decimal("0")
    for item in items:
        p = locked[item["product"].pk]
        OrderLine.objects.create(order=order, product=p, product_name=p.name,
                                 unit_price=p.price, quantity=item["quantity"])
        StockMovement.record(p, StockMovement.OUT, item["quantity"], f"Commande {order.reference}")
        total += p.price * item["quantity"]
    order.total = total
    order.save(update_fields=["total"])
    OrderStatusHistory.objects.create(order=order, new_status=Order.RECEIVED, comment="Commande créée")
    cart.clear()
    return order
