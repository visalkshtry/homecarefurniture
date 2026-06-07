from django.db import models
from django.contrib.auth.models import User


class AIQueryLog(models.Model):
    """
    Audit trail for every query sent to the Gemini Smart Assistant.
    Stores the full context snapshot injected into the prompt so debugging
    hallucinations is possible without re-querying the live database.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ai_queries')
    query = models.TextField(help_text='The natural language question the user asked')
    db_context_snapshot = models.TextField(
        blank=True,
        help_text='The database summary injected into the Gemini prompt at query time'
    )
    response = models.TextField(help_text='The raw text response returned by Gemini')
    prompt_tokens = models.PositiveIntegerField(null=True, blank=True)
    response_tokens = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True, help_text='Round-trip time in milliseconds')
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        snippet = self.query[:60] + '...' if len(self.query) > 60 else self.query
        return f"[{user_str}] {snippet}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI Query Log'
        verbose_name_plural = 'AI Query Logs'
