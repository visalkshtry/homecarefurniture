from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import RawMaterial, FinishedGood, MaterialCategory, ProductCategory, ProductionRun


@login_required
def inventory_dashboard(request):
    raw_materials = RawMaterial.objects.select_related('category').all()
    finished_goods = FinishedGood.objects.select_related('category').filter(is_active=True)
    low_stock = [m for m in raw_materials if m.is_low_stock]
    out_of_stock = [g for g in finished_goods if g.quantity_on_hand == 0]

    total_raw_value = sum(m.total_value for m in raw_materials)
    total_fg_value = sum(float(g.quantity_on_hand) * float(g.selling_price) for g in finished_goods)

    recent_runs = ProductionRun.objects.select_related('finished_good', 'produced_by__user').order_by('-production_date')[:10]

    context = {
        'raw_materials': raw_materials,
        'finished_goods': finished_goods,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_raw_value': total_raw_value,
        'total_fg_value': total_fg_value,
        'recent_runs': recent_runs,
        'mat_categories': MaterialCategory.objects.all(),
        'prod_categories': ProductCategory.objects.all(),
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def production_run_complete(request, pk):
    run = get_object_or_404(ProductionRun, pk=pk)
    try:
        run.complete()
        messages.success(request, f'Production run #{pk} completed — {run.quantity_produced}x {run.finished_good.name}')
    except Exception as e:
        messages.error(request, str(e))
    return redirect('inventory:dashboard')
