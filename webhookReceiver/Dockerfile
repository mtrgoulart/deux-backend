FROM python:3.9

RUN apt-get update && apt-get install -y libpq-dev

# Define o diretório de trabalho
WORKDIR /app

# Instala a configuração de timezone e define o fuso horário
RUN apt-get update && apt-get install -y tzdata
ENV TZ=America/Sao_Paulo

# Copia os arquivos necessários para o contêiner
COPY pipeline_app.py config.ini /app/

# Instala as dependências
RUN pip install --no-cache-dir Flask psycopg2-binary

# Expõe a porta do Flask
EXPOSE 5000

# Comando para iniciar o app
CMD ["python", "pipeline_app.py"]

