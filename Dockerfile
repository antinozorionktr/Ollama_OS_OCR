FROM python:3.11-slim

# ─── System deps ───
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
        curl \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

# ─── docx-js for Word document generation ───
RUN npm install -g docx@9.1.1

WORKDIR /app

# ─── Python deps ───
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── App code ───
COPY . .

# ─── Directories ───
RUN mkdir -p /app/logs /app/data /app/data/docx_outputs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]