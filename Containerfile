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

# Copia o restante do código da aplicação
COPY . .

# Copia o entrypoint.sh para um local temporário, remove as quebras de linha CRLF,
# adiciona permissão de execução e então move para o local final.
# Isso garante que o script seja executável e interpretável no ambiente Linux.
COPY entrypoint.sh /tmp/entrypoint.sh
RUN sed -i 's/\r$//' /tmp/entrypoint.sh && \
    chmod +x /tmp/entrypoint.sh && \
    mv /tmp/entrypoint.sh /usr/local/bin/entrypoint.sh

# Cria um usuário não-root para segurança
RUN adduser -D appuser
USER appuser

# Expõe a porta que a aplicação Gunicorn irá usar
EXPOSE 8000

# Define o script entrypoint que será executado quando o container iniciar
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
