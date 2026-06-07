from django.shortcuts import render

from django.utils import timezone
from datetime import timedelta
import json

from .models import Expense
from pos.models import Sale
from hr.models import TimeEntry


def financials_dashboard(request):
    today = timezone.localdate()

    # Build last 6 months of monthly data
    months = []
    for i in range(5, -1, -1):
        # first day of each month going back
        d = today.replace(day=1) - timedelta(days=1)
        for _ in range(i):
            d = d.replace(day=1) - timedelta(days=1)
        month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        # Simpler: compute directly
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        from calendar import monthrange
        month_start = today.replace(year=year, month=month, day=1)
        last_day = monthrange(year, month)[1]
        month_end = month_start.replace(day=last_day)

        revenue = sum(
            float(s.total_amount) for s in
            Sale.objects.filter(sale_date__date__gte=month_start, sale_date__date__lte=month_end, status=Sale.STATUS_COMPLETED)
        )
        expenses = sum(
            float(e.amount) for e in
            Expense.objects.filter(expense_date__gte=month_start, expense_date__lte=month_end)
        )
        labor = sum(
            (entry.labor_cost or 0) for entry in
            TimeEntry.objects.filter(clock_in__date__gte=month_start, clock_in__date__lte=month_end, clock_out__isnull=False)
        )
        months.append({
            'label': month_start.strftime('%b %Y'),
            'revenue': round(revenue, 2),
            'expenses': round(expenses + labor, 2),
            'profit': round(revenue - expenses - labor, 2),
        })

    # Current month totals
    month_start = today.replace(day=1)
    current_revenue = sum(
        float(s.total_amount) for s in
        Sale.objects.filter(sale_date__date__gte=month_start, status=Sale.STATUS_COMPLETED)
    )
    current_expenses = sum(
        float(e.amount) for e in Expense.objects.filter(expense_date__gte=month_start)
    )
    current_labor = sum(
        (entry.labor_cost or 0) for entry in
        TimeEntry.objects.filter(clock_in__date__gte=month_start, clock_out__isnull=False)
    )
    current_profit = current_revenue - current_expenses - current_labor

    # Expense breakdown by category
    expense_by_cat = {}
    for e in Expense.objects.filter(expense_date__gte=month_start):
        label = e.get_category_display()
        expense_by_cat[label] = expense_by_cat.get(label, 0) + float(e.amount)

    recent_expenses = Expense.objects.order_by('-expense_date')[:20]

    context = {
        'months_json': json.dumps(months),
        'expense_cat_json': json.dumps(expense_by_cat),
        'current_revenue': current_revenue,
        'current_expenses': current_expenses,
        'current_labor': current_labor,
        'current_profit': current_profit,
        'recent_expenses': recent_expenses,
        'today': today,
    }
    return render(request, 'financials/dashboard.html', context)
