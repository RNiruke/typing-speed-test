from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class TypingResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    wpm = models.IntegerField()
    accuracy = models.FloatField()
    grammar_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.wpm} WPM"

