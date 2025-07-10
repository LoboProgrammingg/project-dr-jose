# core/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Importa as views de autenticação e o dashboard diretamente
from conciliacao.views import PaginaLoginView, PaginaLogoutView, dashboard

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- ROTAS PRINCIPAIS E DE AUTENTICAÇÃO ---
    # A raiz do site (/) agora aponta para a tela de login.
    path('', PaginaLoginView.as_view(), name='login'),
    
    # A página inicial para usuários logados.
    path('dashboard/', dashboard, name='home'), 
    
    # A rota de logout.
    path('logout/', PaginaLogoutView.as_view(), name='logout'),

    # --- ROTAS DAS APPS ---
    # Delega todas as URLs que começam com /conciliacao/ para a app de conciliação.
    path('conciliacao/', include('conciliacao.urls')),
    
    # Delega todas as URLs que começam com /credores/ para a app de credores.
    path('credores/', include('credores.urls')),
]

# Configuração para servir arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)