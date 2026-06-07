"""
Local AI engine for Home Care Furniture Udhyog.
Analyses live DB data and returns natural-language business insights.
No external API required.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.utils import timezone


# ── helpers ────────────────────────────────────────────────────────────────────

def _fmt(amount) -> str:
    return f"रू {float(amount):,.2f}"


def _pct(part, whole) -> str:
    if not whole:
        return "0%"
    return f"{part / whole * 100:.1f}%"


def _today():
    return timezone.localdate()


def _month_start():
    d = _today()
    return d.replace(day=1)


# ── data loaders ───────────────────────────────────────────────────────────────

def _sales_this_month():
    from pos.models import Sale
    return Sale.objects.filter(
        sale_date__date__gte=_month_start(),
        status=Sale.STATUS_COMPLETED,
    )


def _sales_last_month():
    from pos.models import Sale
    today = _today()
    first_this = today.replace(day=1)
    first_last = (first_this - timedelta(days=1)).replace(day=1)
    return Sale.objects.filter(
        sale_date__date__gte=first_last,
        sale_date__date__lt=first_this,
        status=Sale.STATUS_COMPLETED,
    )


def _all_completed_sales():
    from pos.models import Sale
    return Sale.objects.filter(status=Sale.STATUS_COMPLETED)


# ── intent routing ─────────────────────────────────────────────────────────────

INTENT_PATTERNS = [
    # (regex pattern, handler_name)
    (r"restock|reorder|stock.up|order.next|which.product.*should|forecast", "restock_forecast"),
    (r"low.stock|running.out|alert|short.on", "low_stock"),
    (r"margin|profit.*product|best.*margin|most.*profit", "top_margin"),
    (r"best.sell|top.*sell|popular|most.*sold|highest.*revenue|top.*product", "top_selling"),
    (r"bedroom|living.room|dining|sofa|chair|table|customer.want|recommend|match|suggest", "product_match"),
    (r"summary|this.month|monthly|month.*perform|overview|how.*doing", "monthly_summary"),
    (r"revenue|income|earning|sales.*total|total.*sale", "revenue"),
    (r"employee|staff|worker|labor|hr|clock.in|clocked|work.hour|labor.cost", "labor"),
    (r"inventory|stock.*level|how.many.*unit|available.*unit", "inventory_status"),
    (r"expense|cost|overhead|operating", "expenses"),
    (r"customer|buyer|client|who.*buy|top.*customer", "top_customers"),
    (r"payment|cash|card|transfer|how.*pay", "payment_breakdown"),
    (r"hello|hi |hey |help|what.can|what.*do", "help"),
]


def classify(query: str) -> str:
    q = query.lower()
    for pattern, handler in INTENT_PATTERNS:
        if re.search(pattern, q):
            return handler
    return "general"


# ── handlers ───────────────────────────────────────────────────────────────────

def handle_help(query: str) -> str:
    return (
        "Hello! I'm your Home Care Furniture AI Business Assistant.\n\n"
        "I can help you with:\n"
        "• 📦 Restock forecast — which products to order next month\n"
        "• 🏆 Top-selling & highest-margin products\n"
        "• ⚠️  Low stock alerts\n"
        "• 💰 Monthly revenue & P&L summary\n"
        "• 👥 Employee labor hours & costs\n"
        "• 🛋️  Product recommendations for customers\n"
        "• 📊 Inventory status\n\n"
        "Try asking: 'Which products should I restock?' or 'Give me a monthly summary.'"
    )


def handle_monthly_summary(query: str) -> str:
    from financials.models import Expense
    sales = _sales_this_month()
    revenue = sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    count = sales.count()
    last_sales = _sales_last_month()
    last_rev = last_sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    expenses = Expense.objects.filter(
        expense_date__gte=_month_start()
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    net_profit = revenue - expenses

    margin = float(net_profit) / float(revenue) * 100 if revenue else 0

    mom_change = ""
    if last_rev:
        diff = float(revenue) - float(last_rev)
        sign = "+" if diff >= 0 else ""
        mom_change = f"\n📈 vs. last month: {sign}{_fmt(diff)} ({sign}{_pct(abs(diff), float(last_rev))})"

    from inventory.models import RawMaterial
    low_stock_count = sum(1 for m in RawMaterial.objects.all() if m.is_low_stock)

    from hr.models import Employee, TimeEntry
    emp_count = Employee.objects.filter(is_active=True).count()
    labor_cost = sum(
        e.labor_cost or 0
        for e in TimeEntry.objects.filter(
            clock_in__date__gte=_month_start(),
            clock_out__isnull=False,
        ).select_related('employee')
    )

    lines = [
        f"📊 Monthly Business Summary — {_today().strftime('%B %Y')}",
        "",
        f"💰 Revenue:          {_fmt(revenue)} ({count} completed sales){mom_change}",
        f"💸 Expenses:         {_fmt(expenses)}",
        f"👷 Labor Cost:       {_fmt(labor_cost)}",
        f"📈 Net Profit:       {_fmt(net_profit)} ({margin:.1f}% margin)",
        f"👥 Active Employees: {emp_count}",
        f"⚠️  Low Stock Items:  {low_stock_count}",
    ]

    if margin >= 90:
        lines.append("\n✅ Excellent month! Profit margin is above 90%.")
    elif margin >= 70:
        lines.append("\n✅ Good performance. Consider reviewing expenses to push margin higher.")
    elif margin > 0:
        lines.append("\n⚠️  Margin is below 70%. Review high-cost items or negotiate better supplier rates.")
    else:
        lines.append("\n🚨 Expenses exceed revenue this month. Immediate review recommended.")

    return "\n".join(lines)


def handle_revenue(query: str) -> str:
    sales = _sales_this_month()
    revenue = sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    count = sales.count()
    avg = float(revenue) / count if count else 0

    today_sales = sales.filter(sale_date__date=_today())
    today_rev = today_sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    last_rev = _sales_last_month().aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    trend = ""
    if last_rev:
        diff = float(revenue) - float(last_rev)
        sign = "+" if diff >= 0 else ""
        trend = f"\n📊 vs. Last Month: {sign}{_fmt(diff)}"

    return (
        f"💰 Revenue Report — {_today().strftime('%B %Y')}\n\n"
        f"Month-to-date:  {_fmt(revenue)}\n"
        f"Today:          {_fmt(today_rev)}\n"
        f"Completed Sales:{count}\n"
        f"Avg Sale Value: {_fmt(avg)}"
        f"{trend}"
    )


def handle_top_selling(query: str) -> str:
    from pos.models import SaleLineItem
    items = (
        SaleLineItem.objects.filter(sale__status='completed')
        .values('finished_good__name', 'finished_good__category__name')
        .annotate(units=Sum('quantity'), revenue=Sum('line_total'))
        .order_by('-revenue')[:8]
    )
    if not items:
        return "No completed sales data found yet."

    lines = ["🏆 Top Selling Products (All Time)\n"]
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. {item['finished_good__name']}\n"
            f"   Category: {item['finished_good__category__name']}\n"
            f"   Units Sold: {item['units']}  |  Revenue: {_fmt(item['revenue'])}"
        )
    return "\n".join(lines)


def handle_top_margin(query: str) -> str:
    from inventory.models import FinishedGood
    goods = FinishedGood.objects.filter(
        is_active=True,
        calculated_bom_cost__gt=0,
    ).order_by('-selling_price')

    results = []
    for g in goods:
        if g.profit_margin is not None:
            results.append((g.profit_margin, g))
    results.sort(reverse=True)

    if not results:
        return (
            "No BOM cost data found to calculate margins.\n"
            "Add Bill of Materials entries in Inventory to enable margin analysis."
        )

    lines = ["💎 Products by Profit Margin\n"]
    for i, (margin, g) in enumerate(results[:8], 1):
        lines.append(
            f"{i}. {g.name}\n"
            f"   Price: {_fmt(g.selling_price)}  |  Cost: {_fmt(g.calculated_bom_cost)}  |  Margin: {margin:.1f}%"
        )
    return "\n".join(lines)


def handle_low_stock(query: str) -> str:
    from inventory.models import RawMaterial
    low = [m for m in RawMaterial.objects.select_related('category').all() if m.is_low_stock]

    if not low:
        return "✅ All raw materials are above their reorder levels. Stock looks healthy!"

    lines = [f"⚠️  Low Stock Alert — {len(low)} material(s) need attention\n"]
    for m in low:
        lines.append(
            f"• {m.name} [{m.category.name}]\n"
            f"  On hand: {m.quantity_on_hand} {m.unit}  |  Reorder at: {m.reorder_level} {m.unit}\n"
            f"  Supplier: {m.supplier_name or 'Not set'}  |  Contact: {m.supplier_contact or 'Not set'}"
        )
    return "\n".join(lines)


def handle_restock_forecast(query: str) -> str:
    from pos.models import SaleLineItem
    from inventory.models import FinishedGood

    # Sales velocity over the last 30 days
    cutoff = _today() - timedelta(days=30)
    sold_30d = (
        SaleLineItem.objects.filter(
            sale__status='completed',
            sale__sale_date__date__gte=cutoff,
        )
        .values('finished_good__id', 'finished_good__name')
        .annotate(units=Sum('quantity'))
        .order_by('-units')
    )

    if not sold_30d:
        return (
            "No sales data in the last 30 days to base a forecast on.\n"
            "Once sales are recorded, I can suggest restock quantities."
        )

    goods_map = {g.pk: g for g in FinishedGood.objects.filter(is_active=True)}

    lines = ["📦 Restock Forecast — Next 30 Days\n(Based on last 30 days sales velocity)\n"]
    has_rec = False
    for item in sold_30d[:10]:
        gid = item['finished_good__id']
        good = goods_map.get(gid)
        if not good:
            continue
        velocity = item['units']  # units/month
        on_hand = good.quantity_on_hand
        days_cover = (on_hand / velocity * 30) if velocity else 999
        suggested = max(0, round(velocity * 1.2 - on_hand))  # 20% buffer

        if days_cover < 45 or suggested > 0:
            has_rec = True
            urgency = "🔴 URGENT" if days_cover < 15 else ("🟡 Soon" if days_cover < 30 else "🟢 Monitor")
            lines.append(
                f"{urgency} {good.name}\n"
                f"  On hand: {on_hand}  |  Sold/month: {velocity}  |  Days cover: {days_cover:.0f} days\n"
                f"  Suggested order: {suggested} units"
            )

    if not has_rec:
        lines.append("✅ All active products have sufficient stock for the next 45 days based on current sales pace.")

    return "\n".join(lines)


def handle_inventory_status(query: str) -> str:
    from inventory.models import FinishedGood, RawMaterial

    goods = FinishedGood.objects.filter(is_active=True).select_related('category').order_by('-quantity_on_hand')
    total_fg_value = sum(float(g.selling_price) * g.quantity_on_hand for g in goods)

    lines = ["📦 Finished Goods Inventory\n"]
    for g in goods[:12]:
        stock_label = "⚠️" if g.quantity_on_hand == 0 else ("🟡" if g.quantity_on_hand < 3 else "✅")
        lines.append(
            f"{stock_label} {g.name} ({g.category.name})\n"
            f"   In stock: {g.quantity_on_hand}  |  Price: {_fmt(g.selling_price)}"
        )

    raw = RawMaterial.objects.select_related('category').all()
    low_count = sum(1 for m in raw if m.is_low_stock)
    raw_value = sum(m.total_value for m in raw)

    lines += [
        "",
        f"📊 Summary",
        f"  Finished goods total value: {_fmt(total_fg_value)}",
        f"  Raw materials total value:  {_fmt(raw_value)}",
        f"  Low stock raw materials:    {low_count}",
    ]
    return "\n".join(lines)


def handle_labor(query: str) -> str:
    from hr.models import Employee, TimeEntry

    emps = Employee.objects.filter(is_active=True).select_related('user', 'department')
    clocked_in = [e for e in emps if e.get_active_shift()]

    entries_this_month = TimeEntry.objects.filter(
        clock_in__date__gte=_month_start(),
        clock_out__isnull=False,
    ).select_related('employee')

    total_hours = sum(e.net_hours or 0 for e in entries_this_month)
    total_labor_cost = sum(e.labor_cost or 0 for e in entries_this_month)

    lines = [
        f"👥 HR & Labor Report — {_today().strftime('%B %Y')}\n",
        f"Active Employees:   {emps.count()}",
        f"Currently Clocked In: {len(clocked_in)}",
        f"Month-to-date Hours:  {total_hours:.1f} hrs",
        f"Month-to-date Labor:  {_fmt(total_labor_cost)}",
    ]

    if clocked_in:
        lines.append("\n🟢 Currently on shift:")
        for e in clocked_in:
            shift = e.get_active_shift()
            since = shift.clock_in.strftime('%H:%M') if shift else '?'
            lines.append(f"  • {e.full_name} (since {since})")

    # Per-employee summary
    emp_hours = defaultdict(float)
    emp_cost = defaultdict(float)
    for entry in entries_this_month:
        emp_hours[entry.employee_id] += entry.net_hours or 0
        emp_cost[entry.employee_id] += entry.labor_cost or 0

    if emp_hours:
        lines.append("\n📋 This Month by Employee:")
        emp_map = {e.pk: e for e in emps}
        for eid, hrs in sorted(emp_hours.items(), key=lambda x: -x[1])[:6]:
            emp = emp_map.get(eid)
            if emp:
                lines.append(f"  • {emp.full_name}: {hrs:.1f} hrs — {_fmt(emp_cost[eid])}")

    return "\n".join(lines)


def handle_expenses(query: str) -> str:
    try:
        from financials.models import Expense
    except ImportError:
        return "Expense data not available."

    expenses = Expense.objects.filter(date__gte=_month_start())
    total = expenses.aggregate(t=Sum('amount'))['t'] or Decimal('0')

    by_cat = expenses.values('category').annotate(t=Sum('amount')).order_by('-t') if hasattr(Expense, 'category') else []

    revenue = _sales_this_month().aggregate(t=Sum('total_amount'))['t'] or Decimal('1')
    exp_ratio = float(total) / float(revenue) * 100

    lines = [
        f"💸 Operating Expenses — {_today().strftime('%B %Y')}\n",
        f"Total Expenses: {_fmt(total)}",
        f"As % of Revenue: {exp_ratio:.1f}%",
    ]

    if by_cat:
        lines.append("\nBy Category:")
        for row in by_cat[:8]:
            lines.append(f"  • {row['category'] or 'Uncategorised'}: {_fmt(row['t'])}")

    return "\n".join(lines)


def handle_top_customers(query: str) -> str:
    from pos.models import Sale
    customers = (
        Sale.objects.filter(status='completed', customer__isnull=False)
        .values('customer__first_name', 'customer__last_name', 'customer__phone')
        .annotate(visits=Count('id'), spent=Sum('total_amount'))
        .order_by('-spent')[:8]
    )
    walk_ins = Sale.objects.filter(status='completed', customer__isnull=True)
    walk_in_rev = walk_ins.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    walk_in_count = walk_ins.count()

    if not customers and not walk_in_count:
        return "No customer data found yet."

    lines = ["👤 Top Customers (All Time)\n"]
    for i, c in enumerate(customers, 1):
        name = f"{c['customer__first_name']} {c['customer__last_name']}"
        lines.append(
            f"{i}. {name}\n"
            f"   Visits: {c['visits']}  |  Total Spent: {_fmt(c['spent'])}"
        )
    if walk_in_count:
        lines.append(f"\n🚶 Walk-in Customers: {walk_in_count} sales totalling {_fmt(walk_in_rev)}")
    return "\n".join(lines)


def handle_payment_breakdown(query: str) -> str:
    from pos.models import Sale
    breakdown = (
        Sale.objects.filter(status='completed')
        .values('payment_method')
        .annotate(count=Count('id'), total=Sum('total_amount'))
        .order_by('-total')
    )
    if not breakdown:
        return "No payment data found."

    total_all = sum(float(r['total']) for r in breakdown)
    lines = ["💳 Payment Method Breakdown (All Time)\n"]
    labels = {'cash': 'Cash', 'card': 'Card', 'check': 'Check', 'bank_transfer': 'Bank Transfer'}
    for row in breakdown:
        method = labels.get(row['payment_method'], row['payment_method'])
        pct = float(row['total']) / total_all * 100 if total_all else 0
        lines.append(f"• {method}: {row['count']} sales — {_fmt(row['total'])} ({pct:.1f}%)")
    return "\n".join(lines)


def handle_product_match(query: str) -> str:
    from inventory.models import FinishedGood, ProductCategory
    q_lower = query.lower()

    # Detect room/category keywords
    room_keywords = {
        'bedroom': 'Bedroom',
        'living': 'Living Room',
        'dining': 'Dining',
        'office': 'Office',
        'kitchen': 'Kitchen',
        'outdoor': 'Outdoor',
    }
    matched_category = None
    for kw, cat in room_keywords.items():
        if kw in q_lower:
            matched_category = cat
            break

    # Price budget detection
    budget = None
    price_match = re.search(r'(?:budget|under|below|up to|within)[^\d]*(\d[\d,]*)', q_lower)
    if price_match:
        budget = float(price_match.group(1).replace(',', ''))

    goods = FinishedGood.objects.filter(is_active=True, quantity_on_hand__gt=0).select_related('category')
    if matched_category:
        goods = goods.filter(category__name__icontains=matched_category)
    if budget:
        goods = goods.filter(selling_price__lte=budget)

    goods = goods.order_by('-quantity_on_hand')[:8]

    if not goods:
        return (
            f"No available products found matching your criteria.\n"
            "Try a different room type or adjust your budget. "
            "You can also check the Inventory section for the full catalogue."
        )

    prefix = f"for a {matched_category} " if matched_category else ""
    budget_note = f" under {_fmt(budget)}" if budget else ""
    lines = [f"🛋️  Recommended Products {prefix}{budget_note}\n"]
    for g in goods:
        margin_str = f"  |  Margin: {g.profit_margin:.0f}%" if g.profit_margin else ""
        lines.append(
            f"• {g.name} ({g.category.name})\n"
            f"  Price: {_fmt(g.selling_price)}  |  In stock: {g.quantity_on_hand}{margin_str}"
        )
    return "\n".join(lines)


def handle_general(query: str) -> str:
    # Try a broad data summary as a catch-all
    from inventory.models import FinishedGood, RawMaterial
    from pos.models import Sale
    revenue = _sales_this_month().aggregate(t=Sum('total_amount'))['t'] or 0
    total_products = FinishedGood.objects.filter(is_active=True).count()
    low_raw = sum(1 for m in RawMaterial.objects.all() if m.is_low_stock)

    return (
        f"I'm not sure I fully understand the question, but here's a quick snapshot:\n\n"
        f"📊 Month Revenue: {_fmt(revenue)}\n"
        f"📦 Active Products: {total_products}\n"
        f"⚠️  Low Stock Raw Materials: {low_raw}\n\n"
        "Try asking something more specific, like:\n"
        "• 'Which products should I restock?'\n"
        "• 'Show me top customers'\n"
        "• 'Give me the monthly summary'"
    )


# ── main entry point ────────────────────────────────────────────────────────────

HANDLERS = {
    "help": handle_help,
    "monthly_summary": handle_monthly_summary,
    "revenue": handle_revenue,
    "top_selling": handle_top_selling,
    "top_margin": handle_top_margin,
    "low_stock": handle_low_stock,
    "restock_forecast": handle_restock_forecast,
    "inventory_status": handle_inventory_status,
    "labor": handle_labor,
    "expenses": handle_expenses,
    "top_customers": handle_top_customers,
    "payment_breakdown": handle_payment_breakdown,
    "product_match": handle_product_match,
    "general": handle_general,
}


def answer(query: str) -> str:
    intent = classify(query)
    handler = HANDLERS.get(intent, handle_general)
    try:
        return handler(query)
    except Exception as exc:
        return f"Sorry, I hit an error analysing that: {exc}"
