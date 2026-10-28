from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from pedidos import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("carrinho/revisar/", views.revisar_pedido, name="revisar_pedido"),
    path("checkout/", views.checkout, name="checkout"),
    path("pedido/<uuid:token>/recibo/", views.recibo, name="recibo"),
]

if settings.DEBUG:
    urlpatterns += [path("carrinho.json", views.carrinho_json, name="carrinho_json")]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
