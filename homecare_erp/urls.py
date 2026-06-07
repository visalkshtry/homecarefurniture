from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('hr/', include('hr.urls')),
    path('sales/', include('pos.urls')),
    path('inventory/', include('inventory.urls')),
    path('financials/', include('financials.urls')),
    path('ai/', include('ai_assistant.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
