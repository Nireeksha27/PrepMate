FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libfreetype6 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.6/wkhtmltox_0.12.6-1.bionic_amd64.deb \
    && apt-get update \
    && apt-get install -y ./wkhtmltox_0.12.6-1.bionic_amd64.deb \
    && rm wkhtmltox_0.12.6-1.bionic_amd64.deb

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PORT=8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]


