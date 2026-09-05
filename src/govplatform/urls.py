from django.contrib import admin
from django.urls import path

from governance.views import health, prompt_versions

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", health, name="health"),
    path("api/prompts/<str:key>/versions/", prompt_versions, name="prompt-versions"),
]
