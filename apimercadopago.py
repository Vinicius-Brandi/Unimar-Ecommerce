import mercadopago
import os

# A função agora recebe o seller_access_token como primeiro argumento
def realizar_pagamento(seller_access_token, items, external_reference, application_fee):
    
    # IMPORTANTE: O SDK é iniciado com o token do VENDEDOR
    sdk = mercadopago.SDK(seller_access_token)

    preference_data = {
        "items": items,
        "back_urls": {
            "success": "https://unimarprojects.pythonanywhere.com/carrinho/compra_realizada/",
            "failure": "https://unimarprojects.pythonanywhere.com/carrinho/compra_falha/",
            "pending": "https://unimarprojects.pythonanywhere.com/carrinho/compra_pendente/",
        },
        "auto_return": "all",
        "notification_url": "https://unimarprojects.pythonanywhere.com/webhook/mercadopago/",
        "external_reference": external_reference,
        # A taxa da sua aplicação (a comissão do marketplace)
        "application_fee": float(application_fee),
    }

    preference_response = sdk.preference().create(preference_data)

    if "response" in preference_response and "init_point" in preference_response["response"]:
        return preference_response["response"]["init_point"]
    else:
        # Adicionando mais detalhes ao erro para facilitar a depuração
        error_details = preference_response.get("response", {}).get("message", "Erro desconhecido")
        raise Exception(f"Erro ao criar link de pagamento: {error_details}")