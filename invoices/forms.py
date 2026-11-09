from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from .models import BusinessProfile, Client, Invoice, InvoiceItem, Payment

DATE_WIDGET = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = [
            "name", "address", "email", "phone", "logo", "currency",
            "vat_rate", "invoice_prefix", "payment_details", "footer_note",
        ]
        widgets = {
            "vat_rate": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "email", "phone", "address"]


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["client", "issue_date", "due_date", "status", "vat_enabled", "notes"]
        widgets = {"issue_date": DATE_WIDGET, "due_date": DATE_WIDGET}

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        if business is not None:
            self.fields["client"].queryset = business.clients.all()


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "unit_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }


class BaseInvoiceItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        has_items = any(
            form.cleaned_data and not form.cleaned_data.get("DELETE")
            for form in self.forms
        )
        if not has_items:
            raise forms.ValidationError("Add at least one line item.")


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    formset=BaseInvoiceItemFormSet,
    extra=1,
    can_delete=True,
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "date", "method", "reference"]
        widgets = {
            "date": DATE_WIDGET,
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, initial_amount=None, **kwargs):
        super().__init__(*args, **kwargs)
        if initial_amount is not None:
            self.fields["amount"].initial = initial_amount
        self.fields["date"].initial = timezone.localdate()