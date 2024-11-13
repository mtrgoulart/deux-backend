# Usa uma imagem base Python
FROM python:3.9

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

RUN apt-get update && apt-get install -y tzdata
ENV TZ=America/Sao_Paulo
RUN dpkg-reconfigure --frontend noninteractive tzdata


# Define o PYTHONPATH para incluir o diretório /app
ENV PYTHONPATH=/app

# Copia o arquivo de dependências para o contêiner
COPY requirements.txt requirements.txt

# Instala as dependências do Python
RUN pip install -r requirements.txt

# Copia todo o conteúdo da aplicação para o diretório de trabalho no contêiner
COPY . .

# Define a variável de ambiente para que o Flask escute em todas as interfaces de rede
ENV FLASK_APP=main
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8080

# Exponha a porta 8080 para o servidor Flask
EXPOSE 8080

# Comando para iniciar o aplicativo Flask com main.py
CMD ["python", "main.py"]

