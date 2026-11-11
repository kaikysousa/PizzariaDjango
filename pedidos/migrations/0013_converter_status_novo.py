from django.db import migrations

STATUS_ANTIGO = "novo"
STATUS_NOVO = "aguardando_aprovacao"


def converter_para_aguardando(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    Pedido.objects.filter(status=STATUS_ANTIGO).update(status=STATUS_NOVO)


def converter_para_novo(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    Pedido.objects.filter(status=STATUS_NOVO).update(status=STATUS_ANTIGO)


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0012_pedido_aprovado_em_pedido_aprovado_por_and_more"),
    ]

    operations = [
        migrations.RunPython(
            converter_para_aguardando,
            converter_para_novo,
        ),
    ]
