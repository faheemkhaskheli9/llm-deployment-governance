"""Regression tests for issue #1: prompt version tracking."""
import json

import pytest
from django.db import IntegrityError
from django.urls import reverse

from governance.models import PromptVersion

pytestmark = pytest.mark.django_db


def test_first_version_is_1():
    v = PromptVersion.objects.create_version(key="welcome_email", prompt_text="Hello {name}!")
    assert v.version == 1


def test_version_auto_increments_per_key():
    PromptVersion.objects.create_version(key="welcome_email", prompt_text="v1")
    v2 = PromptVersion.objects.create_version(key="welcome_email", prompt_text="v2")
    v3 = PromptVersion.objects.create_version(key="welcome_email", prompt_text="v3")
    assert [v2.version, v3.version] == [2, 3]


def test_versions_are_independent_per_key():
    PromptVersion.objects.create_version(key="a", prompt_text="a1")
    PromptVersion.objects.create_version(key="a", prompt_text="a2")
    v = PromptVersion.objects.create_version(key="b", prompt_text="b1")
    assert v.version == 1  # a separate key starts its own sequence


def test_creating_new_version_does_not_overwrite_prior_version():
    v1 = PromptVersion.objects.create_version(key="k", prompt_text="original text")
    PromptVersion.objects.create_version(key="k", prompt_text="updated text")

    v1_reloaded = PromptVersion.objects.get(pk=v1.pk)
    assert v1_reloaded.prompt_text == "original text"
    assert PromptVersion.objects.filter(key="k").count() == 2


def test_past_version_cannot_be_edited_in_place():
    v1 = PromptVersion.objects.create_version(key="k", prompt_text="original")
    v1.prompt_text = "tampered"
    with pytest.raises(ValueError):
        v1.save()


def test_duplicate_key_version_pair_rejected_at_db_level():
    PromptVersion.objects.create(key="k", version=1, prompt_text="a")
    with pytest.raises(IntegrityError):
        PromptVersion.objects.create(key="k", version=1, prompt_text="b")


def test_api_lists_versions_newest_first(client):
    PromptVersion.objects.create_version(key="k", prompt_text="v1")
    PromptVersion.objects.create_version(key="k", prompt_text="v2")
    PromptVersion.objects.create_version(key="k", prompt_text="v3")

    response = client.get(reverse("prompt-versions", args=["k"]))
    assert response.status_code == 200
    data = json.loads(response.content)
    versions = [item["version"] for item in data["versions"]]
    assert versions == [3, 2, 1]


def test_api_returns_empty_list_for_unknown_key(client):
    response = client.get(reverse("prompt-versions", args=["does-not-exist"]))
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data["versions"] == []
