import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from store.models import Order, OrderLine, Product, ProductImage, StockMovement

from .forms import (LoginForm, PeriodForm, ProductForm, ProductImageForm, RoleForm,
                    StockMovementForm, UserCreateForm)
from .permissions import ADMIN_GROUP, EMPLOYEE_GROUP, admin_required, role_of, staff_required

logger = logging.getLogger("psstore")


class LoginView(auth_views.LoginView):
    template_name = "backoffice/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


# ---------- Tableau de bord (PS-19) ----------

@staff_required
def dashboard(request):
    today = timezone.localdate()
    low_stock = Product.objects.filter(stock__lte=F("alert_threshold")).order_by("stock")
    return render(request, "backoffice/dashboard.html", {
        "recent_orders": Order.objects.all()[:8],
        "low_stock": low_stock[:10],
        "low_stock_count": low_stock.count(),
        "pending_count": Order.objects.filter(status__in=[Order.RECEIVED, Order.CONFIRMED, Order.PREPARING]).count(),
        "today_count": Order.objects.filter(created_at__date=today).count(),
        "product_count": Product.objects.filter(is_published=True).count(),
    })


# ---------- Produits (PS-12, PS-13) ----------

@admin_required
def product_list(request):
    products = Product.objects.select_related("category")
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if request.GET.get("statut") == "masque":
        products = products.filter(is_published=False)
    elif request.GET.get("statut") == "publie":
        products = products.filter(is_published=True)
    page = Paginator(products, 20).get_page(request.GET.get("page"))
    return render(request, "backoffice/product_list.html", {"page": page, "q": q})


@admin_required
def product_form(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        logger.info("Produit %s enregistré par %s", product.pk, request.user)
        messages.success(request, "Produit enregistré.")
        return redirect("backoffice:product_edit", pk=product.pk)
    return render(request, "backoffice/product_form.html", {
        "form": form, "product": product,
        "image_form": ProductImageForm() if product else None,
    })


@admin_required
@require_POST
def product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_published = not product.is_published
    product.save(update_fields=["is_published", "updated_at"])
    messages.success(request, f"« {product.name} » est maintenant {'publié' if product.is_published else 'masqué'}.")
    return redirect(request.POST.get("next") or "backoffice:products")


@admin_required
@require_POST
def image_add(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductImageForm(request.POST, request.FILES)
    if form.is_valid():
        img = form.save(commit=False)
        img.product = product
        img.position = product.images.count()
        img.save()
        messages.success(request, "Image ajoutée.")
    else:
        for errs in form.errors.values():
            for e in errs:
                messages.error(request, e)
    return redirect("backoffice:product_edit", pk=pk)


@admin_required
@require_POST
def image_delete(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    product_pk = image.product_id
    image.image.delete(save=False)
    image.delete()
    messages.info(request, "Image supprimée.")
    return redirect("backoffice:product_edit", pk=product_pk)


# ---------- Stock (PS-14, PS-15) ----------

@staff_required
def stock(request):
    initial = {"product": request.GET.get("produit")} if request.GET.get("produit") else None
    form = StockMovementForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            StockMovement.record(d["product"], d["kind"], d["quantity"], d["reason"], request.user)
        except ValidationError as e:
            form.add_error("quantity", e.messages[0])
        else:
            messages.success(request, "Mouvement enregistré.")
            return redirect("backoffice:stock")
    movements = StockMovement.objects.select_related("product", "author")
    if request.GET.get("produit"):
        movements = movements.filter(product_id=request.GET["produit"])
    page = Paginator(movements, 25).get_page(request.GET.get("page"))
    return render(request, "backoffice/stock.html", {
        "form": form, "page": page,
        "products": Product.objects.order_by("name"),
    })


# ---------- Commandes (PS-16, PS-17) ----------

@staff_required
def order_list(request):
    orders = Order.objects.annotate(items=Sum("lines__quantity")).order_by("-created_at")
    status = request.GET.get("statut", "")
    q = request.GET.get("q", "").strip()
    if status:
        orders = orders.filter(status=status)
    if q:
        orders = orders.filter(Q(reference__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    page = Paginator(orders, 20).get_page(request.GET.get("page"))
    return render(request, "backoffice/order_list.html", {
        "page": page, "status": status, "q": q, "statuses": Order.STATUS_CHOICES,
    })


@staff_required
def order_detail(request, reference):
    order = get_object_or_404(Order.objects.prefetch_related("lines", "history__author"), reference=reference)
    if request.method == "POST":
        try:
            order.change_status(request.POST.get("status", ""), request.user, request.POST.get("comment", "")[:255])
            messages.success(request, f"Statut mis à jour : {order.get_status_display()}.")
        except ValidationError as e:
            messages.error(request, e.messages[0])
        return redirect("backoffice:order_detail", reference=reference)
    return render(request, "backoffice/order_detail.html", {"order": order})


# ---------- Rapports (PS-20) ----------

@admin_required
def reports(request):
    today = timezone.localdate()
    form = PeriodForm(request.GET or {"start": today - timedelta(days=29), "end": today})
    ctx = {"form": form}
    if form.is_valid():
        start, end = form.cleaned_data["start"], form.cleaned_data["end"]
        # Règle : chiffre d'affaires = commandes non annulées créées sur la période.
        orders = Order.objects.filter(created_at__date__gte=start, created_at__date__lte=end).exclude(status=Order.CANCELLED)
        agg = orders.aggregate(total=Sum("total"), count=Count("id"))
        by_day = list(orders.annotate(day=TruncDate("created_at")).values("day")
                      .annotate(total=Sum("total"), count=Count("id")).order_by("day"))
        top = (OrderLine.objects.filter(order__in=orders).values("product_name")
               .annotate(qty=Sum("quantity"), revenue=Sum(F("quantity") * F("unit_price"))).order_by("-qty")[:10])
        max_day = max((d["total"] for d in by_day), default=0) or 1
        for d in by_day:
            d["pct"] = int(d["total"] * 100 / max_day)
        ctx.update(start=start, end=end, total=agg["total"] or 0, count=agg["count"],
                   average=(agg["total"] / agg["count"]) if agg["count"] else 0, by_day=by_day, top=top)
    return render(request, "backoffice/reports.html", ctx)


# ---------- Utilisateurs et rôles (PS-18) ----------

@admin_required
def users(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Compte « {user.username} » créé.")
        return redirect("backoffice:users")
    accounts = User.objects.prefetch_related("groups").order_by("username")
    return render(request, "backoffice/users.html", {
        "form": form, "accounts": [(u, role_of(u)) for u in accounts],
    })


@admin_required
@require_POST
def user_role(request, pk):
    account = get_object_or_404(User, pk=pk)
    if account == request.user:
        messages.error(request, "Vous ne pouvez pas modifier votre propre rôle.")
        return redirect("backoffice:users")
    form = RoleForm(request.POST)
    if form.is_valid():
        role = form.cleaned_data["role"]
        account.groups.remove(*Group.objects.filter(name__in=[ADMIN_GROUP, EMPLOYEE_GROUP]))
        if role:
            account.groups.add(Group.objects.get_or_create(name=role)[0])
        account.is_active = form.cleaned_data["is_active"]
        account.save(update_fields=["is_active"])
        messages.success(request, f"Compte « {account.username} » mis à jour.")
    return redirect("backoffice:users")
