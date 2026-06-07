from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_dashboard, name='dashboard'),
    path('production/<int:pk>/complete/', views.production_run_complete, name='production_complete'),
]
