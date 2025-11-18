FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Expose port (Cloud Run sets PORT dynamically)
ENV PORT=8501
EXPOSE 8501

# Run Streamlit app
# Use PORT environment variable for Cloud Run compatibility
# Disable browser auto-open and set headless mode for production
CMD sh -c "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false"

