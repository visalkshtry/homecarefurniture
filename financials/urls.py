from django.urls import path
from . import views

app_name = 'financials'

urlpatterns = [
    path('', views.financials_dashboard, name='dashboard'),
]
