from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from inventory.models import FinishedGood


class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']


class Sale(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_REFUNDED = 'refunded'
    STATUS_VOID = 'void'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_REFUNDED, 'Refunded'),
        (STATUS_VOID, 'Void'),
    ]

    PAYMENT_CASH = 'cash'
    PAYMENT_CARD = 'card'
    PAYMENT_CHECK = 'check'
    PAYMENT_TRANSFER = 'bank_transfer'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_CARD, 'Credit / Debit Card'),
        (PAYMENT_CHECK, 'Check'),
        (PAYMENT_TRANSFER, 'Bank Transfer'),
    ]

    # Walk-in customers are allowed (customer=None)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales'
    )
    served_by = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales'
    )
    sale_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0800,
                                   help_text='Stored as decimal, e.g. 0.08 = 8%')
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    notes = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=30, unique=True, blank=True)

    def __str__(self):
        customer_str = self.customer.full_name if self.customer else 'Walk-in'
        return f"Sale #{self.receipt_number or self.pk} — {customer_str} — ${self.total_amount}"

    def recalculate_totals(self):
        """Recompute subtotal, tax, and total from current line items."""
        subtotal = sum(item.line_total for item in self.line_items.all())
        tax_amount = round(float(subtotal) * float(self.tax_rate), 2)
        total = round(float(subtotal) + tax_amount - float(self.discount_amount), 2)
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total_amount = total
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])

    def complete_sale(self):
        """
        Finalize the sale: deduct all line items from finished-goods inventory
        atomically, then mark status as completed.
        """
        if self.status == self.STATUS_COMPLETED:
            raise ValidationError("This sale has already been completed.")
        if not self.line_items.exists():
            raise ValidationError("Cannot complete a sale with no line items.")

        with transaction.atomic():
            for item in self.line_items.select_related('finished_good').all():
                fg = FinishedGood.objects.select_for_update().get(pk=item.finished_good_id)
                if fg.quantity_on_hand < item.quantity:
                    raise ValidationError(
                        f"Insufficient stock: only {fg.quantity_on_hand} unit(s) of "
                        f"'{fg.name}' available, {item.quantity} requested."
                    )
                fg.quantity_on_hand -= item.quantity
                fg.save(update_fields=['quantity_on_hand'])

            self.recalculate_totals()
            self.status = self.STATUS_COMPLETED
            self.save(update_fields=['status'])

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            import uuid
            self.receipt_number = f"RCP-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-sale_date']


class SaleLineItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='line_items')
    finished_good = models.ForeignKey(
        FinishedGood, on_delete=models.PROTECT, related_name='sale_line_items'
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Price locked at time of sale — never reflects later price changes
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.finished_good.name} @ ${self.unit_price}"

    def save(self, *args, **kwargs):
        # Auto-populate unit_price from finished good if not set
        if not self.unit_price:
            self.unit_price = self.finished_good.selling_price
        self.line_total = round(float(self.unit_price) * self.quantity, 2)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['pk']
