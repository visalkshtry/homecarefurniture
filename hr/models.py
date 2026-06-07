from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Employee(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_MANAGER = 'manager'
    ROLE_EMPLOYEE = 'employee'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_EMPLOYEE, 'Employee'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='employees'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    hire_date = models.DateField(default=timezone.now)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    profile_photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def get_active_shift(self):
        return self.time_entries.filter(clock_out__isnull=True).first()

    def get_weekly_hours(self, week_start):
        from datetime import timedelta
        week_end = week_start + timedelta(days=7)
        entries = self.time_entries.filter(
            clock_in__date__gte=week_start,
            clock_in__date__lt=week_end,
            clock_out__isnull=False,
        )
        return round(sum(e.net_hours or 0 for e in entries), 2)

    def get_weekly_labor_cost(self, week_start):
        return round(self.get_weekly_hours(week_start) * float(self.hourly_rate), 2)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']


class TimeEntry(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='time_entries')
    clock_in = models.DateTimeField()
    meal_start = models.DateTimeField(null=True, blank=True)
    meal_end = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        out_str = self.clock_out.strftime('%H:%M') if self.clock_out else 'Active'
        return f"{self.employee.full_name} | {self.clock_in.strftime('%Y-%m-%d %H:%M')} → {out_str}"

    @property
    def meal_duration_hours(self):
        if self.meal_start and self.meal_end:
            return round((self.meal_end - self.meal_start).total_seconds() / 3600, 2)
        return 0

    @property
    def gross_hours(self):
        if self.clock_out:
            return round((self.clock_out - self.clock_in).total_seconds() / 3600, 2)
        return None

    @property
    def net_hours(self):
        """Total hours worked minus meal break."""
        if self.clock_out:
            gross = (self.clock_out - self.clock_in).total_seconds()
            meal = 0
            if self.meal_start and self.meal_end:
                meal = (self.meal_end - self.meal_start).total_seconds()
            return round((gross - meal) / 3600, 2)
        return None

    # Keep backward-compat alias
    @property
    def hours_worked(self):
        return self.net_hours

    @property
    def labor_cost(self):
        if self.net_hours is not None:
            return round(self.net_hours * float(self.employee.hourly_rate), 2)
        return None

    @property
    def is_active(self):
        return self.clock_out is None

    @property
    def on_meal_break(self):
        return self.meal_start is not None and self.meal_end is None

    class Meta:
        ordering = ['-clock_in']
