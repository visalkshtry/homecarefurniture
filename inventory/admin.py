from django.contrib import admin
from .models import MaterialCategory, RawMaterial, ProductCategory, FinishedGood, BillOfMaterials, ProductionRun


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'unit', 'quantity_on_hand', 'cost_per_unit', 'is_low_stock']
    list_filter = ['category', 'unit']
    search_fields = ['name', 'sku', 'supplier_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(FinishedGood)
class FinishedGoodAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'quantity_on_hand', 'selling_price', 'calculated_bom_cost', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'sku']
    readonly_fields = ['calculated_bom_cost', 'created_at', 'updated_at']


@admin.register(BillOfMaterials)
class BillOfMaterialsAdmin(admin.ModelAdmin):
    list_display = ['finished_good', 'raw_material', 'quantity_required']
    list_filter = ['finished_good']
    search_fields = ['finished_good__name', 'raw_material__name']


@admin.register(ProductionRun)
class ProductionRunAdmin(admin.ModelAdmin):
    list_display = ['pk', 'finished_good', 'quantity_produced', 'status', 'produced_by', 'production_date']
    list_filter = ['status']
    search_fields = ['finished_good__name']
    readonly_fields = ['production_date', 'completed_at']
