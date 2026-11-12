from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm, TrackingForm
from .models import Category, Order, Product
from .services import place_order


def _published():
    return Product.objects.filter(is_published=True).select_related("category").prefetch_related("images")


# Carrousel de l'accueil : un univers par visuel détouré (static/img/hero/).
ORBIT_ITEMS = [
    {"title": "Console", "subtitle": "PS5", "label": "Console PS5", "image": "img/hero/ps5.webp",
     "alt": "Console PlayStation 5 et sa manette", "category": "consoles", "platform": "",
     "eyebrow": "Consoles PlayStation", "accent": "#9fb4f5",
     "description": "PlayStation 5 et éditions spéciales, neuves ou d'occasion, avec l'état et la garantie indiqués.",
     "highlights": ["PS5", "Éditions spéciales", "Neuf / occasion", "Garantie indiquée"]},
    {"title": "Manette", "subtitle": "Sans fil", "label": "Manettes", "image": "img/hero/manette.webp",
     "alt": "Manette de jeu noire", "category": "accessoires", "platform": "",
     "eyebrow": "Accessoires", "accent": "#c9ccd3",
     "description": "Manettes et stations de recharge pour jouer à deux ou garder une manette toujours prête.",
     "highlights": ["Manettes", "Stations de recharge", "PS4", "PS5"]},
    {"title": "Casque", "subtitle": "Gaming", "label": "Casques gaming", "image": "img/hero/casque.webp",
     "alt": "Casque audio gaming noir", "category": "accessoires", "platform": "",
     "eyebrow": "Audio et VR", "accent": "#f6a37c",
     "description": "Casques audio pour les longues sessions et casques VR pour l'immersion totale.",
     "highlights": ["Casques audio", "Micro intégré", "Casques VR"]},
    {"title": "Univers", "subtitle": "Xbox", "label": "Jeux Xbox", "image": "img/hero/xbox.webp",
     "alt": "Console Xbox Series X et sa manette", "category": "jeux", "platform": "XBOX",
     "eyebrow": "Jeux Xbox", "accent": "#bcd98e",
     "description": "Les jeux physiques compatibles Xbox, filtrés directement dans le catalogue.",
     "highlights": ["Jeux physiques", "Xbox", "Disponibilité vérifiée"]},
    {"title": "Édition", "subtitle": "Néon", "label": "Manettes colorées", "image": "img/hero/manette-neon.webp",
     "alt": "Manette de jeu aux couleurs turquoise et violet", "category": "accessoires", "platform": "",
     "eyebrow": "Accessoires", "accent": "#f2a6c6",
     "description": "Des manettes aux coloris originaux pour personnaliser votre setup.",
     "highlights": ["Coloris originaux", "Sans fil", "Accessoires"]},
]


def _orbit_items():
    published = Product.objects.filter(is_published=True)
    items = []
    for item in ORBIT_ITEMS:
        qs = published.filter(category__slug=item["category"])
        if item["platform"]:
            qs = qs.filter(platform=item["platform"])
        url = reverse("store:category", args=[item["category"]])
        if item["platform"]:
            url += "?platform=" + item["platform"]
        items.append({**item, "count": qs.count(), "url": url})
    return items


def home(request):
    return render(request, "store/home.html", {
        "latest": _published().order_by("-created_at")[:8],
        "orbit_items": _orbit_items(),
    })


def product_list(request, slug=None):
    products = _published()
    category = None
    if slug:
        category = get_object_or_404(Category, slug=slug)
        products = products.filter(category=category)

    q = request.GET.get("q", "").strip()
    platform = request.GET.get("platform", "")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(sku__icontains=q))
    if platform in dict(Product.PLATFORM_CHOICES):
        products = products.filter(platform=platform)
    if request.GET.get("dispo") == "1":
        products = products.filter(stock__gt=0)

    sort = request.GET.get("tri", "")
    products = products.order_by({"prix": "price", "-prix": "-price", "recent": "-created_at"}.get(sort, "name"))

    page = Paginator(products, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "store/product_list.html", {
        "category": category, "page": page, "q": q, "platform": platform, "sort": sort,
        "platforms": Product.PLATFORM_CHOICES, "querystring": params.urlencode(),
    })


def product_detail(request, slug):
    product = get_object_or_404(_published(), slug=slug)
    related = _published().filter(category=product.category).exclude(pk=product.pk)[:4]
    return render(request, "store/product_detail.html", {
        "product": product, "related": related, "in_cart": Cart(request).quantity_of(product),
    })


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_published=True)
    cart = Cart(request)
    try:
        qty = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        qty = 1
    new_qty = cart.quantity_of(product) + qty
    if new_qty > product.stock:
        messages.error(request, f"Stock insuffisant : {product.stock} disponible(s) pour « {product.name} ».")
    else:
        cart.set(product, new_qty)
        messages.success(request, f"« {product.name} » ajouté au panier.")
    return redirect(request.POST.get("next") or "store:cart")


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = Cart(request)
    try:
        qty = int(request.POST.get("quantity", 0))
    except ValueError:
        qty = 0
    if qty > product.stock:
        messages.error(request, f"Seulement {product.stock} unité(s) disponible(s) pour « {product.name} ».")
        qty = product.stock
    cart.set(product, qty)
    return redirect("store:cart")


@require_POST
def cart_remove(request, pk):
    product = get_object_or_404(Product, pk=pk)
    Cart(request).remove(product)
    messages.info(request, f"« {product.name} » retiré du panier.")
    return redirect("store:cart")


def cart_detail(request):
    cart = Cart(request)
    items = cart.items()
    return render(request, "store/cart.html", {
        "items": items, "total": cart.total(items),
        "all_available": all(i["available"] for i in items),
    })


def checkout(request):
    cart = Cart(request)
    items = cart.items()
    if not items:
        messages.info(request, "Votre panier est vide.")
        return redirect("store:products")

    initial = {}
    if request.user.is_authenticated:
        last = request.user.orders.first()
        initial = {"first_name": request.user.first_name, "last_name": request.user.last_name, "email": request.user.email}
        if last:
            initial.update(phone=last.phone, address=last.address, city=last.city, delivery_mode=last.delivery_mode)
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            order = place_order(cart, form.cleaned_data, request.user)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
            return redirect("store:cart")
        request.session["last_order"] = order.reference
        return redirect("store:confirmation", reference=order.reference)
    return render(request, "store/checkout.html", {"form": form, "items": items, "total": cart.total(items)})


def _owns_order(request, order):
    return request.user.is_authenticated and order.user_id == request.user.id


def confirmation(request, reference):
    # Seul le navigateur qui a passé la commande voit la confirmation directe.
    order = get_object_or_404(Order, reference=reference)
    if request.session.get("last_order") != reference and not _owns_order(request, order):
        return redirect("store:tracking")
    return render(request, "store/confirmation.html", {"order": order})


def tracking(request):
    form = TrackingForm(request.POST or None)
    order = None
    if request.method == "POST" and form.is_valid():
        order = Order.objects.filter(reference=form.cleaned_data["reference"],
                                     email__iexact=form.cleaned_data["email"]).first()
        if order is None:
            messages.error(request, "Aucune commande ne correspond à ces informations.")
    return render(request, "store/tracking.html", {"form": form, "order": order,
                                                   "steps": Order.STATUS_CHOICES[:5]})
