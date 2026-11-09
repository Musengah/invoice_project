from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from invoices.models import BusinessProfile, Client, Invoice, InvoiceItem, Payment
from invoices.utils import allocate_invoice_number


class Command(BaseCommand):
    help = "Create a demo user (demo / demo1234) with sample clients and invoices."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="demo", defaults={"email": "demo@example.com"}
        )
        if created:
            user.set_password("demo1234")
            user.save()

        profile, _ = BusinessProfile.objects.get_or_create(user=user)
        changed = False
        if not profile.name or profile.name == "demo":
            profile.name = "Nyondo Consulting"
            changed = True
        if not profile.address:
            profile.address = "12 Katondo Street\nLusaka, Zambia"
            changed = True
        if not profile.payment_details:
            profile.payment_details = (
                "Bank: ZANACO\nAccount: 0123456789\nName: Nyondo Consulting\n"
                "Mobile money: 097 000 0000"
            )
            changed = True
        if changed:
            profile.save()

        client_data = [
            ("Kwetu Designs", "info@kwetudesigns.com", "+260 97 000 0001", "Plot 45, Kafue Road\nLusaka"),
            ("Mango Lodge", "book@mangolodge.zm", "+260 97 000 0002", "Kabwe Road\nKabwe"),
            ("Bwalya Haulage", "accounts@bwalayahaulage.com", "+260 97 000 0003", "Industrial Area\nNdola"),
            ("Sunrise Farm", "", "+260 97 000 0004", "Chibombo"),
        ]
        clients = []
        for name, email, phone, address in client_data:
            client, _ = Client.objects.get_or_create(
                business=profile,
                name=name,
                defaults={"email": email, "phone": phone, "address": address},
            )
            clients.append(client)

        if Invoice.objects.filter(business=profile).exists():
            self.stdout.write(self.style.WARNING("Demo invoices already exist; skipping."))
            self.stdout.write(self.style.SUCCESS("Demo login: demo / demo1234"))
            return

        today = timezone.localdate()
        # (client, items, issue offset days ago, due offset from issue, status, vat, pay fraction)
        invoices_data = [
            (clients[0], [("Logo design", 1, "1500.00"), ("Business cards (pack of 100)", 1, "1200.00")], 35, 14, "sent", True, 1.0),
            (clients[1], [("Conference room hire (day rate)", 2, "800.00")], 20, 14, "sent", True, 0.0),
            (clients[2], [("Haulage: Lusaka to Ndola", 3, "4500.00")], 45, 30, "sent", True, 0.5),
            (clients[3], [("Maize seed, 50kg bags", 10, "950.00")], 5, 14, "sent", False, 0.0),
            (clients[0], [("Website maintenance retainer (monthly)", 1, "2000.00")], 2, 14, "draft", True, 0.0),
        ]
        for client, items, issued, due, status, vat, pay_frac in invoices_data:
            invoice = Invoice.objects.create(
                business=profile,
                client=client,
                number=allocate_invoice_number(profile),
                issue_date=today - timedelta(days=issued),
                due_date=today - timedelta(days=issued - due),
                status=status,
                vat_enabled=vat,
            )
            for description, qty, price in items:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=description,
                    quantity=Decimal(str(qty)),
                    unit_price=Decimal(price),
                )
            if pay_frac > 0:
                amount = (invoice.total * Decimal(str(pay_frac))).quantize(Decimal("0.01"))
                Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    method=Payment.Method.BANK,
                    date=invoice.issue_date + timedelta(days=3),
                    reference=f"DEMO-{invoice.number}",
                )
                if pay_frac == 1.0:
                    invoice.status = Invoice.Status.PAID
                    invoice.save(update_fields=["status", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(self.style.SUCCESS("Demo login: demo / demo1234"))