from django.shortcuts import render

from django.utils import timezone

from inventory.models import RawMaterial, FinishedGood
from pos.models import Sale
from hr.models import TimeEntry
from financials.models import Expense



def dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    today_revenue = sum(
        float(s.total_amount) for s in
        Sale.objects.filter(sale_date__date=today, status=Sale.STATUS_COMPLETED)
    )
    month_revenue = sum(
        float(s.total_amount) for s in
        Sale.objects.filter(sale_date__date__gte=month_start, status=Sale.STATUS_COMPLETED)
    )

    low_stock_count = sum(1 for m in RawMaterial.objects.all() if m.is_low_stock)
    out_of_stock_count = FinishedGood.objects.filter(quantity_on_hand=0, is_active=True).count()
    clocked_in_count = TimeEntry.objects.filter(clock_out__isnull=True).count()

    recent_sales = Sale.objects.select_related('customer', 'served_by__user').order_by('-sale_date')[:5]

    total_expenses = sum(
        float(e.amount) for e in Expense.objects.filter(expense_date__gte=month_start)
    )
    net_profit = month_revenue - total_expenses

    return render(request, 'dashboard.html', {
        'today_revenue': today_revenue,
        'month_revenue': month_revenue,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'clocked_in_count': clocked_in_count,
        'recent_sales': recent_sales,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'today': today,
    })
