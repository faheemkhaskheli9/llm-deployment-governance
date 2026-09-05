from django.http import JsonResponse

from .models import PromptVersion


def health(request):
    return JsonResponse({"status": "ok", "app": "llm-deployment-governance"})


def prompt_versions(request, key: str):
    """Lists all versions of `key`, newest first (acceptance criterion #3)."""
    versions = PromptVersion.objects.filter(key=key).order_by("-version")
    return JsonResponse(
        {
            "key": key,
            "versions": [
                {
                    "version": v.version,
                    "prompt_text": v.prompt_text,
                    "created_by": v.created_by.username if v.created_by else None,
                    "created_at": v.created_at.isoformat(),
                }
                for v in versions
            ],
        }
    )
