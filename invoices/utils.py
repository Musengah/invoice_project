from django.db import transaction
from django.db.models import F

from .models import BusinessProfile


def allocate_invoice_number(business):
    """Atomically take the next invoice number and advance the counter."""
    with transaction.atomic():
        business.refresh_from_db(fields=["invoice_prefix", "next_number"])
        number = f"{business.invoice_prefix}{business.next_number:04d}"
        BusinessProfile.objects.filter(pk=business.pk).update(
            next_number=F("next_number") + 1
        )
    return number