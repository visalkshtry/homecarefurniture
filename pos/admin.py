from django.contrib import admin
from .models import Customer, Sale, SaleLineItem


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at']


class SaleLineItemInline(admin.TabularInline):
    model = SaleLineItem
    extra = 1
    readonly_fields = ['line_total']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'customer', 'served_by', 'status', 'payment_method', 'total_amount', 'sale_date']
    list_filter = ['status', 'payment_method']
    search_fields = ['receipt_number', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['receipt_number', 'sale_date', 'subtotal', 'tax_amount', 'total_amount']
    inlines = [SaleLineItemInline]


@admin.register(SaleLineItem)
class SaleLineItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'finished_good', 'quantity', 'unit_price', 'line_total']
    readonly_fields = ['line_total']
