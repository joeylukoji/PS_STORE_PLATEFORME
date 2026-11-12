from django import template
from django.templatetags.static import static

register = template.Library()

KNOWN = {"jeux", "consoles", "accessoires", "informatique"}


@register.simple_tag
def category_photo(category, kind="cat"):
    """Photo d'illustration d'une catégorie (kind="cat") ou image par défaut d'un produit (kind="ph")."""
    slug = category.slug if category.slug in KNOWN else "consoles"
    return static(f"img/{kind}-{slug}.jpg")
