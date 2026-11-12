from functools import partial

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from .account_forms import CustomerLoginForm, ProfileForm, SignupForm
from .models import Order

customer_required = partial(login_required, login_url="store:login")


def _safe_next(request):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return nxt
    return None


class CustomerLoginView(auth_views.LoginView):
    template_name = "store/account/login.html"
    authentication_form = CustomerLoginForm
    redirect_authenticated_user = True
    next_page = reverse_lazy("store:account")

    def form_valid(self, form):
        messages.success(self.request, f"Bonjour {form.get_user().first_name or form.get_user().username} !")
        return super().form_valid(form)


class CustomerLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("store:home")


def signup(request):
    if request.user.is_authenticated:
        return redirect("store:account")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Votre compte a été créé. Bienvenue sur PS STORE !")
        return redirect(_safe_next(request) or "store:account")
    return render(request, "store/account/signup.html", {"form": form, "next": _safe_next(request) or ""})


@customer_required
def account(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil mis à jour.")
        return redirect("store:account")
    orders = request.user.orders.prefetch_related("lines")
    return render(request, "store/account/account.html", {"form": form, "orders": orders})


@customer_required
def account_order(request, reference):
    # Un client ne voit que ses propres commandes.
    order = get_object_or_404(Order.objects.prefetch_related("lines", "history"), reference=reference, user=request.user)
    return render(request, "store/account/order.html", {"order": order, "steps": Order.STATUS_CHOICES[:5]})


class CustomerPasswordChangeView(auth_views.PasswordChangeView):
    template_name = "store/account/password.html"
    success_url = reverse_lazy("store:account")

    def form_valid(self, form):
        messages.success(self.request, "Mot de passe modifié.")
        return super().form_valid(form)

    @classmethod
    def as_view(cls, **kwargs):
        return customer_required(super().as_view(**kwargs))
