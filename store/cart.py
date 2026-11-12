from decimal import Decimal

from .models import Product

SESSION_KEY = "cart"


class Cart:
    """Panier stocké en session : {product_id: quantité}. Le prix vient toujours du catalogue."""

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.get(SESSION_KEY, {})

    def _save(self):
        self.session[SESSION_KEY] = self.data
        self.session.modified = True

    def quantity_of(self, product):
        return self.data.get(str(product.pk), 0)

    def set(self, product, quantity):
        if quantity <= 0:
            self.remove(product)
        else:
            self.data[str(product.pk)] = quantity
            self._save()

    def remove(self, product):
        self.data.pop(str(product.pk), None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    def items(self):
        products = Product.objects.filter(pk__in=self.data.keys(), is_published=True).prefetch_related("images")
        found = {str(p.pk): p for p in products}
        # Les produits retirés du catalogue disparaissent du panier.
        for pid in list(self.data):
            if pid not in found:
                self.data.pop(pid)
                self._save()
        result = []
        for pid, qty in self.data.items():
            p = found[pid]
            result.append({"product": p, "quantity": qty, "subtotal": p.price * qty,
                           "available": qty <= p.stock})
        return result

    def total(self, items=None):
        return sum((i["subtotal"] for i in (items or self.items())), Decimal("0"))

    def __len__(self):
        return sum(self.data.values())
