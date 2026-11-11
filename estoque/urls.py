from django.urls import path

from . import views

app_name = "estoque"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("<int:pk>/ajustar/", views.ajustar, name="ajustar"),
]
