import re

from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["first_name", "last_name", "email", "phone", "delivery_mode", "address", "city", "notes"]
        widgets = {
            "delivery_mode": forms.RadioSelect,
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.fullmatch(r"\+?[\d\s.-]{8,20}", phone):
            raise forms.ValidationError("Numéro de téléphone invalide.")
        return phone

    def clean(self):
        data = super().clean()
        if data.get("delivery_mode") == "livraison":
            for field in ("address", "city"):
                if not data.get(field):
                    self.add_error(field, "Ce champ est obligatoire pour une livraison.")
        return data


class TrackingForm(forms.Form):
    reference = forms.CharField(label="Numéro de commande", max_length=20)
    email = forms.EmailField(label="E-mail utilisé pour la commande")

    def clean_reference(self):
        return self.cleaned_data["reference"].strip().upper()
