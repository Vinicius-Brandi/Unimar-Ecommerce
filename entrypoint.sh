#!/bin/bash

# Define o PYTHONPATH para incluir o diretório raiz da aplicação (/app)
# Isso permite que o Python encontre os módulos do seu projeto (Core, Store, Usuario)
export PYTHONPATH="/app:$PYTHONPATH"

# Aplica as migrações do banco de dados.
# O '--noinput' evita prompts interativos.
# Se as migrações falharem, o script irá exibir uma mensagem de erro e sair com código 1.
echo "Aplicando migrações do banco de dados..."
python manage.py migrate --noinput || { echo "Erro: Falha ao aplicar migrações do banco de dados!" && exit 1; }

# Inicia o servidor Gunicorn.
# 'exec' substitui o processo atual do shell pelo Gunicorn, o que é uma boa prática para Docker.
# 'Core.wsgi:application' aponta para o seu arquivo WSGI principal.
# '--bind 0.0.0.0:8000' faz o Gunicorn escutar em todas as interfaces na porta 8000.
# '--workers 3' define 3 processos de worker (ajuste conforme a necessidade de recursos).
echo "Iniciando o servidor Gunicorn..."
exec gunicorn Core.wsgi:application --bind 0.0.0.0:8000 --workers 3
