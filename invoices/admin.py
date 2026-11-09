from django.contrib import admin

from .models import BusinessProfile, Client, Invoice, InvoiceItem, Payment


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "number", "business", "client", "issue_date", "due_date", "status", "vat_enabled",
    )
    list_filter = ("status", "business")
    search_fields = ("number", "client__name")
    inlines = [InvoiceItemInline, PaymentInline]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "email", "phone")
    list_filter = ("business",)
    search_fields = ("name", "email")


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "currency", "vat_rate", "invoice_prefix", "next_number")
    search_fields = ("name", "user__username")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "date", "method")
    list_filter = ("method",)