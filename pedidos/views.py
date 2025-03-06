from django.shortcuts import render
from .models import Produto, Pedido
from django.core.paginator import Paginator
from pedidos.models import Pedido
from django import forms
# Create your views here.

def index(request):
    produto_objetos = Produto.objects.all()

    item_name = request.GET.get('item_name')
    if item_name != '' and item_name is not None:
        produto_objetos = produto_objetos.filter(nome__icontains=item_name)

    filtro_pizza = request.GET.get('filtroPizza')
    if filtro_pizza == "pizza":
        produto_objetos = produto_objetos.filter(categoria__icontains="pizza")

    filtro_bebida = request.GET.get('filtroBebida')
    if filtro_bebida == "bebida":
        produto_objetos = produto_objetos.filter(categoria__icontains="bebida")

    filtro_doce = request.GET.get('filtroDoce')
    if filtro_doce == "doce":
        produto_objetos = produto_objetos.filter(categoria__icontains="doce")

    #paginação
    paginator = Paginator(produto_objetos, 4)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    return render(request, 'pedidos/index.html', {'produto_objetos': produto_objetos})

def checkout(request):
    if request.method == 'POST':
        items = request.POST.get('items',"")
        nome = request.POST.get('nome',"")
        endereco = request.POST.get('endereco1',"")
        endereco2 = request.POST.get('endereco2',"")
        observacoes = request.POST.get('observacoes',"")
        total = request.POST.get('total',"")

        pedido = Pedido(items= items, nome=nome, endereco=endereco,endereco2=endereco2,observacoes=observacoes,total=total)
        pedido.save()



    return render(request,'pedidos/checkout.html')