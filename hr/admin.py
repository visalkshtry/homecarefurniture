from django.contrib import admin
from .models import Department, Employee, TimeEntry


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'department', 'role', 'phone', 'hire_date', 'hourly_rate', 'is_active']
    list_filter = ['role', 'department', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'user__username', 'phone']
    readonly_fields = []


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'clock_in', 'clock_out', 'hours_worked', 'labor_cost', 'is_active']
    list_filter = ['employee']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    readonly_fields = ['created_at']
