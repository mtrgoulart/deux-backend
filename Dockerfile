# Usa uma imagem base Python
FROM python:3.9-slim

# Instala Node.js e npm
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instalar dependências necessárias para o psycopg
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Define o fuso horário
ENV TZ=America/Sao_Paulo

# Define o PYTHONPATH para incluir o diretório /app
ENV PYTHONPATH=/app

# Copia o arquivo de dependências para o contêiner
COPY requirements.txt .

# Instala as dependências do Python, incluindo o Gunicorn
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copia todo o conteúdo da aplicação para o diretório de trabalho no contêiner
COPY . .

# Instala as dependências do Node.js (incluindo uuid)
RUN npm install uuid

# Expõe a porta que a aplicação usará
EXPOSE 5001

# Comando para iniciar o aplicativo com Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "main:app"]