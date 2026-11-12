from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from backoffice.permissions import ADMIN_GROUP, EMPLOYEE_GROUP
from store.models import Category, Product, StockMovement

CATEGORIES = [("Jeux", "jeux"), ("Consoles", "consoles"), ("Accessoires", "accessoires"), ("Informatique", "informatique")]

# Données de démonstration UNIQUEMENT : les prix/quantités réels doivent venir de l'inventaire validé.
DEMO = [
    ("jeux", "[DÉMO] Jeu d'action PS5", "PS5", "59.99", 5),
    ("jeux", "[DÉMO] Jeu de course PS4", "PS4", "29.99", 3),
    ("jeux", "[DÉMO] Jeu de sport Xbox", "XBOX", "49.99", 0),
    ("consoles", "[DÉMO] Console PlayStation 5 – édition spéciale", "PS5", "549.00", 2),
    ("accessoires", "[DÉMO] Manette sans fil", "PS5", "69.90", 8),
    ("accessoires", "[DÉMO] Casque gaming", "", "79.00", 4),
    ("accessoires", "[DÉMO] Station de recharge manettes", "PS5", "29.00", 1),
    ("accessoires", "[DÉMO] Casque VR", "PS5", "399.00", 1),
]


class Command(BaseCommand):
    help = "Crée les rôles et catégories PS STORE (option --demo pour des produits fictifs)."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Ajoute des produits de démonstration.")

    def handle(self, *args, demo=False, **opts):
        for name in (ADMIN_GROUP, EMPLOYEE_GROUP):
            Group.objects.get_or_create(name=name)
        for i, (name, slug) in enumerate(CATEGORIES):
            Category.objects.update_or_create(slug=slug, defaults={"name": name, "position": i})
        self.stdout.write(self.style.SUCCESS("Rôles et catégories prêts."))

        if demo:
            for cat, name, platform, price, qty in DEMO:
                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={"category": Category.objects.get(slug=cat), "platform": platform,
                              "price": Decimal(price), "is_published": True,
                              "description": "Produit fictif de démonstration – à remplacer par l'inventaire validé."},
                )
                if created and qty:
                    StockMovement.record(product, StockMovement.IN, qty, "Stock initial (démo)")
            self.stdout.write(self.style.WARNING("Produits de démonstration ajoutés (préfixe [DÉMO])."))
