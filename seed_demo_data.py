"""
Seed script – populates the database with realistic demo data for Home Care Furniture.
Run via:  echo "exec(open('seed_demo_data.py').read())" | python manage.py shell
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.contrib.auth.models import User

from hr.models import Department, Employee, TimeEntry
from inventory.models import MaterialCategory, RawMaterial, ProductCategory, FinishedGood, BillOfMaterials
from pos.models import Customer, Sale, SaleLineItem
from financials.models import Expense

now = timezone.now()
today = timezone.localdate()

# ── Guard: skip if data already seeded ──
if FinishedGood.objects.exists():
    print("Demo data already exists — skipping seed.")
else:
    print("Seeding demo data …")

    # ═══════════════════════════════════════════
    # 1. Departments
    # ═══════════════════════════════════════════
    dept_production = Department.objects.create(name='Production', description='Manufacturing & assembly')
    dept_sales = Department.objects.create(name='Sales', description='Sales floor & customer service')
    dept_warehouse = Department.objects.create(name='Warehouse', description='Inventory & logistics')
    dept_admin = Department.objects.create(name='Administration', description='Office & management')

    # ═══════════════════════════════════════════
    # 2. Employees (create Django users + employee profiles)
    # ═══════════════════════════════════════════
    employee_data = [
        ('ram', 'Ram', 'Shrestha', dept_production, 'manager', 350),
        ('sita', 'Sita', 'Maharjan', dept_sales, 'employee', 280),
        ('hari', 'Hari', 'Tamang', dept_production, 'employee', 300),
        ('gita', 'Gita', 'Gurung', dept_warehouse, 'employee', 260),
        ('bikash', 'Bikash', 'Thapa', dept_production, 'employee', 320),
        ('anita', 'Anita', 'Karki', dept_admin, 'manager', 400),
        ('sunil', 'Sunil', 'Rai', dept_sales, 'employee', 275),
        ('maya', 'Maya', 'Lama', dept_warehouse, 'employee', 250),
    ]

    employees = []
    for username, first, last, dept, role, rate in employee_data:
        user = User.objects.create_user(username=username, first_name=first, last_name=last, password='demo1234')
        emp = Employee.objects.create(
            user=user, department=dept, role=role,
            hourly_rate=Decimal(str(rate)),
            hire_date=today - timedelta(days=random.randint(90, 730)),
            phone=f'98{random.randint(10000000, 99999999)}',
        )
        employees.append(emp)

    # ═══════════════════════════════════════════
    # 3. Time entries (last 7 days of shifts)
    # ═══════════════════════════════════════════
    for day_offset in range(7, 0, -1):
        day = today - timedelta(days=day_offset)
        for emp in random.sample(employees, k=min(6, len(employees))):
            clock_in = timezone.make_aware(
                timezone.datetime(day.year, day.month, day.day, random.randint(7, 9), random.randint(0, 59))
            )
            clock_out = clock_in + timedelta(hours=random.uniform(6, 9))
            meal_start = clock_in + timedelta(hours=random.uniform(3, 4))
            meal_end = meal_start + timedelta(minutes=random.randint(25, 45))
            TimeEntry.objects.create(
                employee=emp, clock_in=clock_in, clock_out=clock_out,
                meal_start=meal_start, meal_end=meal_end,
            )

    # ═══════════════════════════════════════════
    # 4. Material categories & raw materials
    # ═══════════════════════════════════════════
    cat_wood = MaterialCategory.objects.create(name='Wood', description='Timber and lumber')
    cat_hardware = MaterialCategory.objects.create(name='Hardware', description='Screws, nails, hinges')
    cat_fabric = MaterialCategory.objects.create(name='Fabric & Foam', description='Upholstery materials')
    cat_finishing = MaterialCategory.objects.create(name='Finishing', description='Paint, varnish, stain')

    raw_materials_data = [
        ('Sal Wood Planks', cat_wood, 'RM-SAL-001', 'ft', 450, 180, 100),
        ('Sisau Wood Planks', cat_wood, 'RM-SIS-001', 'ft', 280, 350, 80),
        ('Plywood Sheets 4x8', cat_wood, 'RM-PLY-001', 'pcs', 120, 1800, 30),
        ('MDF Board 4x8', cat_wood, 'RM-MDF-001', 'pcs', 85, 1200, 25),
        ('Wood Screws (box)', cat_hardware, 'RM-SCR-001', 'box', 200, 450, 50),
        ('Cabinet Hinges', cat_hardware, 'RM-HNG-001', 'pcs', 500, 85, 100),
        ('Drawer Slides (pair)', cat_hardware, 'RM-SLD-001', 'pcs', 180, 320, 40),
        ('Door Handles', cat_hardware, 'RM-HDL-001', 'pcs', 150, 250, 30),
        ('Foam Cushion Sheet', cat_fabric, 'RM-FOA-001', 'pcs', 60, 1500, 15),
        ('Upholstery Fabric', cat_fabric, 'RM-FAB-001', 'm', 95, 650, 20),
        ('Polyurethane Varnish', cat_finishing, 'RM-VAR-001', 'liter', 40, 750, 10),
        ('Wood Stain (Walnut)', cat_finishing, 'RM-STN-001', 'liter', 25, 850, 8),
        ('Sandpaper Assorted Pack', cat_finishing, 'RM-SND-001', 'box', 75, 350, 20),
        ('Wood Glue', cat_finishing, 'RM-GLU-001', 'liter', 35, 420, 10),
    ]

    raw_mats = {}
    for name, cat, sku, unit, qty, cost, reorder in raw_materials_data:
        rm = RawMaterial.objects.create(
            name=name, category=cat, sku=sku, unit=unit,
            quantity_on_hand=qty, cost_per_unit=Decimal(str(cost)),
            reorder_level=reorder, supplier_name='Nepal Timber & Hardware Suppliers',
            last_restocked=today - timedelta(days=random.randint(3, 30)),
        )
        raw_mats[sku] = rm

    # ═══════════════════════════════════════════
    # 5. Product categories & finished goods
    # ═══════════════════════════════════════════
    pc_dining = ProductCategory.objects.create(name='Dining', description='Dining tables & chairs')
    pc_bedroom = ProductCategory.objects.create(name='Bedroom', description='Beds, wardrobes, dressers')
    pc_living = ProductCategory.objects.create(name='Living Room', description='Sofas, coffee tables, shelves')
    pc_office = ProductCategory.objects.create(name='Office', description='Desks, bookshelves, cabinets')
    pc_kitchen = ProductCategory.objects.create(name='Kitchen', description='Kitchen cabinets & storage')

    products_data = [
        ('6-Seater Dining Table', pc_dining, 'FG-DT6-001', 45000, 28000, 8),
        ('Dining Chair (Set of 2)', pc_dining, 'FG-DC2-001', 12000, 6500, 20),
        ('Queen Size Bed Frame', pc_bedroom, 'FG-QBD-001', 55000, 32000, 5),
        ('3-Door Wardrobe', pc_bedroom, 'FG-WD3-001', 48000, 27000, 4),
        ('Bedside Table', pc_bedroom, 'FG-BST-001', 8500, 4200, 12),
        ('Dressing Table with Mirror', pc_bedroom, 'FG-DRS-001', 22000, 12000, 6),
        ('3-Seater Sofa', pc_living, 'FG-SF3-001', 65000, 38000, 3),
        ('Coffee Table', pc_living, 'FG-CFT-001', 15000, 7500, 10),
        ('TV Stand', pc_living, 'FG-TVS-001', 18000, 9000, 7),
        ('Bookshelf (5-Tier)', pc_living, 'FG-BSH-001', 14000, 7000, 9),
        ('Executive Office Desk', pc_office, 'FG-EOD-001', 35000, 19000, 6),
        ('Office Chair', pc_office, 'FG-OFC-001', 16000, 8500, 15),
        ('Filing Cabinet', pc_office, 'FG-FLC-001', 12500, 6000, 8),
        ('Kitchen Cabinet Set', pc_kitchen, 'FG-KCS-001', 85000, 48000, 2),
        ('Kitchen Island', pc_kitchen, 'FG-KIS-001', 42000, 24000, 3),
    ]

    finished_goods = []
    for name, cat, sku, price, bom_cost, qty in products_data:
        fg = FinishedGood.objects.create(
            name=name, category=cat, sku=sku,
            selling_price=Decimal(str(price)),
            calculated_bom_cost=Decimal(str(bom_cost)),
            quantity_on_hand=qty, is_active=True,
        )
        finished_goods.append(fg)

    # ═══════════════════════════════════════════
    # 6. Customers
    # ═══════════════════════════════════════════
    customers_data = [
        ('Rajesh', 'Hamal', 'rajesh@example.com', '9841234567'),
        ('Sunita', 'Basnet', 'sunita@example.com', '9851234567'),
        ('Deepak', 'Pokharel', 'deepak@example.com', '9861234567'),
        ('Kamala', 'Adhikari', 'kamala@example.com', '9871234567'),
        ('Binod', 'Pandey', 'binod@example.com', '9801234567'),
        ('Pramila', 'Koirala', 'pramila@example.com', '9811234567'),
        ('Arun', 'Joshi', 'arun@example.com', '9821234567'),
        ('Nirmala', 'Bhandari', 'nirmala@example.com', '9831234567'),
        ('Santosh', 'Rijal', 'santosh@example.com', '9841111111'),
        ('Laxmi', 'Sapkota', 'laxmi@example.com', '9852222222'),
    ]

    customers = []
    for first, last, email, phone in customers_data:
        c = Customer.objects.create(first_name=first, last_name=last, email=email, phone=phone)
        customers.append(c)

    # ═══════════════════════════════════════════
    # 7. Sales (last 30 days — ~40 sales)
    # ═══════════════════════════════════════════
    tax_rate = Decimal('0.08')
    sales_employees = [e for e in employees if e.department == dept_sales] or employees[:2]

    for i in range(40):
        day_offset = random.randint(0, 30)
        sale_date = now - timedelta(days=day_offset, hours=random.randint(0, 8))
        customer = random.choice(customers) if random.random() > 0.3 else None
        served_by = random.choice(sales_employees)
        payment = random.choice(['cash', 'cash', 'cash', 'card', 'bank_transfer'])

        sale = Sale(
            customer=customer, served_by=served_by,
            payment_method=payment, tax_rate=tax_rate,
            status=Sale.STATUS_COMPLETED,
        )
        sale.save()
        # Override sale_date
        Sale.objects.filter(pk=sale.pk).update(sale_date=sale_date)

        # Add 1-3 line items
        num_items = random.randint(1, 3)
        chosen_products = random.sample(finished_goods, k=min(num_items, len(finished_goods)))
        subtotal = Decimal('0')
        for fg in chosen_products:
            qty = random.randint(1, 3)
            line = SaleLineItem.objects.create(
                sale=sale, finished_good=fg,
                quantity=qty, unit_price=fg.selling_price,
            )
            subtotal += line.line_total

        tax_amount = round(float(subtotal) * float(tax_rate), 2)
        total = round(float(subtotal) + tax_amount, 2)
        Sale.objects.filter(pk=sale.pk).update(
            subtotal=subtotal, tax_amount=tax_amount, total_amount=total,
        )

    # ═══════════════════════════════════════════
    # 8. Expenses (last 60 days)
    # ═══════════════════════════════════════════
    expense_items = [
        ('Monthly rent – Lokanthali factory', 'rent', 75000),
        ('Electricity bill', 'utilities', 12500),
        ('Water bill', 'utilities', 3500),
        ('Internet & phone', 'utilities', 4800),
        ('Workshop equipment maintenance', 'maintenance', 8500),
        ('Marketing – social media ads', 'marketing', 15000),
        ('Office supplies – paper, ink', 'office_supplies', 2800),
        ('New drill machine', 'equipment', 35000),
        ('Delivery van fuel', 'other', 9500),
        ('Staff lunch/tea', 'other', 6200),
        ('Monthly rent – Lokanthali factory', 'rent', 75000),
        ('Electricity bill', 'utilities', 14200),
        ('Showroom cleaning service', 'maintenance', 5000),
        ('Google Ads campaign', 'marketing', 12000),
        ('Fire extinguisher refill', 'maintenance', 3200),
    ]

    for desc, cat, amount in expense_items:
        Expense.objects.create(
            description=desc, category=cat,
            amount=Decimal(str(amount)),
            expense_date=today - timedelta(days=random.randint(0, 55)),
            recorded_by=random.choice(employees),
        )

    print(f"✅ Demo data seeded successfully!")
    print(f"   • {len(employees)} employees")
    print(f"   • {len(raw_materials_data)} raw materials")
    print(f"   • {len(finished_goods)} products")
    print(f"   • {len(customers)} customers")
    print(f"   • 40 sales")
    print(f"   • {len(expense_items)} expenses")
