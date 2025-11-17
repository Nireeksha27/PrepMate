# Use a Python base image
FROM python:3.9-slim-buster as builder

# Install wkhtmltopdf dependencies and wkhtmltopdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xvfb \
    xfonts-base \
    xfonts-75dpi \
    libjpeg-turbo8-dev && \
    wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.6/wkhtmltox_0.12.6-1.buster_amd64.deb && \
    apt-get install -y ./wkhtmltox_0.12.6-1.buster_amd64.deb && \
    rm wkhtmltox_0.12.6-1.buster_amd64.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variable for wkhtmltopdf path
ENV WKHTMLTOPDF_PATH /usr/local/bin/wkhtmltopdf

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY .

# Expose the port Streamlit runs on
EXPOSE 8080

# Command to run the Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
