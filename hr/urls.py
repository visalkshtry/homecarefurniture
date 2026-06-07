from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    path('', views.hr_dashboard, name='dashboard'),
    path('timesheet/', views.timesheet, name='timesheet'),
    path('<int:employee_id>/clock-in/', views.clock_in, name='clock_in'),
    path('<int:employee_id>/meal-start/', views.meal_start, name='meal_start'),
    path('<int:employee_id>/meal-end/', views.meal_end, name='meal_end'),
    path('<int:employee_id>/clock-out/', views.clock_out, name='clock_out'),
]
