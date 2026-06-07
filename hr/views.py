from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta

from .models import Employee, TimeEntry


@login_required
def hr_dashboard(request):
    employees = Employee.objects.select_related('user', 'department').filter(is_active=True)
    active_shifts = {s.employee_id: s for s in
                     TimeEntry.objects.filter(clock_out__isnull=True).select_related('employee__user')}

    today = timezone.localdate()
    today_entries = TimeEntry.objects.filter(
        clock_in__date=today, clock_out__isnull=False
    ).select_related('employee__user')

    # Build enriched rows so the template needs no dict lookups
    employee_rows = []
    for emp in employees:
        shift = active_shifts.get(emp.id)
        employee_rows.append({
            'emp': emp,
            'shift': shift,
            'is_clocked_in': shift is not None,
            'on_break': shift is not None and shift.on_meal_break,
            'clock_in_time': timezone.localtime(shift.clock_in).strftime('%I:%M %p').lstrip('0') if shift else '',
        })

    context = {
        'employee_rows': employee_rows,
        'clocked_in_count': sum(1 for r in employee_rows if r['is_clocked_in']),
        'on_break_count': sum(1 for r in employee_rows if r['on_break']),
        'today_entries': today_entries,
        'today': today,
    }
    return render(request, 'hr/dashboard.html', context)


@login_required
@require_POST
def clock_in(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    if TimeEntry.objects.filter(employee=employee, clock_out__isnull=True).exists():
        messages.warning(request, f"{employee.full_name} is already clocked in.")
    else:
        TimeEntry.objects.create(employee=employee, clock_in=timezone.now())
        messages.success(request, f"{employee.full_name} clocked in at {timezone.localtime().strftime('%I:%M %p')}.")
    return redirect('hr:dashboard')


@login_required
@require_POST
def meal_start(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    entry = TimeEntry.objects.filter(employee=employee, clock_out__isnull=True).first()
    if not entry:
        messages.error(request, f"{employee.full_name} is not clocked in.")
    elif entry.on_meal_break:
        messages.warning(request, f"{employee.full_name} is already on a meal break.")
    else:
        entry.meal_start = timezone.now()
        entry.save(update_fields=['meal_start'])
        messages.success(request, f"Meal break started for {employee.full_name}.")
    return redirect('hr:dashboard')


@login_required
@require_POST
def meal_end(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    entry = TimeEntry.objects.filter(employee=employee, clock_out__isnull=True).first()
    if not entry or not entry.on_meal_break:
        messages.error(request, f"{employee.full_name} is not on a meal break.")
    else:
        entry.meal_end = timezone.now()
        entry.save(update_fields=['meal_end'])
        messages.success(request, f"Meal break ended for {employee.full_name}.")
    return redirect('hr:dashboard')


@login_required
@require_POST
def clock_out(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    entry = TimeEntry.objects.filter(employee=employee, clock_out__isnull=True).first()
    if not entry:
        messages.error(request, f"{employee.full_name} is not clocked in.")
    else:
        if entry.on_meal_break:
            entry.meal_end = timezone.now()
        entry.clock_out = timezone.now()
        entry.save(update_fields=['clock_out', 'meal_end'])
        messages.success(
            request,
            f"{employee.full_name} clocked out. Net hours: {entry.net_hours}h | "
            f"Labor cost: रू {entry.labor_cost or 0:.2f}"
        )
    return redirect('hr:dashboard')


@login_required
def timesheet(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    entries = TimeEntry.objects.filter(
        clock_in__date__gte=week_start
    ).select_related('employee__user').order_by('-clock_in')

    employees = Employee.objects.filter(is_active=True).select_related('user')
    weekly_summary = []
    for emp in employees:
        hours = emp.get_weekly_hours(week_start)
        cost = emp.get_weekly_labor_cost(week_start)
        weekly_summary.append({'employee': emp, 'hours': hours, 'cost': cost})

    context = {
        'entries': entries,
        'weekly_summary': weekly_summary,
        'week_start': week_start,
    }
    return render(request, 'hr/timesheet.html', context)
