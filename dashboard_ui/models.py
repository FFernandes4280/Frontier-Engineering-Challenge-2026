"""Database models for dashboard_ui (if persistent records are stored)."""

from django.db import models


class EvaluationRun(models.Model):
    task_id = models.CharField(max_length=255)
    runner_type = models.CharField(max_length=50)
    score = models.FloatField()
    recommendation = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.runner_type} - {self.task_id} ({self.score})'
