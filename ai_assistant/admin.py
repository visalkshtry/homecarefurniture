from django.contrib import admin
from .models import AIQueryLog


@admin.register(AIQueryLog)
class AIQueryLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'query', 'was_successful', 'latency_ms', 'created_at']
    list_filter = ['was_successful']
    search_fields = ['user__username', 'query']
    readonly_fields = ['created_at', 'prompt_tokens', 'response_tokens', 'latency_ms']
