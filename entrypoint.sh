#!/bin/sh

# Aguarda o banco de dados estar disponível (opcional, mas recomendado para CI/CD)
# Você pode usar ferramentas como wait-for-it.sh ou um loop simples
# while ! nc -z db 5432; do   # Assumindo o serviço do DB se chama 'db' e porta 5432
#   echo "Waiting for database connection..."
#   sleep 1
# done

# Aplica as migrações do banco de dados
echo "Applying database migrations..."
python manage.py migrate --noinput

# Inicia o servidor WSGI de produção (Gunicorn)
echo "Starting Gunicorn server..."
exec gunicorn Core.wsgi:application --bind 0.0.0.0:8000
