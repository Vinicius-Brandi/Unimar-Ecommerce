# Store/tests.py

import decimal
from unittest import mock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import (
    Categoria,
    Produto,
    Carrinho,
    ItemCarrinho,
    Order,
    ItemOrder,
    Subcategoria,
)
from Usuario.models import Profile  # Importação do seu modelo Profile

import json
from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.core.files.uploadedfile import SimpleUploadedFile


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
        self.subcategoria = Subcategoria.objects.create(
            nome="Teclados", categoria_pai=self.categoria
        )

        self.produto1 = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=self.subcategoria,
            nome="Teclado",
            preco=decimal.Decimal("150.75"),
            quantidade=10,
        )
        self.produto2 = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=self.subcategoria,
            nome="Mouse",
            preco=decimal.Decimal("50.00"),
            quantidade=5,
        )

    def test_carrinho_e_item_carrinho_subtotal_e_total(self):
        """Testa o cálculo do subtotal do item e o total do carrinho."""
        carrinho, _ = Carrinho.objects.get_or_create(usuario=self.comprador)
        item1 = ItemCarrinho.objects.create(
            carrinho=carrinho, produto=self.produto1, quantidade=2
        )
        item2 = ItemCarrinho.objects.create(
            carrinho=carrinho, produto=self.produto2, quantidade=1
        )

        self.assertEqual(item1.subtotal(), decimal.Decimal("301.50"))
        self.assertEqual(carrinho.total(), decimal.Decimal("351.50"))

    def test_order_calcular_valor_total(self):
        """Testa o cálculo do valor total do pedido (Order)."""
        order = Order.objects.create(vendedor=self.vendedor, comprador=self.comprador)
        ItemOrder.objects.create(
            order=order, produto=self.produto1, quantidade=3, preco=self.produto1.preco
        )
        ItemOrder.objects.create(
            order=order, produto=self.produto2, quantidade=4, preco=self.produto2.preco
        )

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
        # ACESSA E ATUALIZA OS PERFIS JÁ CRIADOS PELO SIGNAL
        # Adicione essas linhas:
        self.vendedor.perfil.mp_access_token = "TEST_ACCESS_TOKEN_FOR_SELLER"
        self.vendedor.perfil.save()
        self.comprador.perfil.mp_access_token = "TEST_ACCESS_TOKEN_FOR_BUYER"
        self.comprador.perfil.save()

        self.categoria = Categoria.objects.create(nome="View Tests")
        self.subcategoria = Subcategoria.objects.create(
            nome="Monitores", categoria_pai=self.categoria
        )

        image_file = SimpleUploadedFile(
            "test.jpg", b"fake_image_data", content_type="image/jpeg"
        )

        self.produto = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=self.subcategoria,
            nome="Monitor Gamer",
            preco=1200.00,
            quantidade=3,
            imagem=image_file,
        )

        image_file_2 = SimpleUploadedFile(
            "test2.jpg", b"fake_image_data", content_type="image/jpeg"
        )
        self.produto_webhook = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=self.subcategoria,
            nome="Headset",
            preco=300.00,
            quantidade=10,
            imagem=image_file_2,
        )
        self.order = Order.objects.create(
            vendedor=self.vendedor, comprador=self.comprador, status_pagamento="pending"
        )
        Carrinho.objects.get_or_create(usuario=self.comprador)
        self.item = ItemOrder.objects.create(
            order=self.order, produto=self.produto_webhook, quantidade=2, preco=300.00
        )
        self.order_id = str(self.order.id)

    def test_add_remover_excluir_carrinho(self):
        """Testa o fluxo completo de manipulação do carrinho via views."""
        self.client.login(username="comprador_view", password="123")

        Carrinho.objects.filter(usuario=self.comprador).delete()
        self.assertFalse(Carrinho.objects.filter(usuario=self.comprador).exists())

        self.client.get(reverse("adicionar_carrinho", args=[self.produto.id, 2]))
        self.assertTrue(Carrinho.objects.filter(usuario=self.comprador).exists())
        carrinho = Carrinho.objects.get(usuario=self.comprador)
        self.assertEqual(carrinho.itens.count(), 1)
        item = carrinho.itens.first()
        self.assertEqual(item.quantidade, 2)
        self.client.get(reverse("remover_carrinho", args=[self.produto.id]))
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 1)
        self.client.get(reverse("excluir_carrinho", args=[self.produto.id]))
        self.assertEqual(carrinho.itens.count(), 0)

    @mock.patch("Store.views.realizar_pagamento")
    def test_view_pagamento_cria_order_corretamente(self, mock_pagamento):
        mock_pagamento.return_value = reverse("compra_success")
        self.client.login(username="comprador_view", password="123")

        carrinho, _ = Carrinho.objects.get_or_create(usuario=self.comprador)
        # Garante que haja itens para o vendedor específico no carrinho
        ItemCarrinho.objects.create(
            carrinho=carrinho, produto=self.produto, quantidade=1
        )

        order_count_before = Order.objects.count()

        response = self.client.get(reverse("pagamento", args=[self.vendedor.id]))

        order_count_after = Order.objects.count()

        self.assertEqual(order_count_after, order_count_before + 1)

        order = Order.objects.last()
        self.assertEqual(order.vendedor, self.vendedor)
        self.assertEqual(order.comprador, self.comprador)
        mock_pagamento.assert_called_once()
        self.assertRedirects(
            response, reverse("compra_success"), fetch_redirect_response=False
        )

    @mock.patch("Store.views.mercadopago.SDK")
    def test_webhook_success_approved(self, mock_sdk_class):
        mock_sdk = mock_sdk_class.return_value
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {"status": "approved", "external_reference": self.order_id},
        }
        response = self.client.post(
            reverse("mercadopago_webhook"),
            data=json.dumps({"data": {"id": "pagamento123"}, "type": "payment"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.produto_webhook.refresh_from_db()
        self.assertEqual(self.order.status_pagamento, "approved")
        self.assertEqual(self.produto_webhook.quantidade, 8)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_webhook_sem_payment_id(self):
        response = self.client.post(
            reverse("mercadopago_webhook"),
            data=json.dumps({"data": {}, "type": "payment"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {"status": "error", "message": "ID de pagamento não encontrado"},
        )

    def test_compra_success_view(self):
        response = self.client.get(reverse("compra_success"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "compra_success.html")

    def test_compra_failure_view(self):
        response = self.client.get(reverse("compra_failure"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "compra_failure.html")

    def test_compra_pending_view(self):
        response = self.client.get(reverse("compra_pending"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "compra_pending.html")

    def test_produto_view_get(self):
        url = reverse("pagina_produto", args=[self.produto.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "produto.html")
        self.assertIn("produto", response.context)
        self.assertEqual(response.context["produto"], self.produto)

    def test_produto_view_post_autenticado(self):
        self.client.login(username="comprador_view", password="123")
        url = reverse("pagina_produto", args=[self.produto.id])
        response = self.client.post(url, {"quantidade": 2})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "produto.html")
        carrinho = Carrinho.objects.get(usuario=self.comprador)
        item = carrinho.itens.first()
        self.assertEqual(item.produto, self.produto)
        self.assertEqual(item.quantidade, 2)

    def test_produto_view_post_nao_autenticado(self):
        url = reverse("pagina_produto", args=[self.produto.id])
        response = self.client.post(url, {"quantidade": 1})
        self.assertRedirects(response, reverse("logar"))

    def test_carrinho_view_autenticado(self):
        self.client.login(username="comprador_view", password="123")
        url = reverse("carrinho")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "carrinho.html")
        self.assertIn("itens_por_vendedor", response.context)

    def test_carrinho_view_nao_autenticado(self):
        url = reverse("carrinho")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("logar"))

    def test_home_view(self):
        """Testa se a view home retorna status 200, usa o template correto e lista os produtos."""
        url = reverse("home")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertIn("produtos", response.context)
        self.assertIn(self.produto, response.context["produtos"])

    def test_adicionar_carrinho_quantidade_maior_que_estoque(self):
        """Testa adicionar ao carrinho mais unidades do que o estoque disponível."""
        self.client.login(username="comprador_view", password="123")

        carrinho, _ = Carrinho.objects.get_or_create(usuario=self.comprador)
        carrinho.itens.all().delete()

        url = reverse("adicionar_carrinho", args=[self.produto.id, 10])
        self.client.get(url)

        carrinho.refresh_from_db()
        item = carrinho.itens.first()

        self.assertEqual(item.quantidade, self.produto.quantidade)

    def test_remover_carrinho_sem_carrinho_existente(self):
        """Testa se a view redireciona corretamente quando não há carrinho."""
        self.client.login(username="comprador_view", password="123")

        Carrinho.objects.filter(usuario=self.comprador).delete()

        response = self.client.get(reverse("remover_carrinho", args=[self.produto.id]))
        self.assertRedirects(response, reverse("carrinho"))

    def test_remover_carrinho_quantidade_igual_a_um(self):
        """Testa a remoção direta de item quando a quantidade é 1."""
        self.client.login(username="comprador_view", password="123")

        carrinho, _ = Carrinho.objects.get_or_create(usuario=self.comprador)
        carrinho.itens.all().delete()

        ItemCarrinho.objects.create(
            carrinho=carrinho, produto=self.produto, quantidade=1
        )

        self.client.get(reverse("remover_carrinho", args=[self.produto.id]))

        carrinho.refresh_from_db()
        self.assertEqual(carrinho.itens.count(), 0)


class WebhookTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.vendedor = User.objects.create_user(
            username="vendedor_webhook", password="123"
        )
        self.comprador = User.objects.create_user(
            username="comprador_webhook", password="123"
        )
        # ACESSA E ATUALIZA OS PERFIS JÁ CRIADOS PELO SIGNAL
        # Adicione essas linhas:
        self.vendedor.perfil.mp_access_token = "TEST_ACCESS_TOKEN_FOR_SELLER_WEBHOOK"
        self.vendedor.perfil.save()
        self.comprador.perfil.mp_access_token = "TEST_ACCESS_TOKEN_FOR_BUYER_WEBHOOK"
        self.comprador.perfil.save()

        self.categoria = Categoria.objects.create(nome="Webhook Test Category")
        self.subcategoria = Subcategoria.objects.create(
            nome="Webhook Subcategory", categoria_pai=self.categoria
        )
        self.produto_webhook = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=self.subcategoria,
            nome="Produto Webhook",
            preco=100.00,
            quantidade=5,
            imagem=SimpleUploadedFile(
                "webhook_test.jpg", b"fake_data", content_type="image/jpeg"
            ),
        )
        self.order = Order.objects.create(
            vendedor=self.vendedor, comprador=self.comprador, status_pagamento="pending"
        )
        Carrinho.objects.get_or_create(usuario=self.comprador)
        ItemOrder.objects.create(
            order=self.order, produto=self.produto_webhook, quantidade=2, preco=100.00
        )
        self.order_id = str(self.order.id)

    @mock.patch("Store.views.mercadopago.SDK")
    def test_webhook_sem_external_reference(self, mock_sdk_class):
        """Garante que a ausência de external_reference é tratada corretamente."""
        mock_sdk = mock_sdk_class.return_value
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {
                "status": "approved",
            },
        }

        response = self.client.post(
            reverse("mercadopago_webhook"),
            data=json.dumps({"data": {"id": "123"}, "type": "payment"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {"status": "error", "message": "Referência externa não encontrada"},
        )
