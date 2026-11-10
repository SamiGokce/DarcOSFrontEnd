from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('models', views.LanguageModelViewSet)
router.register('chats', views.ChatViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('souls/', views.SoulListView.as_view(), name='forge-souls'),
    path('souls/<str:slug>/memories/', views.SoulMemoriesView.as_view(), name='forge-soul-memories'),
    path('souls/<str:slug>/', views.SoulDetailView.as_view(), name='forge-soul'),
    path('model/', views.ModelView.as_view(), name='forge-model'),
    path('model-card/', views.ModelCardView.as_view(), name='forge-model-card'),
    path('recall/', views.RecallView.as_view(), name='forge-recall'),
    path('huggingface/', views.HuggingFaceView.as_view(), name='forge-huggingface'),
]
