# Use uma imagem Python Alpine para um tamanho de imagem menor
FROM python:3.12-alpine

# Defina variáveis de ambiente para o Python, melhorando o desempenho
# A flag --no-cache-dir usada nos comandos pip já ajuda, mas essas são boas práticas
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copie apenas o requirements.txt primeiro para aproveitar o cache do Docker
# Isso garante que se suas dependências não mudarem, essa camada seja reutilizada
COPY requirements.txt /requirements.txt

# Atualize pip e instale as dependências
# --no-cache-dir economiza espaço na imagem final
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /requirements.txt

# Crie e defina o diretório de trabalho para a aplicação
RUN mkdir /app
WORKDIR /app

COPY . .

COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN adduser -D appuser
USER appuser

EXPOSE 8000

ENTRYPOINT ["entrypoint.sh"]

