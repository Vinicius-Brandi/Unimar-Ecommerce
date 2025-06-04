#!/bin/sh

# Este é um exemplo simples de espera pelo banco de dados.
# Para ambientes de produção, considere usar uma ferramentas mais robustas como 'wait-for-it.sh'
# ou 'dockerize' se precisar de uma espera mais sofisticada.
# Certifique-se de que 'nc' (netcat) ou a ferramenta de espera esteja disponível na sua imagem se for usar.
# Exemplo básico de espera (descomente e ajuste se necessário):
# echo "Waiting for database connection..."
# while ! nc -z <host_do_banco_de_dados> <porta_do_banco_de_dados>; do
#   sleep 1
# done
# echo "Database connection established!"

# Aplica as migrações do banco de dados
# O --noinput evita perguntas interativas, ideal para automação em CI/CD
echo "Applying database migrations..."
python manage.py migrate --noinput

# Inicia o servidor WSGI de produção (Gunicorn)
# Substitua 'seu_projeto' pelo nome do módulo principal do seu projeto Django (onde está wsgi.py)
echo "Starting Gunicorn server..."
exec gunicorn Core.wsgi:application --bind 0.0.0.0:8000
