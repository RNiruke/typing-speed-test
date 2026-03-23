from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import TypingResult, ImageInfo


# ================================================================
# CUSTOM USER ADMIN — adds green tick / red cross for is_active
# in the user list view
# ================================================================
class CustomUserAdmin(UserAdmin):

    # ✅ Columns shown in the user LIST page
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'activation_status',   # ← our custom green/red column
        'is_staff',
        'date_joined',
    )

    # ✅ Allow filtering by active status in the right sidebar
    list_filter = ('is_active', 'is_staff', 'date_joined')

    # ✅ Allow searching by email/name
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # ✅ Sort by newest first
    ordering = ('-date_joined',)

    # ✅ Custom column: shows ✅ green tick or ❌ red cross
    def activation_status(self, obj):
     if obj.is_active:
        return format_html(
            '<span style="color: green; font-size: 18px; font-weight: bold;">{}</span>',
            '✔'
        )
     else:
        return format_html(
            '<span style="color: red; font-size: 18px; font-weight: bold;">{}</span>',
            '✘ Inactive'
        )

    activation_status.short_description = 'Activated'   # column header name
    activation_status.admin_order_field = 'is_active'   # allow sorting by this column


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ================================================================
# TYPING RESULT ADMIN
# ================================================================
@admin.register(TypingResult)
class TypingResultAdmin(admin.ModelAdmin):
    list_display  = ('user', 'wpm', 'accuracy', 'grammar_score', 'time_limit', 'created_at')
    list_filter   = ('time_limit', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering      = ('-created_at',)


# ================================================================
# IMAGE INFO ADMIN
# ================================================================
@admin.register(ImageInfo)
class ImageInfoAdmin(admin.ModelAdmin):
    list_display  = ('image', 'time_limit', 'extracted_text')
    list_filter   = ('time_limit',)