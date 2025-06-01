from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.contrib.auth import logout
import os
from .models import Profile
from Store.models import Order, Solicitacao_Vendedor
from Usuario.models import Profile
from . import views

class CadastrarViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.cadastrar_url = reverse('cadastrar') 

    def test_cadastrar_get(self):
        """Testa se a requisição GET renderiza o template correto."""
        response = self.client.get(self.cadastrar_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cadastrar.html')

    def test_cadastrar_post_senhas_diferentes(self):
        """Testa o POST com senhas diferentes."""
        response = self.client.post(self.cadastrar_url, {
            'usuario': 'teste',
            'nome': 'Teste User',
            'senha1': 'senha1',
            'senha2': 'senha2_errada'
        }, follow=True) 
        self.assertEqual(response.status_code, 200) 
        self.assertTemplateUsed(response, 'cadastrar.html') 

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Senhas diferentes! tente novamente!")
        self.assertFalse(User.objects.filter(username='teste').exists())

    def test_cadastrar_post_usuario_existente(self):
        """Testa o POST com um usuário já existente."""
        User.objects.create_user(username='existente', password='senha')
        response = self.client.post(self.cadastrar_url, { 
            'usuario': 'existente',
            'nome': 'Outro User',
            'senha1': 'outrasenha',
            'senha2': 'outrasenha'
        }, follow=True) 
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cadastrar.html')
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "O username já está cadastrado, tente novamente!")
        self.assertEqual(User.objects.filter(username='existente').count(), 1)


    def test_cadastrar_post_sucesso(self):
        """Testa o POST com dados válidos."""
        cadastrar_url = reverse('cadastrar')
        logar_url = reverse('logar') 

        response = self.client.post(cadastrar_url, {
            'usuario': 'novo_usuario',
            'nome': 'Novo Usuário',
            'senha1': 'senha_correta',
            'senha2': 'senha_correta'
        }, follow=True)
        self.assertRedirects(response, logar_url) 

        self.assertTrue(User.objects.filter(username='novo_usuario').exists())
        novo_usuario = User.objects.get(username='novo_usuario')
        self.assertEqual(novo_usuario.first_name, 'Novo Usuário')
        self.assertTrue(novo_usuario.check_password('senha_correta'))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Cadastrado com sucesso! Faça seu login!")


class LogarViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.logar_url = reverse('logar')
        self.home_url = reverse('home') 
        self.user = User.objects.create_user(username='testuser', password='testpassword')

    def test_logar_get(self):
        """Testa se a requisição GET renderiza o template correto."""
        response = self.client.get(self.logar_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'logar.html')

    def test_logar_post_credenciais_corretas(self):
        """Testa o POST com credenciais corretas."""
        response = self.client.post(self.logar_url, {
            'usuario': 'testuser',
            'senha': 'testpassword'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.home_url)
        self.assertTrue('_auth_user_id' in self.client.session) 

    def test_logar_post_credenciais_incorretas_usuario(self):
        """Testa o POST com usuário incorreto."""
        response = self.client.post(self.logar_url, {
            'usuario': 'wronguser',
            'senha': 'testpassword'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'logar.html')
        self.assertFalse('_auth_user_id' in self.client.session) 
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Usuario ou senha incorreto, tente novamente!")

    def test_logar_post_credenciais_incorretas_senha(self):
        """Testa o POST com senha incorreta."""
        response = self.client.post(self.logar_url, {
            'usuario': 'testuser',
            'senha': 'wrongpassword'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'logar.html')
        self.assertFalse('_auth_user_id' in self.client.session) 
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Usuario ou senha incorreto, tente novamente!")

    def test_logar_post_campos_vazios(self):
        """Testa o POST com campos vazios."""
        response = self.client.post(self.logar_url, {
            'usuario': '',
            'senha': ''
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'logar.html')
        self.assertFalse('_auth_user_id' in self.client.session)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Usuario ou senha incorreto, tente novamente!")


class DeslogarViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.deslogar_url = reverse('deslogar')
        self.home_url = reverse('home') 
        self.user = User.objects.create_user(username='testuser', password='testpassword')

    def test_deslogar_usuario_logado(self):
        """Testa deslogar um usuário que está logado."""
        self.client.login(username='testuser', password='testpassword')
        self.assertTrue('_auth_user_id' in self.client.session)

        response = self.client.get(self.deslogar_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.home_url)
        self.assertFalse('_auth_user_id' in self.client.session) 

    def test_deslogar_usuario_nao_logado(self):
        """Testa deslogar quando nenhum usuário está logado."""
        self.assertFalse('_auth_user_id' in self.client.session)

        response = self.client.get(self.deslogar_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.home_url)
        self.assertFalse('_auth_user_id' in self.client.session) 

    def test_deslogar_via_post(self):
        """Testa deslogar via requisição POST (embora geralmente seja GET)."""
        self.client.login(username='testuser', password='testpassword')
        self.assertTrue('_auth_user_id' in self.client.session)

        response = self.client.post(self.deslogar_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.home_url)
        self.assertFalse('_auth_user_id' in self.client.session)


class SolicitarVendedorViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.solicitar_vendedor_url = reverse('solicitar_vendedor') 

    def test_solicitar_vendedor_get(self):
        self.client.login(username='testuser', password='testpassword') 
        response = self.client.get(self.solicitar_vendedor_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'solicitar_vendedor.html')

    def test_solicitar_vendedor_post_nova_solicitacao(self):
        self.client.login(username='testuser', password='testpassword')
        post_data = {
            'nome-completo': 'Nome Completo Teste',
            'cpf': '123.456.789-00',
            'produtos-a-vender': 'Produtos de teste para vender',
        }
        response = self.client.post(self.solicitar_vendedor_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Solicitado com sucesso, aguarde até darmos uma resposta!", [m.message for m in messages.get_messages(response.wsgi_request)])
        self.assertEqual(Solicitacao_Vendedor.objects.count(), 1)
        solicitacao = Solicitacao_Vendedor.objects.first()
        self.assertEqual(solicitacao.usuario, self.user)
        self.assertEqual(solicitacao.nome_completo, 'Nome Completo Teste')
        self.assertEqual(solicitacao.cpf, '123.456.789-00')
        self.assertEqual(solicitacao.descricao, 'Produtos de teste para vender')
        self.assertRedirects(response, reverse('home'))

    def test_solicitar_vendedor_post_solicitacao_existente(self):
        Solicitacao_Vendedor.objects.create(usuario=self.user, nome_completo='Existente', cpf='...', descricao='...')
        self.client.login(username='testuser', password='testpassword')
        post_data = {
            'nome-completo': 'Outro Nome',
            'cpf': '999.999.999-99',
            'produtos-a-vender': 'Outros produtos',
        }
        response = self.client.post(self.solicitar_vendedor_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Você ja mandou solicitação! Aguarde a verificação!", [m.message for m in messages.get_messages(response.wsgi_request)])
        self.assertEqual(Solicitacao_Vendedor.objects.count(), 1) 
        existing_solicitacao = Solicitacao_Vendedor.objects.first()
        self.assertEqual(existing_solicitacao.usuario, self.user)
        self.assertEqual(existing_solicitacao.nome_completo, 'Existente')
        self.assertRedirects(response, reverse('home'))



class VerSolicitacaoViewTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpassword', email='admin@example.com')
        self.regular_user = User.objects.create_user(username='testuser', password='testpassword')
        self.solicitacao1 = Solicitacao_Vendedor.objects.create(usuario=self.regular_user, nome_completo='Solicitante 1', cpf='111', descricao='A')
        self.ver_solicitacao_url = reverse('ver_solicitacao')
        self.aceitar_solicitacao_url = reverse('aceitar_solicitacao', kwargs={'username': self.regular_user.username})
        self.recusar_solicitacao_url = reverse('recusar_solicitacao', kwargs={'username': self.regular_user.username})

    def test_ver_solicitacao_get_admin_logado(self):
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(self.ver_solicitacao_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ver_solicitacao.html')
        self.assertIn('solicitacoes', response.context)
        self.assertEqual(len(response.context['solicitacoes']), 1)
        self.assertEqual(response.context['solicitacoes'][0].usuario.username, 'testuser')

    def test_ver_solicitacao_get_usuario_nao_admin(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.ver_solicitacao_url)
        self.assertNotEqual(response.status_code, 200) 

  
class AceitarSolicitacaoViewTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpassword', email='admin@example.com')
        self.regular_user = User.objects.create_user(username='testuser', password='testpassword')
        Solicitacao_Vendedor.objects.create(usuario=self.regular_user, nome_completo='Solicitante', cpf='...', descricao='...')
        # Certifique-se que o Perfil seja criado automaticamente ou crie um aqui
        try:
            self.regular_user.perfil
        except  Profile.DoesNotExist:
             Profile.objects.create(usuario=self.regular_user)
        self.aceitar_solicitacao_url = reverse('aceitar_solicitacao', kwargs={'username': self.regular_user.username})
        self.ver_solicitacao_url = reverse('ver_solicitacao')

    def test_aceitar_solicitacao_admin_logado(self):
        self.client.login(username='admin', password='adminpassword')
        self.assertFalse(self.regular_user.perfil.vendedor)
        response = self.client.get(self.aceitar_solicitacao_url, follow=True)
        self.assertTrue(User.objects.get(username='testuser').perfil.vendedor)
        self.assertFalse(Solicitacao_Vendedor.objects.filter(usuario=self.regular_user).exists())
        self.assertRedirects(response, self.ver_solicitacao_url)

    def test_aceitar_solicitacao_usuario_nao_admin(self):
        self.client.login(username='testuser', password='testpassword')
        self.assertFalse(self.regular_user.perfil.vendedor)
        response = self.client.get(self.aceitar_solicitacao_url)
        self.assertEqual(response.status_code, 302) 
        self.assertFalse(User.objects.get(username='testuser').perfil.vendedor)
        self.assertTrue(Solicitacao_Vendedor.objects.filter(usuario=self.regular_user).exists())

    def test_aceitar_solicitacao_usuario_nao_logado(self):
        self.assertFalse(self.regular_user.perfil.vendedor)
        response = self.client.get(self.aceitar_solicitacao_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.get(username='testuser').perfil.vendedor)
        self.assertTrue(Solicitacao_Vendedor.objects.filter(usuario=self.regular_user).exists())


class RecusarSolicitacaoViewTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpassword', email='admin@example.com')
        self.regular_user = User.objects.create_user(username='testuser', password='testpassword')
        Solicitacao_Vendedor.objects.create(usuario=self.regular_user, nome_completo='Solicitante', cpf='...', descricao='...')
        # Certifique-se que o Perfil seja criado automaticamente ou crie um aqui
        try:
            self.regular_user.perfil
        except  Profile.DoesNotExist:
             Profile.objects.create(usuario=self.regular_user)
        self.recusar_solicitacao_url = reverse('recusar_solicitacao', kwargs={'username': self.regular_user.username})
        self.ver_solicitacao_url = reverse('ver_solicitacao')

    def test_recusar_solicitacao_admin_logado(self):
        self.client.login(username='admin', password='adminpassword')
        self.assertFalse(self.regular_user.perfil.vendedor) 
        response = self.client.get(self.recusar_solicitacao_url, follow=True)
        self.assertFalse(User.objects.get(username='testuser').perfil.vendedor) 
        self.assertFalse(Solicitacao_Vendedor.objects.filter(usuario=self.regular_user).exists()) 
        self.assertRedirects(response, self.ver_solicitacao_url)

    def test_recusar_solicitacao_usuario_nao_admin(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.recusar_solicitacao_url)
        self.assertEqual(response.status_code, 302) 
        self.assertFalse(User.objects.get(username='testuser').perfil.vendedor)
        self.assertTrue(Solicitacao_Vendedor.objects.filter(usuario=self.regular_user).exists())

    def test_recusar_solicitacao_usuario_nao_logado(self):
        response = self.client.get(self.recusar_solicitacao_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.get(username='testuser').perfil.vendedor)
        self.assertTrue(Solicitacao_Vendedor.objects.filter(usuario=self.regular_user).exists())
     

class PerfilViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword', first_name='Test', last_name='User')
        self.perfil_url = reverse('perfil_user', kwargs={'username': 'testuser'})

    def test_perfil_get_usuario_existente(self):
        """Testa se a requisição GET renderiza o template correto com um usuário existente."""
        response = self.client.get(self.perfil_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'perfil_usuario.html')
        self.assertEqual(response.context['usuario'], self.user)


class EditarPerfilViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword', first_name='Test')
        try:
            self.profile = Profile.objects.get(usuario=self.user)
        except Profile.DoesNotExist:
            self.profile = Profile.objects.create(usuario=self.user)

        other_username = f'otheruser_{self._testMethodName}'
        self.other_user = User.objects.create_user(username=other_username, password='otherpassword')
        try:
            self.other_profile = Profile.objects.get(usuario=self.other_user)
        except Profile.DoesNotExist:
            self.other_profile = Profile.objects.create(usuario=self.other_user)

        self.editar_perfil_url = reverse('editar_perfil', kwargs={'username': 'testuser'})
        self.perfil_user_url = reverse('perfil_user', kwargs={'username': 'testuser'})
        self.home_url = reverse('home')
        self.client.force_login(self.user)

    def test_editar_perfil_get_usuario_logado_proprio_perfil(self):
        """Testa se GET renderiza o formulário de edição para o próprio usuário logado."""
        response = self.client.get(self.editar_perfil_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'editar_perfil.html')
        self.assertEqual(response.context['usuario'], self.user)


    def test_editar_perfil_post_salvar_nome_bios(self):
        """Testa o POST para salvar nome e bios."""
        post_data = {
            'salvar': 'Salvar',
            'nome': 'Novo Nome',
            'bios': 'Nova biografia'
        }
        response = self.client.post(self.editar_perfil_url, post_data, follow=True)
        self.assertRedirects(response, self.perfil_user_url)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Novo Nome')
        self.assertEqual(self.profile.bios, 'Nova biografia')

    def test_editar_perfil_post_salvar_foto(self):
        """Testa o POST para salvar a foto de perfil."""
        imagem = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        post_data = {
            'salvar': 'Salvar',
            'nome': self.user.first_name,
            'bios': self.profile.bios,
            'foto_perfil': imagem
        }
        response = self.client.post(self.editar_perfil_url, post_data, follow=True)
        self.assertRedirects(response, self.perfil_user_url)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.foto.name.startswith('uploads/fotos_perfil/'))
        # Limpar a imagem salva para não poluir os testes futuros
        if self.profile.foto and os.path.isfile(self.profile.foto.path):
            os.remove(self.profile.foto.path)

    def test_editar_perfil_post_excluir_conta(self):
        """Testa o POST para excluir a conta do usuário."""
        response = self.client.post(self.editar_perfil_url, {'excluir': 'Excluir'}, follow=True)
        self.assertRedirects(response, self.home_url)
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username='testuser')
        self.assertFalse('_auth_user_id' in self.client.session) 

    def test_editar_perfil_get_usuario_nao_logado(self):
        """Testa se GET redireciona para login se o usuário não estiver logado."""
        self.client.logout()
        response = self.client.get(self.editar_perfil_url, follow=False)
        self.assertEqual(response.status_code, 302) 

    def test_editar_perfil_post_salvar_sem_alteracoes(self):
        """Testa o POST para salvar sem alterações."""
        post_data = {
            'salvar': 'Salvar',
            'nome': self.user.first_name,
            'bios': self.profile.bios,
        }
        response = self.client.post(self.editar_perfil_url, post_data, follow=True)
        self.assertRedirects(response, self.perfil_user_url)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test') 
        self.assertEqual(self.profile.bios, 'Olá, este é o meu Perfil!') 


class ListaProdutosViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.other_user = User.objects.create_user(username='otheruser', password='otherpassword')
        self.lista_produtos_url_self = reverse('lista_produtos', kwargs={'username': 'testuser'})
        self.lista_produtos_url_other = reverse('lista_produtos', kwargs={'username': 'otheruser'})
        self.home_url = reverse('home')
        self.client.force_login(self.user)

    def test_lista_produtos_get_proprio_usuario_logado(self):
        """Testa se GET renderiza a lista de produtos para o próprio usuário logado."""
        response = self.client.get(self.lista_produtos_url_self)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lista_produtos.html')
        self.assertEqual(response.context['usuario'], self.user)
        self.assertEqual(response.context['usuariousername'], 'testuser')

    def test_lista_produtos_get_outro_usuario_logado(self):
        """Testa se GET redireciona para home se tentar acessar a lista de outro usuário."""
        response = self.client.get(self.lista_produtos_url_other)
        self.assertRedirects(response, self.home_url)

    def test_lista_produtos_get_usuario_nao_logado(self):
        """Testa se GET redireciona para login se o usuário não estiver logado."""
        self.client.logout()
        response = self.client.get(self.lista_produtos_url_self, follow=False)
        self.assertEqual(response.status_code, 302) 

    def test_lista_produtos_get_usuario_inexistente(self):
        """Testa se GET retorna 404 para um usuário inexistente."""
        inexistente_url = reverse('lista_produtos', kwargs={'username': 'nonexistentuser'})
        response = self.client.get(inexistente_url)
        self.assertEqual(response.status_code, 404)


class VendasViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.vendedor = User.objects.create_user(username='vendedor', password='password')
        self.cliente = User.objects.create_user(username='cliente', password='password2')
        self.vendas_url = reverse('vendas')
        self.client.force_login(self.vendedor)

        # Criando algumas ordens de teste associadas ao vendedor
        self.order1 = Order.objects.create(vendedor=self.vendedor, comprador=self.cliente, valor_total_pedido=50.00)
        self.order2 = Order.objects.create(vendedor=self.vendedor, comprador=self.cliente, valor_total_pedido=100.00)
        self.order_outro_vendedor = Order.objects.create(vendedor=self.cliente, comprador=self.vendedor, valor_total_pedido=25.00)

    def test_vendas_get_cliente_logado(self):
        """Testa se GET para a view de vendas retorna algo apropriado para um cliente logado."""
        self.client.logout()
        self.client.force_login(self.cliente)
        response = self.client.get(self.vendas_url)
        self.assertEqual(response.status_code, 200) 
        if 'orders' in response.context:
            orders_vendedor_cliente = [order for order in response.context['orders'] if order.vendedor == self.cliente]
            self.assertEqual(len(orders_vendedor_cliente), 1)
            self.assertIn(self.order_outro_vendedor, response.context['orders'])
        else:
            self.fail("Context 'orders' não encontrado.")
