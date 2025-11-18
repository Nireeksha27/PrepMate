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
# Try multiple sources to ensure compatibility
RUN apt-get update && apt-get install -y --no-install-recommends \
    xfonts-base \
    xfonts-75dpi \
    xz-utils \
    ca-certificates \
    && cd /tmp \
    && (curl -L -o wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb 2>/dev/null \
        || curl -L -o wkhtmltox.tar.xz https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.6/wkhtmltox_0.12.6-1.static-amd64.tar.xz 2>/dev/null) \
    && (test -f wkhtmltox.deb && dpkg -i wkhtmltox.deb || \
        (test -f wkhtmltox.tar.xz && tar -xJf wkhtmltox.tar.xz && \
         cp wkhtmltox/bin/wkhtmltopdf /usr/local/bin/ && \
         cp wkhtmltox/bin/wkhtmltoimage /usr/local/bin/ && \
         rm -rf wkhtmltox)) \
    && rm -f wkhtmltox.deb wkhtmltox.tar.xz 2>/dev/null || true \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Expose port (Cloud Run sets PORT dynamically)
ENV PORT=8080
EXPOSE 8080

# Run FastAPI with uvicorn
# Use PORT environment variable for Cloud Run compatibility
CMD sh -c "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"


