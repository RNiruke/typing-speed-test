from django.contrib import admin
from .models import TypingResult


@admin.register(TypingResult)
class TypingResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'live_wpm', 'accuracy', 'grammar_score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    ordering = ('-created_at',)

    def live_wpm(self, obj):
        return obj.wpm

    live_wpm.short_description = "LIVE WPM"
