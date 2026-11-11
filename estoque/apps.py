from django.apps import AppConfig


class EstoqueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "estoque"

    def ready(self):
        from . import receivers  # noqa: F401
