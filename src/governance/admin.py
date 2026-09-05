from django.contrib import admin

from .models import PromptVersion


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("key", "version", "created_by", "created_at")
    list_filter = ("key",)
    ordering = ("key", "-version")
    readonly_fields = ("key", "version", "prompt_text", "created_by", "created_at")

    def has_change_permission(self, request, obj=None):
        # Versions are immutable — admin can view/create but never edit a
        # past version in place.
        return False
