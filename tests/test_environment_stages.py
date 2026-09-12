"""Regression tests for issue #3: environment/pipeline stage data model."""
import pytest
from django.db import IntegrityError, connection, transaction

from governance.models import EnvironmentStage, PromptVersion

pytestmark = pytest.mark.django_db


def test_five_standard_stages_are_seeded_in_order():
    slugs = list(EnvironmentStage.objects.order_by("order").values_list("slug", flat=True))
    assert slugs == [
        EnvironmentStage.DEVELOPMENT,
        EnvironmentStage.EVALUATION,
        EnvironmentStage.REVIEW,
        EnvironmentStage.APPROVED,
        EnvironmentStage.PRODUCTION,
    ]


def test_stage_order_values_are_1_through_5():
    orders = list(EnvironmentStage.objects.order_by("order").values_list("order", flat=True))
    assert orders == [1, 2, 3, 4, 5]


def test_new_version_defaults_to_development_stage():
    v = PromptVersion.objects.create_version(key="k", prompt_text="hello")
    assert v.stage.slug == EnvironmentStage.DEVELOPMENT


def test_version_stage_can_be_advanced_to_a_defined_stage():
    v = PromptVersion.objects.create_version(key="k", prompt_text="hello")
    evaluation = EnvironmentStage.objects.get(slug=EnvironmentStage.EVALUATION)

    v.stage = evaluation
    v.save(update_fields=["stage"])

    v.refresh_from_db()
    assert v.stage.slug == EnvironmentStage.EVALUATION


def test_advancing_stage_cannot_smuggle_in_other_field_changes():
    v = PromptVersion.objects.create_version(key="k", prompt_text="hello")
    evaluation = EnvironmentStage.objects.get(slug=EnvironmentStage.EVALUATION)

    v.stage = evaluation
    v.prompt_text = "tampered"
    with pytest.raises(ValueError):
        v.save(update_fields=["stage", "prompt_text"])


def test_version_stage_cannot_reference_a_nonexistent_stage():
    # On SQLite, FK checks inside an atomic block are deferred until the
    # transaction is validated, so the failing UPDATE and the explicit
    # constraint check both need to sit inside the same pytest.raises to
    # catch the violation regardless of backend (Postgres raises on save()
    # itself; SQLite raises on check_constraints()). The whole attempt also
    # has to run inside its own transaction.atomic() so that, when it fails,
    # only that savepoint (and the invalid row/pending FK violation it
    # created) gets rolled back — otherwise the deferred SQLite violation
    # would still be sitting there when the outer test transaction is torn
    # down, and on Postgres the failed save() would otherwise poison the
    # rest of the connection for the remainder of the test.
    v = PromptVersion.objects.create_version(key="k", prompt_text="hello")
    v.stage_id = 999999
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            v.save(update_fields=["stage"])
            connection.check_constraints()


def test_duplicate_stage_slug_rejected_at_db_level():
    with pytest.raises(IntegrityError):
        EnvironmentStage.objects.create(slug=EnvironmentStage.DEVELOPMENT, name="Dev Again", order=99)


def test_duplicate_stage_order_rejected_at_db_level():
    with pytest.raises(IntegrityError):
        EnvironmentStage.objects.create(slug="staging", name="Staging", order=1)
