from django.shortcuts import render
from .models import Produto
# Create your views here.

def index(request):
    produto_objetos = Produto.objects.all()

    item_name = request.GET.get('item_name')
    if item_name != '' and item_name is not None:
        produto_objetos = produto_objetos.filter(nome__icontains=item_name)
    return render(request, 'pedidos/index.html', {'produto_objetos': produto_objetos})