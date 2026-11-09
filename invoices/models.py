from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

ZERO = Decimal("0.00")


def format_money(amount, currency):
    """Return 'ZMW 1,250.00' style output, tolerating None."""
    try:
        return f"{currency} {Decimal(amount):,.2f}"
    except Exception:
        return f"{currency} 0.00"


class BusinessProfile(models.Model):
    """The seller: branding, currency, VAT and invoice numbering."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business"
    )
    name = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    currency = models.CharField(max_length=8, default="ZMW")
    vat_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("16.00")
    )
    invoice_prefix = models.CharField(max_length=12, default="INV-")
    next_number = models.PositiveIntegerField(default=1)
    payment_details = models.TextField(blank=True)
    footer_note = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name or f"Business #{self.pk}"


class Client(models.Model):
    business = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="clients"
    )
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        unique_together = ("business", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"

    business = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="invoices"
    )
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="invoices"
    )
    number = models.CharField(max_length=30)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    vat_enabled = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "number")
        ordering = ["-issue_date", "-pk"]

    def __str__(self):
        return self.number

    # --- computed amounts ------------------------------------------------
    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), ZERO)

    @property
    def vat_amount(self):
        if not self.vat_enabled:
            return ZERO
        rate = self.business.vat_rate or ZERO
        return (self.subtotal * rate / Decimal("100")).quantize(ZERO)

    @property
    def total(self):
        return (self.subtotal + self.vat_amount).quantize(ZERO)

    @property
    def amount_paid(self):
        return sum((payment.amount for payment in self.payments.all()), ZERO)

    @property
    def balance(self):
        return (self.total - self.amount_paid).quantize(ZERO)

    @property
    def is_overdue(self):
        return (
            self.status == self.Status.SENT
            and self.balance > ZERO
            and self.due_date < timezone.localdate()
        )

    # --- display helpers --------------------------------------------------
    @property
    def currency(self):
        return self.business.currency

    @property
    def subtotal_display(self):
        return format_money(self.subtotal, self.currency)

    @property
    def vat_display(self):
        return format_money(self.vat_amount, self.currency)

    @property
    def total_display(self):
        return format_money(self.total, self.currency)

    @property
    def amount_paid_display(self):
        return format_money(self.amount_paid, self.currency)

    @property
    def balance_display(self):
        return format_money(self.balance, self.currency)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="items"
    )
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)

    def __str__(self):
        return self.description

    @property
    def line_total(self):
        return (self.quantity * self.unit_price).quantize(ZERO)

    @property
    def line_total_display(self):
        return format_money(self.line_total, self.invoice.currency)


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank transfer"
        MOBILE = "mobile", "Mobile money"
        CARD = "card", "Card"
        OTHER = "other", "Other"

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    reference = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"{self.invoice.number} payment"

    @property
    def amount_display(self):
        return format_money(self.amount, self.invoice.currency)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_business_profile(sender, instance, created, **kwargs):
    """Every new user automatically gets a business profile."""
    if created:
        BusinessProfile.objects.create(user=instance, name=instance.username)
