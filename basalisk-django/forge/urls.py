from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('personas', views.PersonaViewSet)
router.register('models', views.LanguageModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('mold/', views.MoldView.as_view(), name='forge-mold'),
    path('speak/', views.SpeakView.as_view(), name='forge-speak'),
    path('model/', views.ModelView.as_view(), name='forge-model'),
]
