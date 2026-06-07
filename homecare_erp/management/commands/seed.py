"""
Usage: python manage.py seed
Populates the database with realistic HomeCare Furniture demo data.
Safe to re-run — skips records that already exist.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import timedelta, date, datetime
import random
import decimal


class Command(BaseCommand):
    help = 'Seed the database with demo data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')
        self._departments()
        self._employees()
        self._material_categories()
        self._raw_materials()
        self._product_categories()
        self._finished_goods()
        self._bom()
        self._customers()
        self._expenses()
        self._time_entries()
        self._sales()
        self.stdout.write(self.style.SUCCESS('Done! All demo data loaded.'))

    # ------------------------------------------------------------------ #
    def _departments(self):
        from hr.models import Department
        for name, desc in [
            ('Sales', 'Customer-facing sales team'),
            ('Production', 'Manufacturing and assembly floor'),
            ('Warehouse', 'Receiving, storage and shipping'),
            ('Administration', 'Finance, HR and management'),
        ]:
            Department.objects.get_or_create(name=name, defaults={'description': desc})
        self.stdout.write('  ✓ Departments')

    def _employees(self):
        from hr.models import Employee, Department
        data = [
            ('maria', 'Maria', 'Santos',    'Sales',          'manager',  28.00),
            ('james', 'James', 'Carter',    'Sales',          'employee', 18.50),
            ('linda', 'Linda', 'Nguyen',    'Production',     'manager',  26.00),
            ('carlos','Carlos','Ramirez',   'Production',     'employee', 16.75),
            ('priya', 'Priya', 'Patel',     'Warehouse',      'employee', 15.50),
            ('tom',   'Tom',   'Benson',    'Administration', 'admin',    35.00),
        ]
        for username, first, last, dept_name, role, rate in data:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first, 'last_name': last,
                          'email': f'{username}@homecarefurniture.com.np'}
            )
            user.set_password('demo1234')
            user.save()
            dept = Department.objects.get(name=dept_name)
            Employee.objects.get_or_create(
                user=user,
                defaults={
                    'department': dept,
                    'role': role,
                    'hourly_rate': decimal.Decimal(str(rate)),
                    'hire_date': date(2022, 1, 15),
                    'phone': f'555-{random.randint(1000,9999)}',
                }
            )
        self.stdout.write('  ✓ Employees (password: demo1234)')

    def _material_categories(self):
        from inventory.models import MaterialCategory
        for name, desc in [
            ('Wood & Lumber',  'Solid wood, plywood, MDF boards'),
            ('Hardware',       'Bolts, hinges, drawer slides, brackets'),
            ('Fabric & Foam',  'Upholstery fabric, cushion foam, batting'),
            ('Finishing',      'Paint, stain, varnish, lacquer'),
            ('Metal & Glass',  'Steel frames, glass panels, rods'),
        ]:
            MaterialCategory.objects.get_or_create(name=name, defaults={'description': desc})
        self.stdout.write('  ✓ Material Categories')

    def _raw_materials(self):
        from inventory.models import RawMaterial, MaterialCategory
        items = [
            ('Oak Plank 1"',       'Wood & Lumber',    'WD-001', 'sqft',  320,  4.50,  50),
            ('Birch Plywood 3/4"', 'Wood & Lumber',    'WD-002', 'sqft',  180,  3.20,  40),
            ('MDF Sheet',          'Wood & Lumber',    'WD-003', 'pcs',    60,  22.00, 10),
            ('Furniture Bolt M8',  'Hardware',       'HW-001', 'pcs',   800,   0.35, 200),
            ('Drawer Slide Pair',  'Hardware',       'HW-002', 'pcs',   120,   4.80,  30),
            ('Steel Leg Set',      'Hardware',       'HW-003', 'pcs',    45,  18.00,  10),
            ('High-Density Foam',  'Fabric & Foam',  'FB-001', 'kg',    90,  12.00,  20),
            ('Velvet Upholstery',  'Fabric & Foam',  'FB-002', 'm',     75,   8.50,  15),
            ('Cotton Fabric',      'Fabric & Foam',  'FB-003', 'm',     110,  6.00,  20),
            ('White Paint Gallon', 'Finishing',      'FN-001', 'gallon', 28,  38.00,   5),
            ('Clear Lacquer',      'Finishing',      'FN-002', 'liter', 40,  14.00,  10),
            ('Steel Frame Rod',    'Metal & Glass',  'MG-001', 'pcs',   60,  22.00,  15),
            ('Tempered Glass Panel','Metal & Glass', 'MG-002', 'pcs',   18,  65.00,   5),
            ('Aluminum Corner Bracket','Metal & Glass','MG-003','pcs',  80,   8.00,  20),
            ('Swivel Caster Set',  'Hardware',       'HW-004', 'pcs',   60,  22.00,  12),
        ]
        for name, cat_name, sku, unit, qty, cost, reorder in items:
            cat = MaterialCategory.objects.get(name=cat_name)
            RawMaterial.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name, 'category': cat, 'unit': unit,
                    'quantity_on_hand': decimal.Decimal(str(qty)),
                    'cost_per_unit': decimal.Decimal(str(cost)),
                    'reorder_level': decimal.Decimal(str(reorder)),
                    'supplier_name': 'Himalayan Timber & Supplies',
                    'supplier_contact': 'orders@himalayantimber.com.np',
                    'last_restocked': date.today() - timedelta(days=random.randint(5, 30)),
                }
            )
        self.stdout.write('  ✓ Raw Materials')

    def _product_categories(self):
        from inventory.models import ProductCategory
        for name, desc in [
            ('Bedroom',          'Beds, wardrobes, dressers, nightstands'),
            ('Living Room',      'Sofas, recliners, coffee tables, TV units'),
            ('Dining',           'Dining tables, chairs, buffets'),
            ('Office',           'Desks, office chairs, bookshelves, cabinets'),
        ]:
            ProductCategory.objects.get_or_create(name=name, defaults={'description': desc})
        self.stdout.write('  ✓ Product Categories')

    def _finished_goods(self):
        from inventory.models import FinishedGood, ProductCategory
        items = [
            ('King Size Bed Frame',         'Bedroom',     'BED-001', 15, 28500.00),
            ('Queen Size Bed Frame',        'Bedroom',     'BED-002', 22, 18500.00),
            ('Single Bed with Storage',     'Bedroom',     'BED-003', 30, 12500.00),
            ('4-Door Wardrobe',             'Bedroom',     'BED-004',  8, 32000.00),
            ('3-Seater Sofa',               'Living Room', 'SOF-001', 18, 45000.00),
            ('L-Shape Corner Sofa',         'Living Room', 'SOF-002', 10, 68000.00),
            ('Recliner Armchair',           'Living Room', 'SOF-003', 20, 22000.00),
            ('Coffee Table with Glass Top', 'Living Room', 'TBL-001', 25,  9500.00),
            ('6-Seater Dining Table Set',   'Dining',      'DIN-001', 12, 52000.00),
            ('4-Seater Dining Table Set',   'Dining',      'DIN-002', 18, 35000.00),
            ('Executive Office Desk',       'Office',      'OFF-001', 14, 24000.00),
            ('Bookshelf 5-Tier',            'Office',      'OFF-002', 28,  8500.00),
        ]
        for name, cat_name, sku, qty, price in items:
            cat = ProductCategory.objects.get(name=cat_name)
            FinishedGood.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name, 'category': cat,
                    'quantity_on_hand': qty,
                    'selling_price': decimal.Decimal(str(price)),
                    'calculated_bom_cost': decimal.Decimal(str(round(price * 0.42, 2))),
                    'is_active': True,
                }
            )
        self.stdout.write('  ✓ Finished Goods')

    def _bom(self):
        from inventory.models import BillOfMaterials, FinishedGood, RawMaterial
        bom_data = [
            ('BED-001', [('WD-001', 30), ('WD-002', 12), ('HW-001', 20),
                         ('HW-003', 4),  ('MG-001', 2),  ('FN-001', 0.5), ('FN-002', 1)]),
            ('BED-002', [('WD-001', 22), ('WD-002', 8),  ('HW-001', 16),
                         ('HW-003', 4),  ('FN-001', 0.4), ('FN-002', 0.8)]),
            ('BED-003', [('WD-001', 16), ('WD-002', 6),  ('HW-001', 12),
                         ('HW-002', 4),  ('FN-001', 0.3)]),
            ('BED-004', [('WD-001', 40), ('WD-002', 20), ('HW-001', 28),
                         ('FN-001', 0.6), ('FN-002', 1.5)]),
            ('SOF-001', [('WD-002', 10), ('FB-001', 8),  ('FB-002', 6),
                         ('HW-001', 16), ('MG-003', 4)]),
            ('SOF-002', [('WD-002', 16), ('FB-001', 12), ('FB-002', 10),
                         ('HW-001', 24), ('MG-003', 8)]),
            ('TBL-001', [('WD-001', 6),  ('MG-002', 1),  ('MG-001', 4), ('FN-002', 0.3)]),
            ('DIN-001', [('WD-001', 25), ('HW-001', 24), ('FN-001', 0.5), ('FN-002', 1)]),
            ('OFF-001', [('WD-001', 20), ('WD-002', 8),  ('HW-001', 16),
                         ('HW-002', 4),  ('FN-002', 0.6)]),
        ]
        for sku, materials in bom_data:
            try:
                fg = FinishedGood.objects.get(sku=sku)
                for mat_sku, qty in materials:
                    try:
                        mat = RawMaterial.objects.get(sku=mat_sku)
                        BillOfMaterials.objects.get_or_create(
                            finished_good=fg, raw_material=mat,
                            defaults={'quantity_required': decimal.Decimal(str(qty))}
                        )
                    except RawMaterial.DoesNotExist:
                        pass
            except FinishedGood.DoesNotExist:
                pass
        self.stdout.write('  ✓ Bill of Materials')

    def _customers(self):
        from pos.models import Customer
        customers = [
            ('Ramesh',  'Shrestha', 'ramesh@email.com',   '980-1234567', 'New home furnishing'),
            ('Sita',    'Karki',    'sita@email.com',     '984-2345678', 'Office renovation'),
            ('Bikash',  'Thapa',    'bikash@email.com',   '985-3456789', 'Bedroom set order'),
            ('Anita',   'Gurung',   '',                   '981-4567890', 'Living room furniture'),
            ('Suresh',  'Maharjan', 'suresh@email.com',   '986-5678901', 'Dining set'),
            ('Kathmandu Interiors', 'Showroom', 'orders@ktminteriors.com.np', '014-123456', 'Wholesale buyer'),
            ('Pokhara Furniture House', 'Dealer', 'procurement@pkrfurniture.com', '061-234567', 'Regular dealer'),
            ('Priya',   'Basnet',   'priya@email.com',    '982-6789012', ''),
            ('Mohan',   'Rai',      '',                   '983-7890123', 'Complete home setup'),
            ('Kabita',  'Tamang',   'kabita@email.com',   '987-8901234', 'Repeat customer'),
        ]
        for first, last, email, phone, notes in customers:
            Customer.objects.get_or_create(
                first_name=first, last_name=last,
                defaults={'email': email, 'phone': phone, 'notes': notes}
            )
        self.stdout.write('  ✓ Customers')

    def _expenses(self):
        from financials.models import Expense
        today = date.today()
        expenses = [
            ('Warehouse Rent – June',        'rent',          4200.00, today.replace(day=1)),
            ('Electricity Bill',             'utilities',      380.00, today.replace(day=3)),
            ('Internet & Phone',             'utilities',       95.00, today.replace(day=3)),
            ('Forklift Maintenance',         'maintenance',    650.00, today.replace(day=5)),
            ('Office Supplies',              'office_supplies', 87.50, today.replace(day=7)),
            ('Facebook Ads – May',           'marketing',      500.00, today - timedelta(days=35)),
            ('Google Ads – May',             'marketing',      300.00, today - timedelta(days=35)),
            ('Warehouse Rent – May',         'rent',          4200.00, today - timedelta(days=30)),
            ('Power Bill – May',             'utilities',      420.00, today - timedelta(days=28)),
            ('Trade Show Booth – May',       'marketing',      800.00, today - timedelta(days=20)),
            ('Band Saw Blade Replacement',   'equipment',      220.00, today - timedelta(days=15)),
            ('Cleaning Supplies',            'office_supplies', 45.00, today - timedelta(days=10)),
        ]
        for desc, cat, amt, dt in expenses:
            Expense.objects.get_or_create(
                description=desc,
                defaults={
                    'category': cat,
                    'amount': decimal.Decimal(str(amt)),
                    'expense_date': dt,
                }
            )
        self.stdout.write('  ✓ Expenses')

    def _time_entries(self):
        from hr.models import Employee, TimeEntry
        from django.utils import timezone as tz
        employees = list(Employee.objects.all())
        if not employees:
            return
        today = tz.localdate()
        for i, emp in enumerate(employees[:4]):
            # Past week completed shifts
            for day_offset in range(1, 6):
                d = today - timedelta(days=day_offset)
                clock_in = tz.make_aware(
                    datetime(d.year, d.month, d.day, 8, 0) + timedelta(minutes=random.randint(0, 15))
                )
                meal_start = clock_in + timedelta(hours=4)
                meal_end = meal_start + timedelta(minutes=30)
                clock_out = meal_end + timedelta(hours=3, minutes=random.randint(0, 45))
                TimeEntry.objects.get_or_create(
                    employee=emp,
                    clock_in__date=d,
                    defaults={
                        'clock_in': clock_in,
                        'meal_start': meal_start,
                        'meal_end': meal_end,
                        'clock_out': clock_out,
                    }
                )
            # Today: some clocked in, some not
            if i < 2:
                clock_in_today = tz.make_aware(
                    datetime(today.year, today.month, today.day, 8, 30)
                )
                if not TimeEntry.objects.filter(employee=emp, clock_in__date=today).exists():
                    TimeEntry.objects.create(employee=emp, clock_in=clock_in_today)
        self.stdout.write('  ✓ Time Entries')

    def _sales(self):
        from pos.models import Sale, SaleLineItem, Customer
        from inventory.models import FinishedGood
        from hr.models import Employee
        from django.utils import timezone as tz

        customers = list(Customer.objects.all())
        employees = list(Employee.objects.filter(role__in=['employee', 'manager']))
        products = list(FinishedGood.objects.filter(is_active=True, quantity_on_hand__gt=5))

        if not products or not customers:
            return

        today = tz.localdate()
        payment_choices = ['cash', 'card', 'card', 'card', 'check', 'bank_transfer']

        for day_offset in range(60, 0, -1):
            d = today - timedelta(days=day_offset)
            num_sales = random.randint(0, 3)
            for _ in range(num_sales):
                customer = random.choice(customers)
                emp = random.choice(employees) if employees else None
                sale_time = tz.make_aware(
                    datetime(d.year, d.month, d.day,
                                      random.randint(9, 17), random.randint(0, 59))
                )
                sale = Sale.objects.create(
                    customer=customer,
                    served_by=emp,
                    payment_method=random.choice(payment_choices),
                    tax_rate=decimal.Decimal('0.0800'),
                    status=Sale.STATUS_PENDING,
                )
                # Override auto_now_add date via queryset update
                Sale.objects.filter(pk=sale.pk).update(sale_date=sale_time)

                num_items = random.randint(1, 3)
                chosen = random.sample(products, min(num_items, len(products)))
                for fg in chosen:
                    qty = random.randint(1, 2)
                    SaleLineItem.objects.create(
                        sale=sale,
                        finished_good=fg,
                        quantity=qty,
                        unit_price=fg.selling_price,
                    )

                sale.recalculate_totals()
                sale.status = Sale.STATUS_COMPLETED
                sale.save(update_fields=['status'])

        # A few sales today
        for _ in range(random.randint(2, 4)):
            customer = random.choice(customers)
            emp = random.choice(employees) if employees else None
            sale = Sale.objects.create(
                customer=customer,
                served_by=emp,
                payment_method=random.choice(payment_choices),
                tax_rate=decimal.Decimal('0.0800'),
            )
            fg = random.choice(products)
            SaleLineItem.objects.create(
                sale=sale, finished_good=fg,
                quantity=1, unit_price=fg.selling_price,
            )
            sale.recalculate_totals()
            sale.status = Sale.STATUS_COMPLETED
            sale.save(update_fields=['status'])

        self.stdout.write(f'  ✓ Sales ({Sale.objects.count()} total)')
