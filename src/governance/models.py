"""Prompt version tracking (issue #1, Phase 1).

Applies the knowledge-base episodic-memory pattern: versions are immutable,
append-only records queried by exact key/version/timestamp — never by
similarity, never overwritten in place.
"""
from django.conf import settings
from django.db import models, transaction


class PromptVersionManager(models.Manager):
    def create_version(self, key: str, prompt_text: str, created_by=None) -> "PromptVersion":
        """Creates the next version for `key`, auto-incrementing from the
        current highest version. Wrapped in a transaction with a row lock
        on existing versions for this key so two concurrent creators can't
        compute the same "next version" number and collide.
        """
        with transaction.atomic():
            current_max = (
                self.select_for_update()
                .filter(key=key)
                .order_by("-version")
                .values_list("version", flat=True)
                .first()
            )
            next_version = (current_max or 0) + 1
            return self.create(
                key=key,
                version=next_version,
                prompt_text=prompt_text,
                created_by=created_by,
            )


class PromptVersion(models.Model):
    key = models.CharField(max_length=255, db_index=True, help_text="Stable identifier for this prompt template")
    version = models.PositiveIntegerField()
    prompt_text = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="prompt_versions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PromptVersionManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "version"], name="unique_prompt_key_version"),
        ]
        ordering = ["key", "-version"]
        indexes = [models.Index(fields=["key", "-version"])]

    def __str__(self):
        return f"{self.key} v{self.version}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            # Past versions are immutable — re-saving an existing row would
            # silently rewrite audit history. Editing means creating a new
            # version via PromptVersion.objects.create_version(...).
            raise ValueError("PromptVersion records are immutable; create a new version instead of editing one.")
        super().save(*args, **kwargs)
