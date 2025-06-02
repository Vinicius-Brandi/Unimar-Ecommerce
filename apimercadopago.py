# apimercadopago.py
import mercadopago
import os
from dotenv import load_dotenv  # Adicionado para garantir que .env seja lido se existir


def realizar_pagamento(
    collector_id, items, external_reference, fee_amount
):  # 'fee_amount' será sua comissão
    load_dotenv()

    marketplace_access_token = os.getenv("MP_ACCESS_TOKEN")
    app_id_str = os.getenv("MP_APP_ID")  # Seu APP_ID/Client ID como string

    if not marketplace_access_token:
        raise Exception(
            "MP_ACCESS_TOKEN (do marketplace) não encontrado nas variáveis de ambiente."
        )
    if not app_id_str:
        raise Exception(
            "MP_APP_ID (do marketplace) não encontrado nas variáveis de ambiente."
        )

    sdk = mercadopago.SDK(
        marketplace_access_token
    )  # SDK iniciado com o TOKEN DO SEU MARKETPLACE

    try:
        # O APP_ID/Client ID do Mercado Pago é um número
        app_id_int = int(app_id_str)
    except ValueError:
        raise Exception(f"MP_APP_ID ('{app_id_str}') não é um número válido.")

    preference_data = {
        "items": items,
        "collector_id": int(collector_id),  # ID do usuário Mercado Pago do vendedor
        # --- CAMPOS ADICIONADOS BASEADO NO EXEMPLO DO MERCADO PAGO ---
        "marketplace": f"MP-MKT-{app_id_str}",  # Identificador do Marketplace
        "marketplace_fee": float(fee_amount),  # Sua comissão. Usando 'marketplace_fee'.
        "client_id": app_id_int,  # APP_ID da sua aplicação de marketplace
        # --- FIM DOS CAMPOS ADICIONADOS ---
        "back_urls": {
            "success": "https://unimarprojects.pythonanywhere.com/carrinho/compra_realizada/",
            "failure": "https://unimarprojects.pythonanywhere.com/carrinho/compra_falha/",
            "pending": "https://unimarprojects.pythonanywhere.com/carrinho/compra_pendente/",
        },
        "auto_return": "all",
        "notification_url": "https://unimarprojects.pythonanywhere.com/webhook/mercadopago/",
        "external_reference": external_reference,
        # "application_fee": float(fee_amount), # Removemos este, pois estamos testando com marketplace_fee
    }

    # DEBUG CRUCIAL: Para vermos exatamente o que está sendo enviado
    print("--- DEBUG API MP: Enviando Preference Data:", preference_data)

    preference_response = sdk.preference().create(preference_data)

    if "response" not in preference_response:
        print(
            "--- DEBUG API MP: Erro Completo na Criação da Preferência:",
            preference_response,
        )
        error_details = preference_response.get(
            "message", "Erro desconhecido ao criar preferência."
        )
        raise Exception(f"Erro ao criar link de pagamento: {error_details}")

    if "init_point" in preference_response["response"]:
        print(
            "--- DEBUG API MP: Sucesso na Criação da Preferência, init_point:",
            preference_response["response"]["init_point"],
        )
        return preference_response["response"]["init_point"]
    else:
        print(
            "--- DEBUG API MP: Erro na Resposta da Criação da Preferência:",
            preference_response["response"],
        )
        error_details = preference_response["response"].get(
            "message", "init_point não encontrado na resposta"
        )
        raise Exception(f"Erro ao criar link de pagamento: {error_details}")
