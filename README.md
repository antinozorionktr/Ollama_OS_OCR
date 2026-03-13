# DocVision OCR v4.0

Semantic document OCR system using **llama3.2-vision:11b** for text extraction and **mistral:7b** for text cleanup & layout reconstruction. 100% offline, no bounding boxes — pure LLM-based pipeline.

## Architecture

```
Document Upload → PDF to page images → Per page:
  1. llama3.2-vision:11b  →  Raw Text (structural hints)
  2. mistral:7b           →  Cleaned Text (spacing/punctuation fixed)
  3. mistral:7b           →  Recreated Layout (sections/tables/checkboxes)
→ Stored per-page in SQLite
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Vision Extraction | `llama3.2-vision:11b` via Ollama |
| Text Cleanup / Layout | `mistral:7b` via Ollama |
| Backend | FastAPI (Python) |
| Frontend | React + Vite |
| Database | SQLite (`data/docvision.db`) |

---

## Prerequisites

1. **Python 3.10+**
2. **Node.js 18+** (for frontend)
3. **Ollama** installed and running — [Install Ollama](https://ollama.com/download)

---

## Setup Guide

### 1. Pull Required Models

```bash
# Vision model (text extraction from images)
ollama pull llama3.2-vision:11b

# Cleanup model (text formatting & layout reconstruction)
ollama pull mistral:7b
```

Verify models are available:
```bash
ollama list
```
You should see both `llama3.2-vision:11b` and `mistral:7b` listed.

### 2. Backend Setup

```bash
# Navigate to project
cd Ollama_OS_OCR

# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create data directories
mkdir -p data/Documents logs
```

### 3. Configure Environment

The `.env` file is pre-configured with defaults. Edit if needed:

```env
OLLAMA_BASE_URL=http://localhost:11434
VISION_MODEL=llama3.2-vision:11b
CLEANUP_MODEL=mistral:7b
DB_PATH=./data/docvision.db
DOCUMENT_DIR=./data/Documents
```

### 4. Start Ollama

```bash
# In a separate terminal
ollama serve
```

### 5. Run the Backend

```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

The API will be available at:
- **API Docs**: http://localhost:8004/docs
- **Health Check**: http://localhost:8004/api/health

### 6. Frontend Setup

```bash
# In a separate terminal
cd frontend

# Install dependencies (first time only)
npm install

# Run dev server
npm run dev
```

Frontend runs at **http://localhost:5173** by default.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check (Ollama + DB status) |
| `GET` | `/api/config` | Current server configuration |
| `GET` | `/api/stats` | Document and file counts |
| `POST` | `/api/upload` | Upload & process a document |
| `GET` | `/api/documents` | List all processed documents |
| `GET` | `/api/documents/{id}` | Get document with all pages |
| `GET` | `/api/documents/{id}/pages/{n}` | Get single page result |
| `GET` | `/api/documents/{id}/preview` | Stream original document file |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `DELETE` | `/api/documents` | Delete all documents |

### Example API Response

```json
{
  "document": {
    "id": 1,
    "filename": "application.pdf",
    "uploaded_at": "2026-03-12T18:30:00",
    "total_pages": 3
  },
  "pages": [
    {
      "page_number": 1,
      "raw_text": "Section: Application Form\nName: John Doe...",
      "cleaned_text": "Name: John Doe\nAge: 32\nMarital Status: Single",
      "recreated_layout": "──────────────────\n  APPLICATION FORM\n──────────────────\nName: John Doe..."
    }
  ]
}
```

---

## Three Output Views

| View | Description | Source |
|------|-------------|--------|
| **Raw Text** | Direct output from vision model, minimal formatting | `llama3.2-vision:11b` |
| **Cleaned Text** (default) | Readable, properly formatted text | `mistral:7b` |
| **Recreated Layout** | Visually reconstructed document with tables, forms, checkboxes | `mistral:7b` |

---

## Database Schema

```sql
-- Documents table
documents (id, filename, file_path, uploaded_at, total_pages, processing_time_seconds, error)

-- Per-page results
document_pages (id, document_id FK, page_number, raw_text, cleaned_text, recreated_layout, created_at)
```

---

## Quick Test

```bash
# 1. Check health
curl http://localhost:8004/api/health

# 2. Upload a document
curl -X POST http://localhost:8004/api/upload \
  -F "file=@/path/to/document.pdf"

# 3. View results
curl http://localhost:8004/api/documents/1
```