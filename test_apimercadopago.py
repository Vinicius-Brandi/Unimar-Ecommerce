import unittest
from unittest.mock import patch, MagicMock
from apimercadopago import realizar_pagamento


class TestMercadoPago(unittest.TestCase):

    # Cenário 1: Testar o caminho de SUCESSO
    # Aqui, simulamos uma resposta bem-sucedida da API do Mercado Pago.
    @patch("apimercadopago.mercadopago.SDK")
    def test_realizar_pagamento_sucesso(self, MockSDK):
        """
        Testa se a função retorna o 'init_point' quando a API responde com sucesso.
        """
        # Configuração do Mock
        mock_sdk_instance = MagicMock()
        mock_preference = MagicMock()

        # Resposta simulada de sucesso da API
        mock_response_sucesso = {
            "response": {"init_point": "https://www.mercadopago.com.br/pagar"}
        }

        # Fazemos o método create() do mock retornar nossa resposta simulada
        mock_preference.create.return_value = mock_response_sucesso
        mock_sdk_instance.preference.return_value = mock_preference
        MockSDK.return_value = mock_sdk_instance

        # Dados de exemplo para a função
        seller_token = "TEST-TOKEN"
        items = [
            {"id": "123", "title": "Produto Teste", "quantity": 1, "unit_price": 100}
        ]
        external_reference = "REF-12345"
        application_fee = 10.0

        # Execução da função
        init_point = realizar_pagamento(
            seller_token, items, external_reference, application_fee
        )

        # Verificações (Asserts)
        self.assertEqual(init_point, "https://www.mercadopago.com.br/pagar")
        MockSDK.assert_called_once_with(
            seller_token
        )  # Verifica se o SDK foi iniciado com o token correto
        mock_preference.create.assert_called_once()  # Verifica se a criação da preferência foi chamada

    # Cenário 2: Testar o caminho de FALHA (erro conhecido da API)
    # Simulamos uma resposta de erro da API para garantir que nossa exceção é levantada.
    @patch("apimercadopago.mercadopago.SDK")
    def test_realizar_pagamento_falha_api(self, MockSDK):
        """
        Testa se a função levanta uma exceção com a mensagem de erro da API.
        """
        # Configuração do Mock
        mock_sdk_instance = MagicMock()
        mock_preference = MagicMock()

        # Resposta simulada de erro da API
        mock_response_falha = {"response": {"message": "Invalid seller access token"}}

        mock_preference.create.return_value = mock_response_falha
        mock_sdk_instance.preference.return_value = mock_preference
        MockSDK.return_value = mock_sdk_instance

        # Usamos 'assertRaises' para verificar se uma exceção é levantada
        with self.assertRaises(Exception) as context:
            realizar_pagamento("TOKEN-INVALIDO", [], "REF-FALHA", 5.0)

        # Verificamos se a mensagem de erro na exceção é a que esperamos
        self.assertEqual(
            str(context.exception),
            "Erro ao criar link de pagamento: Invalid seller access token",
        )

    # Cenário 3: Testar o caminho de FALHA (resposta inesperada)
    # Simulamos uma resposta malformada para garantir que o erro genérico é usado.
    @patch("apimercadopago.mercadopago.SDK")
    def test_realizar_pagamento_falha_desconhecida(self, MockSDK):
        """
        Testa se a função levanta uma exceção com a mensagem de erro padrão
        quando a resposta da API não tem o formato esperado.
        """
        # Configuração do Mock para retornar uma resposta vazia/inesperada
        mock_sdk_instance = MagicMock()
        mock_preference = MagicMock()
        mock_preference.create.return_value = {}  # Resposta vazia
        mock_sdk_instance.preference.return_value = mock_preference
        MockSDK.return_value = mock_sdk_instance

        with self.assertRaises(Exception) as context:
            realizar_pagamento("TOKEN", [], "REF-DESCONHECIDA", 5.0)

        self.assertEqual(
            str(context.exception), "Erro ao criar link de pagamento: Erro desconhecido"
        )
