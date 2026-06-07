import io
from django.shortcuts import render, redirect, get_object_or_404

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.conf import settings

from .models import Sale, SaleLineItem, Customer
from inventory.models import FinishedGood
from hr.models import Employee


def sales_dashboard(request):
    sales = Sale.objects.select_related('customer', 'served_by__user').order_by('-sale_date')[:50]
    today = timezone.localdate()
    today_sales = [s for s in Sale.objects.filter(sale_date__date=today, status=Sale.STATUS_COMPLETED)]
    today_revenue = sum(float(s.total_amount) for s in today_sales)
    context = {
        'sales': sales,
        'today_revenue': today_revenue,
        'today_count': len(today_sales),
    }
    return render(request, 'pos/dashboard.html', context)


def new_sale(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id') or None
        employee_id = request.POST.get('employee_id') or None
        payment_method = request.POST.get('payment_method', Sale.PAYMENT_CASH)
        notes = request.POST.get('notes', '')
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')

        if not product_ids:
            messages.error(request, 'Add at least one product.')
            return _render_new_sale(request)

        sale = Sale.objects.create(
            customer_id=customer_id,
            served_by_id=employee_id,
            payment_method=payment_method,
            notes=notes,
            tax_rate=settings.DEFAULT_TAX_RATE,
        )

        for pid, qty in zip(product_ids, quantities):
            try:
                qty = int(qty)
                if qty < 1:
                    continue
                fg = FinishedGood.objects.get(pk=pid)
                SaleLineItem.objects.create(
                    sale=sale,
                    finished_good=fg,
                    quantity=qty,
                    unit_price=fg.selling_price,
                )
            except (FinishedGood.DoesNotExist, ValueError):
                continue

        if not sale.line_items.exists():
            sale.delete()
            messages.error(request, 'No valid products added.')
            return _render_new_sale(request)

        try:
            sale.complete_sale()
            messages.success(request, f'Sale {sale.receipt_number} completed — रू {sale.total_amount}')
            return redirect('pos:receipt', pk=sale.pk)
        except Exception as e:
            sale.delete()
            messages.error(request, str(e))
            return _render_new_sale(request)

    return _render_new_sale(request)


def _render_new_sale(request):
    return render(request, 'pos/new_sale.html', {
        'customers': Customer.objects.order_by('last_name'),
        'employees': Employee.objects.filter(is_active=True).select_related('user'),
        'products': FinishedGood.objects.filter(is_active=True, quantity_on_hand__gt=0).select_related('category'),
        'payment_choices': Sale.PAYMENT_CHOICES,
    })


def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer', 'served_by__user'), pk=pk)
    items = sale.line_items.select_related('finished_good')
    return render(request, 'pos/sale_detail.html', {'sale': sale, 'items': items})


def receipt_pdf(request, pk):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    sale = get_object_or_404(Sale, pk=pk)
    items = sale.line_items.select_related('finished_good').all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.75*inch, rightMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('title', parent=styles['Heading1'], alignment=1, fontSize=20, textColor=colors.HexColor('#1a56db'))
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], alignment=1, fontSize=10, textColor=colors.grey)
    normal = styles['Normal']

    story.append(Paragraph('Home Care Furniture', title_style))
    story.append(Paragraph('Furniture Manufacturer', sub_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#1a56db')))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph(f'<b>Receipt #:</b> {sale.receipt_number}', normal))
    story.append(Paragraph(f'<b>Date:</b> {sale.sale_date.strftime("%B %d, %Y %I:%M %p")}', normal))
    customer_name = sale.customer.full_name if sale.customer else 'Walk-in Customer'
    story.append(Paragraph(f'<b>Customer:</b> {customer_name}', normal))
    if sale.served_by:
        story.append(Paragraph(f'<b>Sales Rep:</b> {sale.served_by.full_name}', normal))
    story.append(Paragraph(f'<b>Payment:</b> {sale.get_payment_method_display()}', normal))
    story.append(Spacer(1, 0.2*inch))

    table_data = [['Product', 'Qty', 'Unit Price', 'Total']]
    for item in items:
        table_data.append([
            item.finished_good.name,
            str(item.quantity),
            f'रू {item.unit_price:.2f}',
            f'रू {item.line_total:.2f}',
        ])

    table = Table(table_data, colWidths=[3.5*inch, 0.75*inch, 1.25*inch, 1.25*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a56db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.15*inch))

    totals = [
        ['Subtotal', f'रू {sale.subtotal:.2f}'],
        [f'Tax ({float(sale.tax_rate)*100:.1f}%)', f'रू {sale.tax_amount:.2f}'],
    ]
    if float(sale.discount_amount) > 0:
        totals.append(['Discount', f'-रू {sale.discount_amount:.2f}'])
    totals.append(['TOTAL', f'रू {sale.total_amount:.2f}'])

    totals_table = Table(totals, colWidths=[5.5*inch, 1.25*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#1a56db')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('Thank you for your business!', ParagraphStyle('thanks', parent=styles['Normal'], alignment=1, textColor=colors.grey)))

    doc.build(story)
    buf.seek(0)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receipt_{sale.receipt_number}.pdf"'
    return response


@login_required
def product_price(request, pk):
    fg = get_object_or_404(FinishedGood, pk=pk)
    return JsonResponse({'price': float(fg.selling_price), 'stock': fg.quantity_on_hand, 'name': fg.name})
