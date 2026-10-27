from django.conf import settings


def pizzaria(request):
    """Dados operacionais da loja exibidos no rodapé."""
    return {
        "pizzaria": {
            "telefone": settings.PIZZARIA_TELEFONE,
            "endereco": settings.PIZZARIA_ENDERECO,
            "horario": settings.PIZZARIA_HORARIO,
            "cnpj": settings.PIZZARIA_CNPJ,
        }
    }
