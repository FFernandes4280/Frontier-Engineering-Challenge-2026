"""Admin registration for dashboard_ui."""

from django.contrib import admin
from .models import EvaluationRun

@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'runner_type', 'score', 'recommendation', 'created_at')
