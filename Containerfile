# Use uma imagem Python Alpine para um tamanho de imagem menor
FROM python:3.12-alpine

# Defina variáveis de ambiente para o Python, melhorando o desempenho
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copie apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt /requirements.txt

# Atualize pip e instale as dependências
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /requirements.txt

# Crie e defina o diretório de trabalho para a aplicação
RUN mkdir /app
WORKDIR /app

# Copie todo o código da aplicação para o diretório de trabalho
# Certifique-se de ter um .dockerignore para excluir arquivos desnecessários
COPY . .

# Crie um usuário não-root para segurança
RUN adduser -D appuser
USER appuser

# Exponha a porta que a aplicação vai escutar
EXPOSE 8000

# Copie o script de entrypoint e torne-o executável
# Este script irá lidar com migrações e iniciar o servidor WSGI
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Defina o entrypoint do container
ENTRYPOINT ["entrypoint.sh"]

# Não há necessidade de CMD aqui, o entrypoint lida com a inicialização.
# A variável DEBUG DEVE ser controlada em tempo de execução, não no build da imagem!
# Removido: CMD python manage.py runserver 0.0.0.0:8000
# Removido: ENV debug=1
