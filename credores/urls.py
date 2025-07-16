from django.urls import path
from . import views

app_name = 'credores'

urlpatterns = [
    path('', views.CredorListView.as_view(), name='lista'),
    path('credor/<int:pk>/', views.CredorDetailView.as_view(), name='detalhe'),
    path('credor/novo/', views.CredorCreateView.as_view(), name='novo'),
    path(
        'credor/<int:pk>/editar/',
        views.CredorUpdateView.as_view(),
        name='editar',
    ),
    path(
        'credor/<int:pk>/deletar/',
        views.CredorDeleteView.as_view(),
        name='deletar',
    ),
    path(
        'credor/<int:pk>/adicionar-pagamento/',
        views.adicionar_pagamento,
        name='adicionar_pagamento',
    ),
    path(
        'credor/<int:pk>/toggle-status/',
        views.toggle_credor_status,
        name='toggle_status',
    ),
    path(
        'credor/<int:pk>/aplicar-juros/',
        views.aplicar_juros,
        name='aplicar_juros',
    ),
]
