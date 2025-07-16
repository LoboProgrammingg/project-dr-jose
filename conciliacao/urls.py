# conciliacao/urls.py

from django.urls import path
from . import views

app_name = 'conciliacao'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    path('upload/', views.pagina_upload, name='pagina_upload'),
        
    path('historico/', views.lista_relatorios, name='lista_relatorios'),
    path('relatorio/<int:pk>/', views.detalhe_relatorio, name='detalhe_relatorio'),
    path('relatorio/<int:pk>/download/', views.download_relatorio_excel, name='download_relatorio'),
    
    path('instrucoes-ofx/', views.instrucoes_ofx, name='instrucoes_ofx'),
]
