from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction


class MaterialCategory(models.Model):
    """Top-level grouping for raw inputs: Wood, Hardware, Fabric, Finishing, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Material Categories'


class RawMaterial(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Pieces'),
        ('kg', 'Kilograms'),
        ('lbs', 'Pounds'),
        ('m', 'Meters'),
        ('ft', 'Feet'),
        ('sqft', 'Square Feet'),
        ('liter', 'Liters'),
        ('gallon', 'Gallons'),
        ('box', 'Box'),
        ('roll', 'Roll'),
    ]

    name = models.CharField(max_length=200)
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT, related_name='materials')
    sku = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pcs')
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0,
                                        help_text='Alert threshold for low stock')
    supplier_name = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=200, blank=True)
    last_restocked = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.reorder_level

    @property
    def total_value(self):
        return round(float(self.quantity_on_hand) * float(self.cost_per_unit), 2)

    class Meta:
        ordering = ['category', 'name']


class ProductCategory(models.Model):
    """Grouping for finished goods: Dining, Bedroom, Living Room, Office, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Product Categories'


class FinishedGood(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name='products')
    sku = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    quantity_on_hand = models.PositiveIntegerField(default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Snapshot of BOM cost at last calculation — updated by signals/production runs
    calculated_bom_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def profit_margin(self):
        if self.calculated_bom_cost and float(self.calculated_bom_cost) > 0:
            margin = (float(self.selling_price) - float(self.calculated_bom_cost)) / float(self.selling_price) * 100
            return round(margin, 2)
        return None

    def recalculate_bom_cost(self):
        """Recompute and save calculated_bom_cost from current BOM + raw material prices."""
        total = sum(
            float(item.quantity_required) * float(item.raw_material.cost_per_unit)
            for item in self.bom_items.select_related('raw_material').all()
        )
        self.calculated_bom_cost = round(total, 2)
        self.save(update_fields=['calculated_bom_cost'])
        return self.calculated_bom_cost

    class Meta:
        ordering = ['category', 'name']


class BillOfMaterials(models.Model):
    """
    Defines how much of each RawMaterial is consumed to produce ONE unit of a FinishedGood.
    When a ProductionRun is recorded, these quantities are multiplied by units produced
    and deducted from RawMaterial.quantity_on_hand.
    """
    finished_good = models.ForeignKey(FinishedGood, on_delete=models.CASCADE, related_name='bom_items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name='used_in_boms')
    quantity_required = models.DecimalField(max_digits=12, decimal_places=4,
                                            help_text='Units of raw material per one finished good')
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return (
            f"{self.finished_good.name} ← "
            f"{self.quantity_required} {self.raw_material.unit} of {self.raw_material.name}"
        )

    class Meta:
        unique_together = ('finished_good', 'raw_material')
        verbose_name = 'Bill of Materials Entry'
        verbose_name_plural = 'Bill of Materials'


class ProductionRun(models.Model):
    """
    Records a manufacturing batch. On save, deducts raw materials and increments
    finished goods inventory atomically inside a database transaction.
    """
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    finished_good = models.ForeignKey(FinishedGood, on_delete=models.PROTECT, related_name='production_runs')
    quantity_produced = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    produced_by = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='production_runs'
    )
    production_date = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Run #{self.pk} — {self.quantity_produced}x {self.finished_good.name} [{self.get_status_display()}]"

    def complete(self):
        """
        Atomically deduct raw materials per BOM and add finished goods to stock.
        Raises ValidationError if any raw material has insufficient stock.
        """
        from django.utils import timezone
        if self.status == self.STATUS_COMPLETED:
            raise ValidationError("This production run has already been completed.")

        bom_items = self.finished_good.bom_items.select_related('raw_material').all()

        with transaction.atomic():
            for item in bom_items:
                required = float(item.quantity_required) * self.quantity_produced
                material = RawMaterial.objects.select_for_update().get(pk=item.raw_material_id)
                if float(material.quantity_on_hand) < required:
                    raise ValidationError(
                        f"Insufficient stock: need {required} {material.unit} of "
                        f"'{material.name}', only {material.quantity_on_hand} available."
                    )
                material.quantity_on_hand = float(material.quantity_on_hand) - required
                material.save(update_fields=['quantity_on_hand'])

            fg = FinishedGood.objects.select_for_update().get(pk=self.finished_good_id)
            fg.quantity_on_hand += self.quantity_produced
            fg.save(update_fields=['quantity_on_hand'])

            self.status = self.STATUS_COMPLETED
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])

        self.finished_good.recalculate_bom_cost()

    class Meta:
        ordering = ['-production_date']
