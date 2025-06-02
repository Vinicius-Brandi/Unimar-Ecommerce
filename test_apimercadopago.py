import pytest
from unittest.mock import Mock, patch
from apimercadopago import realizar_pagamento


# --- Testes de Sucesso ---
def test_realizar_pagamento_com_sucesso():
    # 1. Simular o SDK do Mercado Pago
    # Usamos 'patch' para substituir 'mercadopago.SDK' por um mock temporariamente
    # e 'sdk.preference().create' pelo nosso mock_criar
    with patch('mercadopago.SDK') as MockMercadoPagoSDK:
        # Configurar o comportamento esperado do mock
        instancia_mock_sdk = Mock()
        MockMercadoPagoSDK.return_value = instancia_mock_sdk # Quando mercadopago.SDK() é chamado, retorna esta instância mock

        instancia_mock_preferencia = Mock()
        instancia_mock_sdk.preference.return_value = instancia_mock_preferencia # Quando sdk.preference() é chamado, retorna esta instância mock

        # Configurar a resposta esperada da chamada .create()
        instancia_mock_preferencia.create.return_value = {
            "response": {
                "init_point": "https://pagamento.mercadopago.com/link_de_teste",
                "id": "123456789",
                # Outros dados que você espera na resposta, se houver
            }
        }

        # 2. Dados de teste
        token_acesso_vendedor = "TEST_ACCESS_TOKEN"
        itens = [{"title": "Produto Teste", "quantity": 1, "unit_price": 10.0}]
        referencia_externa = "REF-12345"
        taxa_aplicacao = 0.50

        # 3. Chamar a função a ser testada
        link_inicial = realizar_pagamento(token_acesso_vendedor, itens, referencia_externa, taxa_aplicacao)

        # 4. Verificar os resultados (Asserções)
        # Verifica se o SDK foi inicializado com o token correto
        MockMercadoPagoSDK.assert_called_once_with(token_acesso_vendedor)

        # Verifica se a preferência foi criada com os dados corretos
        dados_preferencia_esperados = {
            "items": itens,
            "back_urls": {
                "success": "https://unimarprojects.pythonanywhere.com/carrinho/compra_realizada/",
                "failure": "https://unimarprojects.pythonanywhere.com/carrinho/compra_falha/",
                "pending": "https://unimarprojects.pythonanywhere.com/carrinho/compra_pendente/",
            },
            "auto_return": "all",
            "notification_url": "https://unimarprojects.pythonanywhere.com/webhook/mercadopago/",
            "external_reference": referencia_externa,
            "application_fee": float(taxa_aplicacao), # Garante que a conversão para float aconteceu
        }
        instancia_mock_preferencia.create.assert_called_once_with(dados_preferencia_esperados)

        # Verifica se o link de pagamento retornado é o esperado
        assert link_inicial == "https://pagamento.mercadopago.com/link_de_teste"

# --- Testes de Erro ---
def test_realizar_pagamento_erro_da_api():
    with patch('mercadopago.SDK') as MockMercadoPagoSDK:
        instancia_mock_sdk = Mock()
        MockMercadoPagoSDK.return_value = instancia_mock_sdk

        instancia_mock_preferencia = Mock()
        instancia_mock_sdk.preference.return_value = instancia_mock_preferencia

        # Configurar a resposta de erro da API do Mercado Pago
        instancia_mock_preferencia.create.return_value = {
            "response": {
                "status": 400,
                "message": "Dados de pagamento inválidos",
                "error": "bad_request"
            }
        }

        token_acesso_vendedor = "TEST_ACCESS_TOKEN"
        itens = [{"title": "Produto Teste", "quantity": 1, "unit_price": 10.0}]
        referencia_externa = "REF-ERROR"
        taxa_aplicacao = 0.50

        # Verifica se a função levanta uma exceção com a mensagem de erro esperada
        with pytest.raises(Exception) as informacao_excecao:
            realizar_pagamento(token_acesso_vendedor, itens, referencia_externa, taxa_aplicacao)

        assert "Erro ao criar link de pagamento: Dados de pagamento inválidos" in str(informacao_excecao.value)

def test_realizar_pagamento_resposta_invalida():
    with patch('mercadopago.SDK') as MockMercadoPagoSDK:
        instancia_mock_sdk = Mock()
        MockMercadoPagoSDK.return_value = instancia_mock_sdk

        instancia_mock_preferencia = Mock()
        instancia_mock_sdk.preference.return_value = instancia_mock_preferencia

        # Simular uma resposta da API sem a chave 'response' ou 'init_point'
        instancia_mock_preferencia.create.return_value = {
            "alguma_outra_chave": "algum_valor"
        }

        token_acesso_vendedor = "TEST_ACCESS_TOKEN"
        itens = [{"title": "Produto Teste", "quantity": 1, "unit_price": 10.0}]
        referencia_externa = "REF-INVALIDA"
        taxa_aplicacao = 0.50

        with pytest.raises(Exception) as informacao_excecao:
            realizar_pagamento(token_acesso_vendedor, itens, referencia_externa, taxa_aplicacao)

        assert "Erro ao criar link de pagamento: Erro desconhecido" in str(informacao_excecao.value)

def test_taxa_aplicacao_com_conversao_para_float():
    with patch('mercadopago.SDK') as MockMercadoPagoSDK:
        instancia_mock_sdk = Mock()
        MockMercadoPagoSDK.return_value = instancia_mock_sdk

        instancia_mock_preferencia = Mock()
        instancia_mock_sdk.preference.return_value = instancia_mock_preferencia

        instancia_mock_preferencia.create.return_value = {
            "response": {
                "init_point": "https://pagamento.mercadopago.com/link_de_teste",
            }
        }

        token_acesso_vendedor = "TEST_ACCESS_TOKEN"
        itens = [{"title": "Produto Teste", "quantity": 1, "unit_price": 10.0}]
        referencia_externa = "REF-TAXA"
        taxa_aplicacao = "0.75" # Passando como string para testar a conversão

        realizar_pagamento(token_acesso_vendedor, itens, referencia_externa, taxa_aplicacao)

        # Verifica se a chamada para create recebeu application_fee como float
        # A maneira mais robusta é inspecionar o argumento da chamada
        args, kwargs = instancia_mock_preferencia.create.call_args
        assert kwargs['application_fee'] == 0.75
        assert isinstance(kwargs['application_fee'], float)