from django.shortcuts import render
from .models import Produto
from django.core.paginator import Paginator
# Create your views here.

def index(request):
    produto_objetos = Produto.objects.all()

    item_name = request.GET.get('item_name')
    if item_name != '' and item_name is not None:
        produto_objetos = produto_objetos.filter(nome__icontains=item_name)

    #paginação
    paginator = Paginator(produto_objetos, 4)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    return render(request, 'pedidos/index.html', {'produto_objetos': produto_objetos})