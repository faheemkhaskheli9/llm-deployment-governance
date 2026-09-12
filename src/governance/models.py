"""Prompt version tracking (issue #1, Phase 1) and pipeline stage model
(issue #3, Phase 1).

Applies the knowledge-base episodic-memory pattern: versions are immutable,
append-only records queried by exact key/version/timestamp — never by
similarity, never overwritten in place.

The EnvironmentStage model below is a plain ordered lookup table for a fixed
five-stage pipeline; no knowledge-base pattern (memory/rag/agentic-loops/ml)
matches this closely, so it is implemented as a standard Django model rather
than adapted from an existing pattern file.
"""
from django.conf import settings
from django.db import models, transaction


class EnvironmentStage(models.Model):
    """One of the five fixed stages a version moves through end to end.

    Development -> Evaluation -> Review -> Approved -> Production.
    Stored as rows (rather than a plain choices enum) so later phases
    (state-machine enforcement, deployment history) can attach data per
    stage without a schema change.
    """

    DEVELOPMENT = "development"
    EVALUATION = "evaluation"
    REVIEW = "review"
    APPROVED = "approved"
    PRODUCTION = "production"

    STANDARD_STAGES = (
        (DEVELOPMENT, "Development", 1),
        (EVALUATION, "Evaluation", 2),
        (REVIEW, "Review", 3),
        (APPROVED, "Approved", 4),
        (PRODUCTION, "Production", 5),
    )

    slug = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    order = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name

    @classmethod
    def default_stage(cls):
        """Returns the pk of the first pipeline stage (Development).

        Seeded by a data migration in the normal case; falls back to
        get_or_create so an out-of-band test DB (migrations skipped) still
        gets a usable default instead of an FK error.
        """
        stage, _ = cls.objects.get_or_create(
            slug=cls.DEVELOPMENT, defaults={"name": "Development", "order": 1}
        )
        return stage.pk


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
    stage = models.ForeignKey(
        EnvironmentStage,
        on_delete=models.PROTECT,
        related_name="prompt_versions",
        default=EnvironmentStage.default_stage,
        help_text="Current pipeline stage for this version.",
    )

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
            # version via PromptVersion.objects.create_version(...). The one
            # exception is advancing `stage` as the version moves through the
            # pipeline, which must be done explicitly via
            # save(update_fields=["stage"]) so no other field can ride along.
            update_fields = kwargs.get("update_fields")
            if update_fields is None or set(update_fields) - {"stage"}:
                raise ValueError(
                    "PromptVersion records are immutable; create a new version instead of "
                    "editing one. To advance the pipeline stage use "
                    "save(update_fields=['stage'])."
                )
        super().save(*args, **kwargs)
