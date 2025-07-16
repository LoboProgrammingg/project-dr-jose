# planilhas/urls.py
from django.urls import path
from . import views

app_name = 'planilhas'

urlpatterns = [
    path('', views.ListaAnosView.as_view(), name='lista_anos'),
    path('novo-ano/', views.criar_ano, name='criar_ano'),
    path('<int:ano>/', views.DetalheAnoView.as_view(), name='detalhe_ano'),
    path('<int:ano>/upload/', views.upload_planilha, name='upload_planilha'),
    path(
        'planilha/<int:pk>/',
        views.DetalhePlanilhaView.as_view(),
        name='detalhe_planilha',
    ),
    path(
        'planilha/<int:pk>/editar/',
        views.EditarPlanilhaView.as_view(),
        name='editar_planilha',
    ),
    path(
        'planilha/<int:pk>/deletar/',
        views.DeletarPlanilhaView.as_view(),
        name='deletar_planilha',
    ),
    path(
        'planilha/<int:pk>/download/',
        views.download_planilha,
        name='download_planilha',
    ),
    path(
        '<int:ano>/criar-nativa/',
        views.criar_planilha_nativa,
        name='criar_planilha_nativa',
    ),
    path(
        'planilha-nativa/<int:pk>/editar/',
        views.editar_planilha_nativa,
        name='editar_planilha_nativa',
    ),
    path(
        'planilha-nativa/<int:pk>/deletar/',
        views.DeletarPlanilhaNativaView.as_view(),
        name='deletar_planilha_nativa',
    ),
    path(
        'planilha-nativa/<int:pk>/download/',
        views.download_planilha_nativa,
        name='download_planilha_nativa',
    ),
]
