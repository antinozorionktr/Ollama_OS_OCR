FROM python:3.11-slim

# ─── System deps for PDF processing + Node.js for docx generation ───
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
        curl \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

# ─── Install docx-js globally for Word document generation ───
RUN npm install -g docx@9.1.1

WORKDIR /app

# ─── Python deps ───
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── App code ───
COPY . .

# ─── Logs + data directories ───
RUN mkdir -p /app/logs /app/data /app/data/docx_outputs

# ─── Streamlit config (disable telemetry, set server) ───
RUN mkdir -p /root/.streamlit
RUN echo '[server]\nheadless = true\nport = 8501\naddress = "0.0.0.0"\nenableCORS = false\nenableXsrfProtection = false\nmaxUploadSize = 200\n\n[browser]\ngatherUsageStats = false\n' > /root/.streamlit/config.toml

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py"]