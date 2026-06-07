from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.ai_dashboard, name='dashboard'),
    path('ask/', views.ask_ai, name='ask'),
]
