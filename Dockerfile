FROM python:3.13-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY workshop/setup/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn pypdf reportlab openpyxl

# Copy application code
COPY workshop/ workshop/

# Environment (override at runtime)
ENV AWS_DEFAULT_REGION=us-east-1
ENV STREAMLIT_SERVER_PORT=8501
ENV API_PORT=8000

# Expose ports
EXPOSE 8501 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start both Streamlit and API
CMD ["sh", "-c", "uvicorn workshop.api:app --host 0.0.0.0 --port ${API_PORT} & streamlit run workshop/app.py --server.port ${STREAMLIT_SERVER_PORT} --server.address 0.0.0.0"]
