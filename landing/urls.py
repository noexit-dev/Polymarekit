from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("api/health", views.health, name="health"),
    path("", views.home, name="home"),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="landing/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/delete/", views.delete_account, name="delete_account"),
    path("profile/", views.profile, name="profile"),
    path("wallet/", views.wallet, name="wallet"),
]
