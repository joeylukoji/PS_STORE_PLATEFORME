import json

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User

from store.models import Product, ProductImage, StockMovement

from .permissions import ADMIN_GROUP, EMPLOYEE_GROUP


class LoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        from .permissions import is_employee
        if not is_employee(user):
            raise forms.ValidationError("Ce compte n'a pas accès à l'espace de gestion.", code="no_role")


class ProductForm(forms.ModelForm):
    attributes_text = forms.CharField(
        label="Caractéristiques", required=False, widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Une caractéristique par ligne, au format « Clé : valeur » (ex. Processeur : Intel Core i5 7e gén.).",
    )

    class Meta:
        model = Product
        fields = ["name", "sku", "category", "platform", "condition", "price", "alert_threshold",
                  "warranty", "description", "is_published"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.attributes:
            self.fields["attributes_text"].initial = "\n".join(f"{k} : {v}" for k, v in self.instance.attributes.items())

    def clean_attributes_text(self):
        attrs = {}
        for n, line in enumerate(self.cleaned_data["attributes_text"].splitlines(), 1):
            if not line.strip():
                continue
            if ":" not in line:
                raise forms.ValidationError(f"Ligne {n} : utilisez le format « Clé : valeur ».")
            key, value = line.split(":", 1)
            attrs[key.strip()] = value.strip()
        return attrs

    def save(self, commit=True):
        self.instance.attributes = self.cleaned_data["attributes_text"]
        return super().save(commit)


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt"]


class StockMovementForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all(), label="Produit")
    kind = forms.ChoiceField(choices=StockMovement.KIND_CHOICES, label="Type")
    quantity = forms.IntegerField(min_value=1, label="Quantité")
    reason = forms.CharField(max_length=160, label="Motif")


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, min_length=8)
    role = forms.ChoiceField(choices=[(EMPLOYEE_GROUP, "Employé"), (ADMIN_GROUP, "Administrateur")], label="Rôle")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.save()
        user.groups.set([Group.objects.get_or_create(name=self.cleaned_data["role"])[0]])
        return user


class RoleForm(forms.Form):
    role = forms.ChoiceField(choices=[(EMPLOYEE_GROUP, "Employé"), (ADMIN_GROUP, "Administrateur"), ("", "Aucun (accès retiré)")],
                             required=False, label="Rôle")
    is_active = forms.BooleanField(required=False, label="Compte actif")


class PeriodForm(forms.Form):
    start = forms.DateField(label="Du", widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(label="Au", widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["start"] > data["end"]:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")
        return data
