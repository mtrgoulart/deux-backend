# Usa uma imagem base do Python
FROM python:3.9

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto para o container
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Define o comando de entrada
CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info","--concurrency=4"]
