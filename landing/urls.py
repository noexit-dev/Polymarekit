from django.urls import path

from .views import health, home


urlpatterns = [
    path("api/health", health, name="health"),
    path("", home, name="home"),
]
