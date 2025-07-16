from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from conciliacao.views import PaginaLoginView, PaginaLogoutView, dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', PaginaLoginView.as_view(), name='login'),
    path('dashboard/', dashboard, name='home'),
    path('logout/', PaginaLogoutView.as_view(), name='logout'),
    path('conciliacao/', include('conciliacao.urls')),
    path('credores/', include('credores.urls')),
    path('planilhas/', include('planilhas.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
