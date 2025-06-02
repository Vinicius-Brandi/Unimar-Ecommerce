import mercadopago

def realizar_pagamento(platform_access_token, seller_user_id, items, external_reference, application_fee):
    # Use o token da sua plataforma (não do vendedor)
    sdk = mercadopago.SDK(platform_access_token)

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
        "application_fee": float(application_fee),  # Sua comissão
        "payer": {
            # você pode adicionar o e-mail ou info do comprador se quiser
        },
        # IMPORTANTE: identifica o vendedor para receber o valor líquido
        "marketplace": "MeuMarketplace",  # opcional
        "collector_id": seller_user_id,  # ID do vendedor (não o token!)
    }

    preference_response = sdk.preference().create(preference_data)

    if "response" in preference_response and "init_point" in preference_response["response"]:
        return preference_response["response"]["init_point"]
    else:
        error_details = preference_response.get("response", {}).get("message", "Erro desconhecido")
        raise Exception(f"Erro ao criar link de pagamento: {error_details}")