from django.db import models


class Expense(models.Model):
    """
    General operating expenses not captured by raw-material purchases or labor.
    Examples: rent, utilities, equipment, marketing.
    """
    CATEGORY_RENT = 'rent'
    CATEGORY_UTILITIES = 'utilities'
    CATEGORY_EQUIPMENT = 'equipment'
    CATEGORY_SUPPLIES = 'office_supplies'
    CATEGORY_MARKETING = 'marketing'
    CATEGORY_MAINTENANCE = 'maintenance'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_RENT, 'Rent / Lease'),
        (CATEGORY_UTILITIES, 'Utilities'),
        (CATEGORY_EQUIPMENT, 'Equipment'),
        (CATEGORY_SUPPLIES, 'Office Supplies'),
        (CATEGORY_MARKETING, 'Marketing & Advertising'),
        (CATEGORY_MAINTENANCE, 'Maintenance & Repairs'),
        (CATEGORY_OTHER, 'Other'),
    ]

    description = models.CharField(max_length=300)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    recorded_by = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recorded_expenses'
    )
    receipt_file = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()} — ${self.amount} on {self.expense_date}"

    class Meta:
        ordering = ['-expense_date']


class ProfitLossSnapshot(models.Model):
    """
    Cached daily/monthly P&L snapshot for fast dashboard reads.
    Populated by a management command or scheduled task; not written directly by users.
    """
    PERIOD_DAILY = 'daily'
    PERIOD_MONTHLY = 'monthly'
    PERIOD_CHOICES = [
        (PERIOD_DAILY, 'Daily'),
        (PERIOD_MONTHLY, 'Monthly'),
    ]

    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()

    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_material_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_labor_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_operating_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    units_sold = models.PositiveIntegerField(default=0)

    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_period_type_display()} P&L: {self.period_start} → {self.period_end}"

    class Meta:
        ordering = ['-period_start']
        unique_together = ('period_type', 'period_start')
