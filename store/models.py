import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils.text import slugify


def validate_image_size(f):
    if f.size > settings.MAX_IMAGE_SIZE:
        raise ValidationError("L'image dépasse la taille maximale de 3 Mo.")


class Category(models.Model):
    name = models.CharField("nom", max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name = "catégorie"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("store:category", args=[self.slug])


class Product(models.Model):
    PLATFORM_CHOICES = [("PS4", "PS4"), ("PS5", "PS5"), ("XBOX", "Xbox"), ("PC", "PC")]
    CONDITION_CHOICES = [("neuf", "Neuf"), ("occasion", "Occasion")]

    name = models.CharField("nom", max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    sku = models.CharField("référence", max_length=40, unique=True, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="catégorie")
    platform = models.CharField("plateforme", max_length=8, choices=PLATFORM_CHOICES, blank=True)
    condition = models.CharField("état", max_length=10, choices=CONDITION_CHOICES, default="neuf")
    description = models.TextField(blank=True)
    warranty = models.CharField("garantie", max_length=120, blank=True)
    price = models.DecimalField("prix", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    stock = models.PositiveIntegerField("stock", default=0, editable=False)
    alert_threshold = models.PositiveIntegerField("seuil d'alerte", default=2)
    attributes = models.JSONField("caractéristiques", default=dict, blank=True)
    is_published = models.BooleanField("publié", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "produit"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:160] or "produit"
            slug, i = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, i = f"{base}-{i}", i + 1
            self.slug = slug
        if self.sku == "":
            self.sku = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product", args=[self.slug])

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return self.stock <= self.alert_threshold

    @property
    def main_image(self):
        return self.images.first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        validators=[FileExtensionValidator(settings.ALLOWED_IMAGE_EXTENSIONS), validate_image_size],
    )
    alt = models.CharField("texte alternatif", max_length=160, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]


class StockMovement(models.Model):
    IN, OUT = "in", "out"
    KIND_CHOICES = [(IN, "Entrée"), (OUT, "Sortie")]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField("type", max_length=3, choices=KIND_CHOICES)
    quantity = models.PositiveIntegerField("quantité", validators=[MinValueValidator(1)])
    reason = models.CharField("motif", max_length=160)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    stock_after = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @classmethod
    @transaction.atomic
    def record(cls, product, kind, quantity, reason, author=None):
        """PS-14 : enregistre un mouvement et recalcule le stock ; refuse un stock négatif."""
        if quantity <= 0:
            raise ValidationError("La quantité doit être positive.")
        locked = Product.objects.select_for_update().get(pk=product.pk)
        if kind == cls.OUT and quantity > locked.stock:
            raise ValidationError(
                f"Stock insuffisant pour « {locked.name} » ({locked.stock} disponible(s))."
            )
        delta = quantity if kind == cls.IN else -quantity
        Product.objects.filter(pk=locked.pk).update(stock=F("stock") + delta)
        locked.refresh_from_db(fields=["stock"])
        product.stock = locked.stock
        return cls.objects.create(
            product=locked, kind=kind, quantity=quantity, reason=reason,
            author=author, stock_after=locked.stock,
        )


class Order(models.Model):
    RECEIVED, CONFIRMED, PREPARING, READY, DONE, CANCELLED = (
        "recue", "confirmee", "preparation", "prete", "terminee", "annulee",
    )
    STATUS_CHOICES = [
        (RECEIVED, "Reçue"),
        (CONFIRMED, "Confirmée"),
        (PREPARING, "En préparation"),
        (READY, "Prête / expédiée"),
        (DONE, "Terminée"),
        (CANCELLED, "Annulée"),
    ]
    # PS-17 : transitions autorisées.
    TRANSITIONS = {
        RECEIVED: [CONFIRMED, CANCELLED],
        CONFIRMED: [PREPARING, CANCELLED],
        PREPARING: [READY, CANCELLED],
        READY: [DONE],
        DONE: [],
        CANCELLED: [],
    }
    DELIVERY_CHOICES = [("retrait", "Retrait en magasin"), ("livraison", "Livraison")]

    reference = models.CharField("référence", max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="orders", verbose_name="compte client")
    first_name = models.CharField("prénom", max_length=80)
    last_name = models.CharField("nom", max_length=80)
    email = models.EmailField("e-mail")
    phone = models.CharField("téléphone", max_length=30)
    delivery_mode = models.CharField("mode de réception", max_length=10, choices=DELIVERY_CHOICES)
    address = models.CharField("adresse", max_length=255, blank=True)
    city = models.CharField("ville", max_length=80, blank=True)
    notes = models.TextField("remarques", blank=True)
    status = models.CharField("statut", max_length=12, choices=STATUS_CHOICES, default=RECEIVED)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "commande"

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if not self.reference:
            while True:
                ref = "PS-" + secrets.token_hex(4).upper()
                if not Order.objects.filter(reference=ref).exists():
                    self.reference = ref
                    break
        super().save(*args, **kwargs)

    @property
    def customer_name(self):
        return f"{self.first_name} {self.last_name}"

    def allowed_transitions(self):
        return [(s, dict(self.STATUS_CHOICES)[s]) for s in self.TRANSITIONS[self.status]]

    @transaction.atomic
    def change_status(self, new_status, user=None, comment=""):
        if new_status not in self.TRANSITIONS.get(self.status, []):
            raise ValidationError("Transition de statut non autorisée.")
        old = self.status
        if new_status == self.CANCELLED:
            # Le stock réservé à la création est restitué.
            for line in self.lines.select_related("product"):
                if line.product_id:
                    StockMovement.record(line.product, StockMovement.IN, line.quantity,
                                         f"Annulation commande {self.reference}", user)
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=self, old_status=old, new_status=new_status,
                                          author=user, comment=comment)


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=160)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=12, blank=True)
    new_status = models.CharField(max_length=12)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def get_new_status_display(self):
        return dict(Order.STATUS_CHOICES).get(self.new_status, self.new_status)

    def get_old_status_display(self):
        return dict(Order.STATUS_CHOICES).get(self.old_status, self.old_status)
