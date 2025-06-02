# apimercadopago.py
import mercadopago
import os
from dotenv import load_dotenv # Certifique-se que esta linha está presente

def realizar_pagamento(collector_id, items, external_reference, application_fee):
    load_dotenv() # Carrega as variáveis de ambiente do arquivo .env

    # IMPORTANTE: Usaremos o Access Token do SEU MARKETPLACE
    # Certifique-se que a variável de ambiente MP_ACCESS_TOKEN contém o token do seu marketplace
    marketplace_token = os.getenv("MP_ACCESS_TOKEN")
    if not marketplace_token:
        raise Exception("MP_ACCESS_TOKEN não encontrado nas variáveis de ambiente.")
        
    sdk = mercadopago.SDK(marketplace_token)

    preference_data = {
        "items": items,
        # Informa quem é o vendedor que deve receber o valor principal
        "collector_id": int(collector_id), # Convertendo para int, pois ID do usuário é numérico
        "back_urls": {
            "success": "https://unimarprojects.pythonanywhere.com/carrinho/compra_realizada/",
            "failure": "https://unimarprojects.pythonanywhere.com/carrinho/compra_falha/",
            "pending": "https://unimarprojects.pythonanywhere.com/carrinho/compra_pendente/",
        },
        "auto_return": "all",
        "notification_url": "https://unimarprojects.pythonanywhere.com/webhook/mercadopago/",
        "external_reference": external_reference,
        "application_fee": float(application_fee), # Sua comissão
    }

    # LINHA DE DEBUG CRUCIAL: Para vermos exatamente o que está sendo enviado
    print("--- DEBUG API MP: Enviando Preference Data:", preference_data) 

    preference_response = sdk.preference().create(preference_data)

    # Tratamento de erro mais detalhado
    if "response" not in preference_response:
        print("--- DEBUG API MP: Erro Completo na Criação da Preferência:", preference_response)
        error_details = preference_response.get("message", "Erro desconhecido ao criar preferência.")
        raise Exception(f"Erro ao criar link de pagamento: {error_details}")
        
    if "init_point" in preference_response["response"]:
        print("--- DEBUG API MP: Sucesso na Criação da Preferência, init_point:", preference_response["response"]["init_point"])
        return preference_response["response"]["init_point"]
    else:
        print("--- DEBUG API MP: Erro na Resposta da Criação da Preferência:", preference_response["response"])
        error_details = preference_response["response"].get("message", "init_point não encontrado na resposta")
        raise Exception(f"Erro ao criar link de pagamento: {error_details}")