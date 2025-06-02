from django.shortcuts import render, redirect
from .models import Produto
from .models import Produto, Categoria, Carrinho, ItemCarrinho, Order, ItemOrder
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from collections import defaultdict

from apimercadopago import realizar_pagamento
from dotenv import load_dotenv
import os
import mercadopago
from decimal import Decimal

from django.db.models import Q


def home(request):
    produtos = Produto.objects.all()
    categorias = Categoria.objects.all()
    return render(
        request, "home.html", {"produtos": produtos, "categorias": categorias}
    )


def produto(request, id_produto):
    produto = get_object_or_404(Produto, id=id_produto)

    if request.method == "GET":
        return render(request, "produto.html", {"produto": produto})
    elif request.method == "POST":
        if request.user.is_authenticated:
            quantidade = int(request.POST.get("quantidade", 1))
            adicionar_carrinho(request, produto.id, quantidade)
            return render(request, "produto.html", {"produto": produto})
        else:
            messages.error(request, ("Você deve estar logado para acessar o carrinho"))
            return redirect("logar")


def categoria(request, nome_categoria):
    filtro_subcategoria = Q(subcategoria__nome__iexact=nome_categoria)
    filtro_categoria_pai = Q(subcategoria__categoria_pai__nome__iexact=nome_categoria)

    produtos = Produto.objects.filter(
        filtro_subcategoria | filtro_categoria_pai
    ).distinct()

    categorias = Categoria.objects.all()

    return render(
        request, "home-category.html", {"produtos": produtos, "categorias": categorias}
    )


def carrinho(request):
    if not request.user.is_authenticated:
        messages.error(request, ("Você deve estar logado para acessar o carrinho"))
        return redirect("logar")

    try:
        carrinho_usuario = request.user.carrinho
        itens_do_carrinho = carrinho_usuario.itens.all()
    except Carrinho.DoesNotExist:
        itens_do_carrinho = []

    # Se o carrinho estiver vazio
    if not itens_do_carrinho:
        return render(request, "carrinho.html", {"itens_por_vendedor": {}})

    # Agrupando itens e calculando subtotais por vendedor
    itens_por_vendedor = defaultdict(lambda: {"itens": [], "subtotal": Decimal("0.00")})
    for item in itens_do_carrinho:
        vendedor = item.produto.vendedor
        subtotal_item = (
            item.subtotal()
        )  # Usando o método subtotal do modelo ItemCarrinho

        itens_por_vendedor[vendedor]["itens"].append(item)
        itens_por_vendedor[vendedor]["subtotal"] += subtotal_item

    contexto = {
        "usuario": request.user,
        "itens_por_vendedor": dict(itens_por_vendedor),  # Convertendo para dict normal
        "total_carrinho": carrinho_usuario.total(),
    }

    return render(request, "carrinho.html", contexto)


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

    return redirect("carrinho")


def remover_carrinho(request, id_produto):
    produto = Produto.objects.get(id=id_produto)

    carrinho = Carrinho.objects.filter(usuario=request.user).first()
    if not carrinho:
        return redirect("carrinho")

    item = ItemCarrinho.objects.filter(carrinho=carrinho, produto=produto).first()
    if item:
        if item.quantidade > 1:
            item.quantidade -= 1
            item.save()
        else:
            item.delete()

    return redirect("carrinho")


def excluir_carrinho(request, id_produto):
    produto = Produto.objects.get(id=id_produto)

    carrinho = Carrinho.objects.filter(usuario=request.user).first()

    item = ItemCarrinho.objects.filter(carrinho=carrinho, produto=produto).first()
    if item:
        item.delete()
    return redirect("carrinho")


def pagamento(request, vendedor_id):
    vendedor = get_object_or_404(User, id=vendedor_id)
    carrinho = get_object_or_404(Carrinho, usuario=request.user)

    # Pega o token de acesso do vendedor a partir do seu perfil
    seller_token = vendedor.perfil.mp_access_token

    # Verificação crucial: O vendedor tem um token válido?
    if not seller_token:
        messages.error(
            request,
            f"O vendedor '{vendedor.first_name}' não está configurado para receber pagamentos.",
        )
        return redirect("carrinho")

    itens_para_pagar = carrinho.itens.filter(produto__vendedor=vendedor)

    if not itens_para_pagar.exists():
        messages.error(request, "Itens não encontrados no carrinho para este vendedor.")
        return redirect("carrinho")

    MARKETPLACE_FEE_PERCENTAGE = Decimal("0.10")
    payment_items = []
    subtotal_vendedor = Decimal("0.00")

    order = Order.objects.create(vendedor=vendedor, comprador=request.user)

    for item in itens_para_pagar:
        preco_item = Decimal(str(item.produto.preco))
        subtotal_item = item.quantidade * preco_item
        subtotal_vendedor += subtotal_item

        ItemOrder.objects.create(
            order=order,
            produto=item.produto,
            quantidade=item.quantidade,
            preco=preco_item,
        )
        payment_items.append(
            {
                "id": str(item.produto.id),
                "title": item.produto.nome,
                "quantity": item.quantidade,
                "currency_id": "BRL",
                "unit_price": float(preco_item),
            }
        )

    order.valor_total_pedido = subtotal_vendedor
    order.save()

    comissao_total = round(subtotal_vendedor * MARKETPLACE_FEE_PERCENTAGE, 2)
    external_reference = str(order.id)

    # A chamada agora passa o token do vendedor como o primeiro argumento
    link_pagamento = realizar_pagamento(
        seller_token, payment_items, external_reference, comissao_total
    )

    itens_para_pagar.delete()

    return redirect(link_pagamento)


@csrf_exempt
def mercadopago_webhook(request):
    load_dotenv()
    if request.method == "POST":
        data = json.loads(request.body)
        payment_id = data.get("data", {}).get("id")

        if not payment_id:
            return JsonResponse(
                {"status": "error", "message": "ID de pagamento não encontrado"},
                status=400,
            )

        sdk = mercadopago.SDK(f'{os.getenv("MP_ACCESS_TOKEN")}')
        payment_response = sdk.payment().get(payment_id)
        response_data = payment_response["response"]

        payment_status = response_data.get("status")
        external_reference = response_data.get("external_reference")

        if not external_reference:
            return JsonResponse(
                {"status": "error", "message": "Referência externa não encontrada"},
                status=400,
            )

        # Se vários IDs estiverem separados por vírgula
        pedido_ids = external_reference.split(",")
        pedidos = Order.objects.filter(id__in=pedido_ids)

        for pedido in pedidos:
            pedido.status_pagamento = (
                payment_status  # Você precisa ter esse campo no model Order
            )
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
    return render(request, "compra_success.html", {})


def compra_failure(request):
    return render(request, "compra_failure.html", {})


def compra_pending(request):
    return render(request, "compra_pending.html", {})
