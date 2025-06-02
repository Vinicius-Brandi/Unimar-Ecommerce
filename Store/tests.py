# Store/tests.py

import decimal
from unittest import mock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Categoria, Produto, Carrinho, ItemCarrinho, Order, ItemOrder


class StoreModelsTest(TestCase):
    """Testa os modelos do app Store."""

    def setUp(self):
        self.vendedor = User.objects.create_user(
            username="vendedor_test", password="123"
        )
        self.comprador = User.objects.create_user(
            username="comprador_test", password="123"
        )
        self.categoria = Categoria.objects.create(nome="Eletrônicos")
        self.produto1 = Produto.objects.create(
            vendedor=self.vendedor,
            categoria=self.categoria,
            nome="Teclado",
            preco=decimal.Decimal("150.75"),
            quantidade=10,
        )
        self.produto2 = Produto.objects.create(
            vendedor=self.vendedor,
            categoria=self.categoria,
            nome="Mouse",
            preco=decimal.Decimal("50.00"),
            quantidade=5,
        )

    def test_carrinho_e_item_carrinho_subtotal_e_total(self):
        """Testa o cálculo do subtotal do item e o total do carrinho."""
        carrinho = Carrinho.objects.create(usuario=self.comprador)
        item1 = ItemCarrinho.objects.create(
            carrinho=carrinho, produto=self.produto1, quantidade=2
        )
        item2 = ItemCarrinho.objects.create(
            carrinho=carrinho, produto=self.produto2, quantidade=1
        )

        # Testa o subtotal de um item
        self.assertEqual(item1.subtotal(), decimal.Decimal("301.50"))

        # Testa o total do carrinho
        self.assertEqual(carrinho.total(), decimal.Decimal("351.50"))

    def test_order_calcular_valor_total(self):
        """Testa o cálculo do valor total do pedido (Order)."""
        order = Order.objects.create(vendedor=self.vendedor, comprador=self.comprador)
        ItemOrder.objects.create(
            order=order, produto=self.produto1, quantidade=3, preco=self.produto1.preco
        )  # 3 * 150.75 = 452.25
        ItemOrder.objects.create(
            order=order, produto=self.produto2, quantidade=4, preco=self.produto2.preco
        )  # 4 * 50.00 = 200.00

        # Total esperado: 452.25 + 200.00 = 652.25
        self.assertEqual(order.calcular_valor_total, decimal.Decimal("652.25"))


class StoreViewsTest(TestCase):
    """Testa as views do app Store."""

    def setUp(self):
        self.client = Client()
        self.vendedor = User.objects.create_user(
            username="vendedor_view", password="123"
        )
        self.comprador = User.objects.create_user(
            username="comprador_view", password="123"
        )
        self.categoria = Categoria.objects.create(nome="View Tests")
        self.produto = Produto.objects.create(
            vendedor=self.vendedor,
            categoria=self.categoria,
            nome="Monitor Gamer",
            preco=1200.00,
            quantidade=3,
        )

    def test_adicionar_remover_excluir_do_carrinho(self):
        """Testa o fluxo completo de manipulação do carrinho via views."""
        self.client.login(username="comprador_view", password="123")

        # Usuário não tem carrinho ainda
        self.assertFalse(Carrinho.objects.filter(usuario=self.comprador).exists())

        # Adiciona 2 monitores ao carrinho - A view deve criar o carrinho e o item
        self.client.get(reverse("adicionar_carrinho", args=[self.produto.id, 2]))

        self.assertTrue(Carrinho.objects.filter(usuario=self.comprador).exists())
        carrinho = Carrinho.objects.get(usuario=self.comprador)
        self.assertEqual(carrinho.itens.count(), 1)
        item = carrinho.itens.first()
        self.assertEqual(item.quantidade, 2)

        # Remove 1 monitor
        self.client.get(reverse("remover_carrinho", args=[self.produto.id]))
        item.refresh_from_db()  # Recarrega o item do banco de dados
        self.assertEqual(item.quantidade, 1)

        # Exclui o item
        self.client.get(reverse("excluir_carrinho", args=[self.produto.id]))
        self.assertEqual(carrinho.itens.count(), 0)

    @mock.patch("Store.views.realizar_pagamento")
    def test_view_pagamento_cria_order_corretamente(self, mock_pagamento):
        """Testa se a view de pagamento cria o pedido e chama a API externa."""
        # Simula que a API externa retornará um redirecionamento para a pág. de sucesso
        mock_pagamento.return_value = reverse("compra_success")

        self.client.login(username="comprador_view", password="123")
        carrinho = Carrinho.objects.create(usuario=self.comprador)
        ItemCarrinho.objects.create(
            carrinho=carrinho, produto=self.produto, quantidade=1
        )

        # Garante que não existem pedidos antes de chamar a view
        self.assertEqual(Order.objects.count(), 0)

        # Chama a view de pagamento
        url = reverse("pagamento")
        response = self.client.get(url)

        # Verifica se o pedido foi criado
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.vendedor, self.vendedor)
        self.assertEqual(order.comprador, self.comprador)

        # Verifica se a API de pagamento foi chamada
        mock_pagamento.assert_called_once()

        # Verifica se o cliente é redirecionado corretamente
        self.assertRedirects(
            response, reverse("compra_success"), fetch_redirect_response=False
        )
