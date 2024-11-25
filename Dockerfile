# Usa uma imagem base Python
FROM python:3.9-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala dependências do sistema e configura o fuso horário
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata iputils-ping curl && \
    rm -rf /var/lib/apt/lists/* && \
    dpkg-reconfigure --frontend noninteractive tzdata

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

# Expõe a porta que a aplicação usará
EXPOSE 5001

# Comando para iniciar o aplicativo com Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "main:app"]

