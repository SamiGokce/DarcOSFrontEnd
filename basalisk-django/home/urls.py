from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import auth_views, views

urlpatterns = [
    path('health/', views.api_health, name='api-health'),
    path('auth/register/', auth_views.RegisterView.as_view(), name='auth-register'),
    path('auth/login/', auth_views.LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/me/', auth_views.MeView.as_view(), name='auth-me'),
]
