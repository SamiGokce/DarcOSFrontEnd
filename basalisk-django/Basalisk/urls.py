from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from forge import views as forge_views
from home import views

urlpatterns = [
    path('shelf/', forge_views.forge_page, name='forge'),
    path('admin/', admin.site.urls),
    path('api/forge/', include('forge.urls')),
    path('api/', include('home.urls')),
    re_path(r'^(?P<path>.*)$', views.serve_frontend, name='frontend'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
