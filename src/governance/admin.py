from django.contrib import admin

from .models import EnvironmentStage, PromptVersion


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("key", "version", "stage", "created_by", "created_at")
    list_filter = ("key", "stage")
    ordering = ("key", "-version")
    readonly_fields = ("key", "version", "prompt_text", "created_by", "created_at")

    def has_change_permission(self, request, obj=None):
        # Versions are immutable — admin can view/create but never edit a
        # past version in place. The admin's default save() writes every
        # field at once, which PromptVersion.save() would reject even for a
        # stage-only change, so stage advancement is a later-phase workflow
        # action done through the service layer/API, not this admin form.
        return False


@admin.register(EnvironmentStage)
class EnvironmentStageAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "slug")
    ordering = ("order",)
