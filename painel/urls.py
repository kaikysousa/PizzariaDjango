from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="painel_dashboard"),
    path("pedidos/", views.lista_pedidos, name="painel_pedidos"),
    path("pedidos/novo/", views.pedido_novo, name="painel_pedido_novo"),
    path(
        "pedidos/<int:pk>/",
        views.pedido_detalhe,
        name="painel_pedido_detalhe",
    ),
    path(
        "pedidos/<int:pk>/editar/",
        views.pedido_editar,
        name="painel_pedido_editar",
    ),
    path(
        "pedidos/<int:pk>/acao/",
        views.pedido_acao,
        name="painel_pedido_acao",
    ),
    path("sair/", views.sair, name="painel_sair"),
]
