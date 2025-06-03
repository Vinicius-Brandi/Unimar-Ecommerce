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
from django.db.models import Q  # Importar Q para os filtros da view categoria


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

    @mock.patch("Store.views.mercadopago.SDK")
    def test_webhook_payment_not_found_mp(self, mock_sdk_class):
        """
        Testa o comportamento do webhook quando o Mercado Pago retorna
        um status diferente de 200 (ex: 404) para a requisição de pagamento.
        """
        mock_sdk = mock_sdk_class.return_value
        # Simula o Mercado Pago retornando que o pagamento não foi encontrado (status 404)
        mock_sdk.payment().get.return_value = {
            "status": 404,  # Status que indica "não encontrado" ou outro erro
            "response": {},  # Resposta vazia ou com informações mínimas
        }

        response = self.client.post(
            reverse("mercadopago_webhook"),
            data=json.dumps(
                {"data": {"id": "non_existent_payment"}, "type": "payment"}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content,
            {"status": "error", "message": "Pagamento não encontrado no Mercado Pago"},
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

        # Adicionar itens ao carrinho de diferentes vendedores
        carrinho_usuario, _ = Carrinho.objects.get_or_create(usuario=self.comprador)

        # Produto do vendedor_view (self.vendedor)
        ItemCarrinho.objects.create(
            carrinho=carrinho_usuario, produto=self.produto, quantidade=2
        )
        # Produto de um novo vendedor
        vendedor_2 = User.objects.create_user(username="vendedor_2", password="123")
        categoria_2 = Categoria.objects.create(nome="Livros")
        subcategoria_2 = Subcategoria.objects.create(
            nome="Ficção", categoria_pai=categoria_2
        )

        # Adicionar uma imagem para produto_vendedor_2 para evitar ValueError no template
        image_file_vendedor_2 = SimpleUploadedFile(
            "test_vendedor2.jpg", b"fake_image_data_2", content_type="image/jpeg"
        )

        produto_vendedor_2 = Produto.objects.create(
            vendedor=vendedor_2,
            subcategoria=subcategoria_2,
            nome="Livro A",
            preco=decimal.Decimal("50.00"),
            quantidade=5,
            imagem=image_file_vendedor_2,  # Adicionada imagem aqui
        )
        ItemCarrinho.objects.create(
            carrinho=carrinho_usuario, produto=produto_vendedor_2, quantidade=3
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "carrinho.html")
        self.assertIn("itens_por_vendedor", response.context)

        itens_por_vendedor = response.context["itens_por_vendedor"]

        # Verificar que ambos os vendedores estão presentes
        self.assertIn(self.vendedor, itens_por_vendedor)
        self.assertIn(vendedor_2, itens_por_vendedor)

        # Verificar os itens e subtotal para o primeiro vendedor (self.vendedor)
        self.assertEqual(len(itens_por_vendedor[self.vendedor]["itens"]), 1)
        self.assertEqual(
            itens_por_vendedor[self.vendedor]["subtotal"],
            decimal.Decimal("2400.00"),  # 2 * 1200.00
        )
        self.assertEqual(
            itens_por_vendedor[self.vendedor]["itens"][0].produto.nome, "Monitor Gamer"
        )
        self.assertEqual(itens_por_vendedor[self.vendedor]["itens"][0].quantidade, 2)

        # Verificar os itens e subtotal para o segundo vendedor (vendedor_2)
        self.assertEqual(len(itens_por_vendedor[vendedor_2]["itens"]), 1)
        self.assertEqual(
            itens_por_vendedor[vendedor_2]["subtotal"],
            decimal.Decimal("150.00"),  # 3 * 50.00
        )
        self.assertEqual(
            itens_por_vendedor[vendedor_2]["itens"][0].produto.nome, "Livro A"
        )
        self.assertEqual(itens_por_vendedor[vendedor_2]["itens"][0].quantidade, 3)

        # Verificar o total geral do carrinho
        self.assertIn("total_carrinho", response.context)
        self.assertEqual(
            response.context["total_carrinho"],
            decimal.Decimal("2550.00"),  # 2400.00 + 150.00
        )

    def test_carrinho_view_nao_autenticado(self):
        """
        Testa se a view carrinho redireciona para a página de login
        e adiciona uma mensagem de erro se o usuário não estiver autenticado.
        """
        # Garante que o cliente não esteja logado
        self.client.logout()

        url = reverse("carrinho")
        response = self.client.get(
            url, follow=True
        )  # follow=True para seguir o redirecionamento

        # 1. Verifica se houve um redirecionamento para a página de login
        self.assertRedirects(response, reverse("logar"))

        # 2. Verifica se a mensagem de erro foi adicionada
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Você deve estar logado para acessar o carrinho"
        )
        self.assertEqual(messages[0].tags, "error")

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

    # --- Testes para a view categoria ---

    def test_categoria_view_filtra_por_subcategoria(self):
        """Testa se a view categoria filtra produtos corretamente por subcategoria."""
        # Criar uma nova subcategoria e um produto associado
        categoria_nova = Categoria.objects.create(nome="Esportes")
        subcategoria_nova = Subcategoria.objects.create(
            nome="Futebol", categoria_pai=categoria_nova
        )
        produto_futebol = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=subcategoria_nova,
            nome="Bola de Futebol",
            preco=decimal.Decimal("100.00"),
            quantidade=20,
            imagem=SimpleUploadedFile(
                "bola.jpg", b"fake_image", content_type="image/jpeg"
            ),
        )
        # Produto de outra subcategoria/categoria para garantir que o filtro funciona
        Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=self.subcategoria,  # Subcategoria 'Monitores'
            nome="Teclado",
            preco=decimal.Decimal("200.00"),
            quantidade=15,
            imagem=SimpleUploadedFile(
                "teclado.jpg", b"fake_image", content_type="image/jpeg"
            ),
        )

        url = reverse("categoria", args=["Futebol"])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home-category.html")
        self.assertIn("produtos", response.context)
        self.assertIn("categorias", response.context)

        # Deve conter apenas o produto da subcategoria 'Futebol'
        self.assertEqual(len(response.context["produtos"]), 1)
        self.assertIn(produto_futebol, response.context["produtos"])
        self.assertNotIn(
            self.produto, response.context["produtos"]
        )  # Monitor Gamer é de outra categoria

    def test_categoria_view_filtra_por_categoria_pai(self):
        """Testa se a view categoria filtra produtos corretamente pela categoria pai."""
        # Já temos produtos na self.subcategoria (Monitores) que pertence à self.categoria (View Tests)
        # Vamos adicionar mais um produto na mesma categoria pai, mas em uma subcategoria diferente
        subcategoria_audio = Subcategoria.objects.create(
            nome="Áudio", categoria_pai=self.categoria
        )
        produto_audio = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=subcategoria_audio,
            nome="Fone de Ouvido",
            preco=decimal.Decimal("250.00"),
            quantidade=8,
            imagem=SimpleUploadedFile(
                "fone.jpg", b"fake_image", content_type="image/jpeg"
            ),
        )

        # Vamos criar um produto de outra categoria para garantir que o filtro funciona
        categoria_roupas = Categoria.objects.create(nome="Roupas")
        subcategoria_camisas = Subcategoria.objects.create(
            nome="Camisas", categoria_pai=categoria_roupas
        )
        produto_camisa = Produto.objects.create(
            vendedor=self.vendedor,
            subcategoria=subcategoria_camisas,
            nome="Camisa Casual",
            preco=decimal.Decimal("80.00"),
            quantidade=30,
            imagem=SimpleUploadedFile(
                "camisa.jpg", b"fake_image", content_type="image/jpeg"
            ),
        )

        url = reverse(
            "categoria", args=["View Tests"]
        )  # Filtrando pela categoria pai 'View Tests'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home-category.html")
        self.assertIn("produtos", response.context)
        self.assertIn("categorias", response.context)

        # Deve conter produtos das subcategorias 'Monitores' e 'Áudio', que pertencem a 'View Tests'
        self.assertIn(self.produto, response.context["produtos"])  # Monitor Gamer
        self.assertIn(
            self.produto_webhook, response.context["produtos"]
        )  # Headset (também é da subcategoria Monitores)
        self.assertIn(produto_audio, response.context["produtos"])  # Fone de Ouvido

        # Não deve conter o produto da categoria 'Roupas'
        self.assertNotIn(produto_camisa, response.context["produtos"])

        # Verifica se não há duplicatas (por causa do .distinct())
        self.assertEqual(len(response.context["produtos"]), 3)

    def test_categoria_view_sem_produtos(self):
        """Testa a view categoria quando não há produtos para a categoria/subcategoria."""
        url = reverse("categoria", args=["CategoriaInexistente"])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home-category.html")
        self.assertIn("produtos", response.context)
        self.assertIn("categorias", response.context)
        self.assertEqual(
            len(response.context["produtos"]), 0
        )  # Nenhuma produto encontrado


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

    @mock.patch("Store.views.mercadopago.SDK")
    def test_webhook_status_update_non_approved(self, mock_sdk_class):
        """
        Testa a atualização do status do pedido quando o status do pagamento
        no Mercado Pago é diferente do status atual do pedido e não é 'approved'.
        """
        mock_sdk = mock_sdk_class.return_value
        # Simula um pagamento 'in_process' no Mercado Pago
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {"status": "in_process", "external_reference": self.order_id},
        }

        # Garante que o status inicial do pedido NÃO seja 'in_process'
        self.order.status_pagamento = "pending"
        self.order.save()

        response = self.client.post(
            reverse("mercadopago_webhook"),
            data=json.dumps(
                {"data": {"id": "pagamento_in_process"}, "type": "payment"}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        # Verifica se o status do pedido foi atualizado para 'in_process'
        self.assertEqual(self.order.status_pagamento, "in_process")
        self.assertJSONEqual(response.content, {"status": "ok"})

    @mock.patch("Store.views.mercadopago.SDK")
    def test_webhook_order_does_not_exist(self, mock_sdk_class):
        """
        Testa o comportamento do webhook quando o Order (pedido)
        com o external_reference não é encontrado.
        """
        mock_sdk = mock_sdk_class.return_value
        # Simula um pagamento aprovado, mas com um external_reference inválido
        invalid_order_id = (
            "99999999-9999-9999-9999-999999999999"  # Um UUID que não existe
        )
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {"status": "approved", "external_reference": invalid_order_id},
        }

        response = self.client.post(
            reverse("mercadopago_webhook"),
            data=json.dumps(
                {"data": {"id": "pagamento_inexistente"}, "type": "payment"}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content,
            {
                "status": "error",
                "message": f"Pedido com ID {invalid_order_id} não encontrado",
            },
        )

    @mock.patch("Store.views.mercadopago.SDK")
    def test_webhook_general_exception_handling(self, mock_sdk_class):
        """
        Testa o tratamento de exceções genéricas dentro do webhook.
        """
        mock_sdk = mock_sdk_class.return_value
        # Simula uma exceção genérica ao tentar obter o pagamento
        mock_sdk.payment().get.side_effect = Exception("Erro simulado do Mercado Pago")

        response = self.client.post(
            reverse("mercadopago_webhook"),
            data=json.dumps({"data": {"id": "any_payment_id"}, "type": "payment"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(
            response.content,
            {"status": "error", "message": "Erro interno do servidor"},
        )
