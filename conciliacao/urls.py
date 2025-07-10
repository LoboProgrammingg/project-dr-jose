# conciliacao/urls.py

from django.urls import path
from . import views

app_name = 'conciliacao'

urlpatterns = [
    path('', views.pagina_upload, name='pagina_upload'),
    path('historico/', views.lista_relatorios, name='lista_relatorios'),
    path('relatorio/<int:pk>/', views.detalhe_relatorio, name='detalhe_relatorio'),
    
    # --- NOVA ROTA PARA O DOWNLOAD DO EXCEL ---
    path('relatorio/<int:pk>/download/', views.download_relatorio_excel, name='download_relatorio'),
]