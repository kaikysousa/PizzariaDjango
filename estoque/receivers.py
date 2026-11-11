from django.dispatch import receiver

from pedidos.models import Pedido
from pedidos.signals import pedido_itens_alterados, pedido_status_alterado

from .services import consumir_pedido, estornar_pedido, reprocessar_pedido


@receiver(pedido_status_alterado, dispatch_uid="estoque_consumir_aprovado")
def consumir_ao_aprovar(
    sender, instance=None, status_anterior=None, status_novo=None, usuario=None, **kwargs
):
    if status_novo == Pedido.Status.APROVADO:
        consumir_pedido(instance, usuario=usuario)
    elif (
        status_novo == Pedido.Status.CANCELADO
        and status_anterior == Pedido.Status.APROVADO
    ):
        estornar_pedido(instance, usuario=usuario)


@receiver(pedido_itens_alterados, dispatch_uid="estoque_reprocessar_itens")
def reprocessar_itens_alterados(sender, instance=None, usuario=None, **kwargs):
    if instance is not None and instance.status == Pedido.Status.APROVADO:
        reprocessar_pedido(instance, usuario=usuario)
