import mercadopago
from dotenv import load_dotenv
import os

def realizar_pagamento(items, external_reference, application_fee):
    load_dotenv()

    sdk = mercadopago.SDK(f'{os.getenv("MP_ACCESS_TOKEN")}')

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
        "application_fee": float(application_fee),
    }

    preference_response = sdk.preference().create(preference_data)

    if "response" in preference_response and "init_point" in preference_response["response"]:
        return preference_response["response"]["init_point"]
    else:
        raise Exception(f"Erro ao criar link de pagamento: {preference_response.get('message')}")