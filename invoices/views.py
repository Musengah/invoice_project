from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

from .forms import (
    BusinessProfileForm,
    ClientForm,
    InvoiceForm,
    InvoiceItemFormSet,
    PaymentForm,
    SignUpForm,
)
from .models import Invoice, Payment, format_money
from .utils import allocate_invoice_number

ZERO = Decimal("0.00")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Start by completing your business settings.")
            return redirect("profile_edit")
    else:
        form = SignUpForm()
    return render(request, "invoices/signup.html", {"form": form})


@login_required
def dashboard(request):
    business = request.user.business
    invoices = list(business.invoices.select_related("client"))
    outstanding = sum(
        (i.balance for i in invoices if i.status == Invoice.Status.SENT), ZERO
    )
    overdue_count = sum(1 for i in invoices if i.is_overdue)
    today = timezone.localdate()
    month_start = today.replace(day=1)
    paid_this_month = (
        Payment.objects.filter(invoice__business=business, date__gte=month_start)
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    context = {
        "business": business,
        "outstanding_display": format_money(outstanding, business.currency),
        "overdue_count": overdue_count,
        "paid_this_month_display": format_money(paid_this_month, business.currency),
        "client_count": business.clients.count(),
        "recent_invoices": invoices[:5],
    }
    return render(request, "invoices/dashboard.html", context)


@login_required
def profile_edit(request):
    business = request.user.business
    if request.method == "POST":
        form = BusinessProfileForm(request.POST, request.FILES, instance=business)
        if form.is_valid():
            form.save()
            messages.success(request, "Business settings saved.")
            return redirect("dashboard")
    else:
        form = BusinessProfileForm(instance=business)
    return render(
        request,
        "invoices/form.html",
        {"form": form, "title": "Business settings", "submit_label": "Save settings"},
    )


@login_required
def client_list(request):
    clients = request.user.business.clients.all()
    return render(request, "invoices/client_list.html", {"clients": clients})


@login_required
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.business = request.user.business
            client.save()
            messages.success(request, f"Client {client.name} added.")
            return redirect("client_list")
    else:
        form = ClientForm()
    return render(
        request,
        "invoices/form.html",
        {"form": form, "title": "New client", "submit_label": "Add client"},
    )


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk, business=request.user.business)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client updated.")
            return redirect("client_list")
    else:
        form = ClientForm(instance=client)
    return render(
        request,
        "invoices/form.html",
        {"form": form, "title": f"Edit client: {client.name}", "submit_label": "Save"},
    )


@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk, business=request.user.business)
    if request.method == "POST":
        client.delete()
        messages.success(request, "Client deleted.")
        return redirect("client_list")
    return render(
        request,
        "invoices/confirm_delete.html",
        {"object": client, "title": "Delete client", "cancel_url_name": "client_list"},
    )


@login_required
def invoice_list(request):
    business = request.user.business
    invoices = business.invoices.select_related("client")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        invoices = invoices.filter(Q(number__icontains=q) | Q(client__name__icontains=q))
    if status in ("draft", "sent", "paid"):
        invoices = invoices.filter(status=status)
    elif status == "overdue":
        invoices = [i for i in invoices if i.is_overdue]
    return render(
        request,
        "invoices/invoice_list.html",
        {"invoices": invoices, "status": status, "q": q},
    )


@login_required
def invoice_create(request):
    business = request.user.business
    if request.method == "POST":
        form = InvoiceForm(request.POST, business=business)
        formset = InvoiceItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.business = business
            invoice.number = allocate_invoice_number(business)
            invoice.save()
            formset.instance = invoice
            formset.save()
            messages.success(request, f"Invoice {invoice.number} created.")
            return redirect("invoice_detail", pk=invoice.pk)
    else:
        today = timezone.localdate()
        form = InvoiceForm(
            business=business,
            initial={"issue_date": today, "due_date": today + timedelta(days=14)},
        )
        formset = InvoiceItemFormSet()
    return render(
        request,
        "invoices/invoice_form.html",
        {"form": form, "formset": formset, "title": "New invoice"},
    )


@login_required
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, business=request.user.business)
    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice, business=request.user.business)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f"Invoice {invoice.number} updated.")
            return redirect("invoice_detail", pk=invoice.pk)
    else:
        form = InvoiceForm(instance=invoice, business=request.user.business)
        formset = InvoiceItemFormSet(instance=invoice)
    return render(
        request,
        "invoices/invoice_form.html",
        {"form": form, "formset": formset, "title": f"Edit invoice {invoice.number}"},
    )


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("client", "business"),
        pk=pk,
        business=request.user.business,
    )
    return render(request, "invoices/invoice_detail.html", {"invoice": invoice})


@login_required
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, business=request.user.business)
    if request.method == "POST":
        invoice.delete()
        messages.success(request, "Invoice deleted.")
        return redirect("invoice_list")
    return render(
        request,
        "invoices/confirm_delete.html",
        {"object": invoice, "title": "Delete invoice", "cancel_url_name": "invoice_list"},
    )


@login_required
def invoice_mark_sent(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, business=request.user.business)
    if request.method == "POST" and invoice.status == Invoice.Status.DRAFT:
        invoice.status = Invoice.Status.SENT
        invoice.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Invoice {invoice.number} marked as sent.")
    return redirect("invoice_detail", pk=invoice.pk)


@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("client", "business"),
        pk=pk,
        business=request.user.business,
    )
    context = {"invoice": invoice}
    if invoice.business.logo:
        try:
            context["logo_path"] = invoice.business.logo.path
        except Exception:
            pass
    html = render_to_string("invoices/pdf/invoice_pdf.html", context)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{invoice.number}.pdf"'
    status = pisa.CreatePDF(html, dest=response, encoding="utf-8")
    if status.err:
        messages.error(request, "Could not generate the PDF.")
        return redirect("invoice_detail", pk=invoice.pk)
    return response


@login_required
def payment_add(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, business=request.user.business)
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()
            if (
                invoice.status == Invoice.Status.SENT
                and invoice.balance <= ZERO
            ):
                invoice.status = Invoice.Status.PAID
                invoice.save(update_fields=["status", "updated_at"])
                messages.success(request, "Invoice fully paid!")
            else:
                messages.success(request, "Payment recorded.")
            return redirect("invoice_detail", pk=invoice.pk)
    else:
        form = PaymentForm(
            initial_amount=invoice.balance if invoice.balance > ZERO else None
        )
    return render(
        request,
        "invoices/form.html",
        {"form": form, "title": f"Record payment: {invoice.number}", "submit_label": "Save payment"},
    )