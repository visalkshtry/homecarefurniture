from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.sales_dashboard, name='dashboard'),
    path('new/', views.new_sale, name='new_sale'),
    path('<int:pk>/', views.sale_detail, name='detail'),
    path('<int:pk>/receipt/', views.receipt_pdf, name='receipt'),
    path('product/<int:pk>/price/', views.product_price, name='product_price'),
]
