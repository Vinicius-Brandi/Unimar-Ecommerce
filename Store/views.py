from django.shortcuts import render, redirect
from .models import Produto
from .models import Produto, Categoria, Carrinho, ItemCarrinho, Order, ItemOrder
from django.shortcuts import get_object_or_404
from django.contrib import messages

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from collections import defaultdict

from apimercadopago import realizar_pagamento
from dotenv import load_dotenv
import os
import mercadopago
from decimal import Decimal

def home(request):
    produtos = Produto.objects.all()
    return render(request, 'home.html', {'produtos':produtos})

def produto(request, id_produto):
    produto = get_object_or_404(Produto, id=id_produto)

    if request.method == "GET":
        return render(request, 'produto.html', {'produto':produto})
    elif request.method == "POST":
        if request.user.is_authenticated:
            quantidade = int(request.POST.get('quantidade', 1))
            adicionar_carrinho(request, produto.id, quantidade)
            return render(request, 'produto.html', {'produto':produto})
        else:
            messages.error(request, ("Você deve estar logado para acessar o carrinho"))
            return redirect('logar')

def carrinho(request):
    if request.user.is_authenticated:
        return render(request, 'carrinho.html', {'usuario':request.user})
    else:
        messages.error(request, ("Você deve estar logado para acessar o carrinho"))
        return redirect('logar')
    
def adicionar_carrinho(request, id_produto, quantidade):
    produto = Produto.objects.get(id=id_produto)
    carrinho, criou = Carrinho.objects.get_or_create(usuario=request.user)
    item, criou = ItemCarrinho.objects.get_or_create(carrinho=carrinho, produto=produto)
    
    if item.quantidade + quantidade <= produto.quantidade:
        item.quantidade += quantidade
        item.save()
    else:
        item.quantidade = produto.quantidade
        item.save()

    return redirect('carrinho')

def remover_carrinho(request, id_produto):
    produto = Produto.objects.get(id=id_produto)

    carrinho = Carrinho.objects.filter(usuario=request.user).first()
    if not carrinho:
        return redirect('carrinho')
    
    item = ItemCarrinho.objects.filter(carrinho=carrinho, produto=produto).first()
    if item:
        if item.quantidade > 1:
            item.quantidade -= 1
            item.save()
        else:
            item.delete()

    return redirect('carrinho')

def excluir_carrinho(request, id_produto):
    produto = Produto.objects.get(id=id_produto)

    carrinho = Carrinho.objects.filter(usuario=request.user).first()
    
    item = ItemCarrinho.objects.filter(carrinho=carrinho, produto=produto).first()
    if item:
        item.delete()
    return redirect('carrinho')

def pagamento(request):
    carrinho = Carrinho.objects.filter(usuario=request.user).first()
    if not carrinho or not carrinho.itens.exists():
        messages.error(request, "Seu carrinho está vazio.")
        return redirect('carrinho')
        
    # Defina a porcentagem da sua comissão (ex: 10%)
    MARKETPLACE_FEE_PERCENTAGE = Decimal('0.10')

    itens_por_vendedor = defaultdict(list)
    for item in carrinho.itens.all():
        # Verificação importante: o vendedor conectou a conta?
        if not item.produto.vendedor.perfil.mp_connected:
            messages.error(request, f"O vendedor do produto '{item.produto.nome}' ainda não configurou uma forma de recebimento. O item foi removido do seu carrinho.")
            item.delete() # Remove o item problemático
            return redirect('carrinho')
        itens_por_vendedor[item.produto.vendedor].append(item)

    payment_items = []
    pedidos_criados = []
    total_comissao = Decimal('0.00')

    for vendedor, itens in itens_por_vendedor.items():
        subtotal_vendedor = Decimal('0.00')
        order = Order.objects.create(
            vendedor=vendedor,
            comprador=request.user
        )

        for item in itens:
            ItemOrder.objects.create(
                order=order,
                produto=item.produto,
                quantidade=item.quantidade,
                preco=item.produto.preco
            )
            
            preco_item = Decimal(str(item.produto.preco))
            subtotal_item = item.quantidade * preco_item
            subtotal_vendedor += subtotal_item

            payment_items.append({
                "id": str(item.produto.id),
                "title": item.produto.nome,
                "quantity": item.quantidade,
                "currency_id": "BRL",
                "unit_price": float(preco_item)
            })

        # Atualiza o valor total do pedido
        order.valor_total_pedido = subtotal_vendedor
        order.save()
        pedidos_criados.append(order)

        # Calcula a comissão para os itens deste vendedor e adiciona ao total
        total_comissao += subtotal_vendedor * MARKETPLACE_FEE_PERCENTAGE

    # Garante que a comissão tenha no máximo 2 casas decimais
    total_comissao = round(total_comissao, 2)

    if not payment_items:
        messages.error(request, "Não foi possível processar os itens do carrinho.")
        return redirect('carrinho')

    pedido_ids = [str(pedido.id) for pedido in pedidos_criados]
    external_reference = ",".join(pedido_ids)

    # Passa a lista de itens, a referência e a comissão calculada
    link_pagamento = realizar_pagamento(payment_items, external_reference, total_comissao)
    
    request.session['pedidos_ids'] = pedido_ids

    # Limpa o carrinho após gerar o link de pagamento
    carrinho.delete()

    return redirect(link_pagamento)

@csrf_exempt
def mercadopago_webhook(request):
    load_dotenv()
    if request.method == 'POST':
        data = json.loads(request.body)
        payment_id = data.get("data", {}).get("id")

        if not payment_id:
            return JsonResponse({"status": "error", "message": "ID de pagamento não encontrado"}, status=400)

        sdk = mercadopago.SDK(f'{os.getenv("MP_ACCESS_TOKEN")}')
        payment_response = sdk.payment().get(payment_id)
        response_data = payment_response["response"]

        payment_status = response_data.get("status")
        external_reference = response_data.get("external_reference")

        if not external_reference:
            return JsonResponse({"status": "error", "message": "Referência externa não encontrada"}, status=400)

        # Se vários IDs estiverem separados por vírgula
        pedido_ids = external_reference.split(",")
        pedidos = Order.objects.filter(id__in=pedido_ids)

        for pedido in pedidos:
            pedido.status_pagamento = payment_status  # Você precisa ter esse campo no model Order
            pedido.save()

            # Exemplo: Atualizar estoque apenas se for aprovado
            if payment_status == "approved":
                for pedido_id in pedido_ids:
                    try:
                        pedido = Order.objects.get(id=pedido_id)

                        # Verifica se o pedido já foi aprovado
                        if pedido.status_pagamento != "approved":
                            pedido.status_pagamento = "approved"
                            pedido.save()

                            for item in pedido.itens.all():
                                item.produto.quantidade -= item.quantidade
                                item.produto.save()
                    except:
                        print("boa")

        return JsonResponse({"status": "ok"})

def compra_success(request):
    return render(request, 'compra_success.html', {})


def compra_failure(request):
    return render(request, 'compra_failure.html', {})

def compra_pending(request):
    return render(request, 'compra_pending.html', {})