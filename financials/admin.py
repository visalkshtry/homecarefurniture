from django.contrib import admin
from .models import Expense, ProfitLossSnapshot


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'category', 'amount', 'expense_date', 'recorded_by', 'created_at']
    list_filter = ['category']
    search_fields = ['description']
    readonly_fields = ['created_at']


@admin.register(ProfitLossSnapshot)
class ProfitLossSnapshotAdmin(admin.ModelAdmin):
    list_display = ['period_type', 'period_start', 'period_end', 'total_revenue', 'gross_profit', 'net_profit', 'units_sold']
    list_filter = ['period_type']
    readonly_fields = ['generated_at']
