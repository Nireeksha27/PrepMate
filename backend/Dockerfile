FROM python:3.11-slim

# Install system dependencies for PDF generation (wkhtmltopdf)
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

# Install wkhtmltopdf for PDF generation
RUN wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.6/wkhtmltox_0.12.6-1.bionic_amd64.deb \
    && apt-get update \
    && apt-get install -y ./wkhtmltox_0.12.6-1.bionic_amd64.deb \
    && rm wkhtmltox_0.12.6-1.bionic_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Expose port
ENV PORT=8080
EXPOSE 8080

# Run FastAPI with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]


