"""TECH-07 : tests stock, commandes, statuts et permissions."""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from backoffice.permissions import ADMIN_GROUP, EMPLOYEE_GROUP
from store.models import Category, Order, Product, StockMovement


class BaseTest(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Jeux", slug="jeux")
        self.p5 = Product.objects.create(name="Jeu PS5", category=self.cat, platform="PS5",
                                         price=Decimal("50"), is_published=True)
        self.p4 = Product.objects.create(name="Jeu PS4", category=self.cat, platform="PS4",
                                         price=Decimal("20"), is_published=True)
        self.hidden = Product.objects.create(name="Caché", category=self.cat, price=1, is_published=False)
        StockMovement.record(self.p5, StockMovement.IN, 3, "init")
        StockMovement.record(self.p4, StockMovement.IN, 1, "init")

    def checkout(self, **extra):
        data = {"first_name": "A", "last_name": "B", "email": "a@b.cd", "phone": "+243 990 000 000",
                "delivery_mode": "retrait"}
        data.update(extra)
        return self.client.post(reverse("store:checkout"), data)


class CatalogTests(BaseTest):
    def test_hidden_products_not_listed(self):
        r = self.client.get(reverse("store:products"))
        self.assertContains(r, "Jeu PS5")
        self.assertNotContains(r, "Caché")
        self.assertEqual(self.client.get(reverse("store:product", args=[self.hidden.slug])).status_code, 404)

    def test_platform_filter_and_search(self):
        r = self.client.get(reverse("store:products"), {"platform": "PS4"})
        self.assertContains(r, "Jeu PS4")
        self.assertNotContains(r, "Jeu PS5")
        r = self.client.get(reverse("store:products"), {"q": "ps5"})
        self.assertContains(r, "Jeu PS5")
        r = self.client.get(reverse("store:products"), {"q": "introuvable"})
        self.assertContains(r, "Aucun article")


class StockTests(BaseTest):
    def test_negative_stock_blocked(self):
        with self.assertRaises(ValidationError):
            StockMovement.record(self.p4, StockMovement.OUT, 2, "test")
        self.p4.refresh_from_db()
        self.assertEqual(self.p4.stock, 1)

    def test_movement_recalculates_stock(self):
        StockMovement.record(self.p5, StockMovement.OUT, 2, "vente")
        self.p5.refresh_from_db()
        self.assertEqual(self.p5.stock, 1)


class OrderTests(BaseTest):
    def test_cart_refuses_quantity_above_stock(self):
        self.client.post(reverse("store:cart_add", args=[self.p4.pk]), {"quantity": 5})
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_full_order_flow(self):
        self.client.post(reverse("store:cart_add", args=[self.p5.pk]), {"quantity": 2})
        r = self.checkout()
        order = Order.objects.get()
        self.assertRedirects(r, reverse("store:confirmation", args=[order.reference]))
        self.assertEqual(order.total, Decimal("100"))
        self.p5.refresh_from_db()
        self.assertEqual(self.p5.stock, 1)
        # Suivi : nécessite référence + e-mail
        r = self.client.post(reverse("store:tracking"), {"reference": order.reference, "email": "a@b.cd"})
        self.assertContains(r, "Reçue")
        r = self.client.post(reverse("store:tracking"), {"reference": order.reference, "email": "x@y.zz"})
        self.assertContains(r, "Aucune commande")

    def test_delivery_requires_address(self):
        self.client.post(reverse("store:cart_add", args=[self.p5.pk]), {"quantity": 1})
        r = self.checkout(delivery_mode="livraison")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_stock_rechecked_at_checkout(self):
        self.client.post(reverse("store:cart_add", args=[self.p4.pk]), {"quantity": 1})
        StockMovement.record(self.p4, StockMovement.OUT, 1, "vendu ailleurs")
        self.checkout()
        self.assertFalse(Order.objects.exists())

    def test_status_transitions_and_cancel_restores_stock(self):
        self.client.post(reverse("store:cart_add", args=[self.p5.pk]), {"quantity": 2})
        self.checkout()
        order = Order.objects.get()
        with self.assertRaises(ValidationError):
            order.change_status(Order.DONE)
        order.change_status(Order.CONFIRMED)
        order.change_status(Order.CANCELLED)
        self.p5.refresh_from_db()
        self.assertEqual(self.p5.stock, 3)
        self.assertEqual(order.history.count(), 3)


class PermissionTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.emp = User.objects.create_user("emp", password="pass12345!")
        self.emp.groups.add(Group.objects.create(name=EMPLOYEE_GROUP))
        self.adm = User.objects.create_user("adm", password="pass12345!")
        self.adm.groups.add(Group.objects.create(name=ADMIN_GROUP))
        self.nobody = User.objects.create_user("nobody", password="pass12345!")

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("backoffice:dashboard"))
        self.assertRedirects(r, reverse("backoffice:login") + "?next=" + reverse("backoffice:dashboard"))

    def test_user_without_role_cannot_log_in(self):
        self.client.post(reverse("backoffice:login"), {"username": "nobody", "password": "pass12345!"})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_employee_permissions(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(reverse("backoffice:orders")).status_code, 200)
        self.assertEqual(self.client.get(reverse("backoffice:stock")).status_code, 200)
        self.assertEqual(self.client.get(reverse("backoffice:products")).status_code, 403)
        self.assertEqual(self.client.get(reverse("backoffice:users")).status_code, 403)
        self.assertEqual(self.client.get(reverse("backoffice:reports")).status_code, 403)

    def test_admin_permissions(self):
        self.client.force_login(self.adm)
        for name in ("dashboard", "products", "users", "reports", "stock", "orders"):
            self.assertEqual(self.client.get(reverse(f"backoffice:{name}")).status_code, 200, name)

    def test_logout_invalidates_session(self):
        self.client.force_login(self.adm)
        self.client.post(reverse("backoffice:logout"))
        self.assertEqual(self.client.get(reverse("backoffice:dashboard")).status_code, 302)

    def test_employee_stock_movement_records_author(self):
        self.client.force_login(self.emp)
        self.client.post(reverse("backoffice:stock"), {"product": self.p4.pk, "kind": "in", "quantity": 4, "reason": "livraison"})
        mv = StockMovement.objects.first()
        self.assertEqual(mv.author, self.emp)
        self.assertEqual(mv.stock_after, 5)


class CustomerAccountTests(BaseTest):
    def signup(self, email="client@ps.cd"):
        return self.client.post(reverse("store:signup"), {
            "first_name": "Ana", "last_name": "Kasongo", "email": email,
            "password1": "Manette-2026!", "password2": "Manette-2026!"})

    def test_signup_logs_in_and_rejects_duplicate_email(self):
        r = self.signup()
        self.assertRedirects(r, reverse("store:account"))
        self.assertTrue(User.objects.filter(username="client@ps.cd").exists())
        self.client.post(reverse("store:logout"))
        r = self.signup("CLIENT@ps.cd")
        self.assertContains(r, "Un compte existe déjà")

    def test_signup_password_mismatch(self):
        r = self.client.post(reverse("store:signup"), {
            "first_name": "A", "last_name": "B", "email": "x@ps.cd",
            "password1": "Manette-2026!", "password2": "Autre-2026!"})
        self.assertContains(r, "ne correspondent pas")
        self.assertFalse(User.objects.filter(email="x@ps.cd").exists())

    def test_login_with_email_and_logout(self):
        User.objects.create_user("client@ps.cd", "client@ps.cd", "Manette-2026!")
        r = self.client.post(reverse("store:login"), {"username": "Client@PS.cd", "password": "Manette-2026!"})
        self.assertRedirects(r, reverse("store:account"))
        self.client.post(reverse("store:logout"))
        self.assertRedirects(self.client.get(reverse("store:account")),
                             reverse("store:login") + "?next=" + reverse("store:account"))

    def test_order_linked_to_account_and_private(self):
        self.signup()
        self.client.post(reverse("store:cart_add", args=[self.p5.pk]), {"quantity": 1})
        self.checkout(email="client@ps.cd")
        order = Order.objects.get()
        self.assertEqual(order.user.username, "client@ps.cd")
        self.assertContains(self.client.get(reverse("store:account")), order.reference)
        self.client.post(reverse("store:logout"))
        other = User.objects.create_user("autre@ps.cd", "autre@ps.cd", "Manette-2026!")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("store:account_order", args=[order.reference])).status_code, 404)

    def test_guest_checkout_still_works(self):
        self.client.post(reverse("store:cart_add", args=[self.p5.pk]), {"quantity": 1})
        self.checkout()
        self.assertIsNone(Order.objects.get().user)
