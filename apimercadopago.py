import mercadopago
import os
from dotenv import load_dotenv

load_dotenv()

# A função agora também recebe o collector_id
def realizar_pagamento(collector_id, items, external_reference, application_fee):
    
    MARKETPLACE_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
    if not MARKETPLACE_ACCESS_TOKEN:
        raise Exception("Access Token do Marketplace não encontrado.")

    sdk = mercadopago.SDK(MARKETPLACE_ACCESS_TOKEN)

    preference_data = {
        # ✅ NOVO PARÂMETRO: Indica para quem vai o dinheiro
        "collector_id": 554466433, 
        
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
        error_details = preference_response.get("response", {}).get("message", "Erro desconhecido")
        raise Exception(f"Erro ao criar link de pagamento: {error_details}")