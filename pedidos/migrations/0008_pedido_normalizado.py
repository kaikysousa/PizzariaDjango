import uuid

import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


def assign_tokens(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    for pedido in Pedido.objects.filter(token__isnull=True):
        pedido.token = uuid.uuid4()
        pedido.save(update_fields=["token"])


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0007_alter_produto_descricao"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pedido",
            old_name="items",
            new_name="legacy_items",
        ),
        migrations.AlterField(
            model_name="pedido",
            name="legacy_items",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="pedido",
            name="token",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.RunPython(assign_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="pedido",
            name="token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="pedido",
            name="telefone",
            field=models.CharField(default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="pedido",
            name="endereco",
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="endereco2",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="observacoes",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="total",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="pedido",
            name="status",
            field=models.CharField(
                choices=[
                    ("novo", "Novo"),
                    ("preparando", "Preparando"),
                    ("saiu", "Saiu para entrega"),
                    ("entregue", "Entregue"),
                    ("cancelado", "Cancelado"),
                ],
                default="novo",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="pagamento",
            field=models.CharField(
                choices=[
                    ("dinheiro", "Dinheiro"),
                    ("pix", "Pix"),
                    ("cartao", "Cartão"),
                ],
                default="dinheiro",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="criado_em",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pedido",
            name="atualizado_em",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="produto",
            name="categoria",
            field=models.CharField(
                choices=[
                    ("pizza", "Pizza"),
                    ("pizza doce", "Pizza doce"),
                    ("bebida", "Bebida"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="produto",
            name="disponivel",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterModelOptions(
            name="pedido",
            options={"ordering": ["-criado_em"]},
        ),
        migrations.AlterModelOptions(
            name="produto",
            options={"ordering": ["categoria", "nome"]},
        ),
        migrations.AddIndex(
            model_name="produto",
            index=models.Index(
                fields=["categoria", "nome"], name="ped_prod_cat_nome_idx"
            ),
        ),
        migrations.CreateModel(
            name="ItemPedido",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantidade", models.PositiveIntegerField()),
                (
                    "preco_unitario",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                (
                    "pedido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens",
                        to="pedidos.pedido",
                    ),
                ),
                (
                    "produto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="itens_pedido",
                        to="pedidos.produto",
                    ),
                ),
                (
                    "segundo_produto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="pedidos.produto",
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
    ]
