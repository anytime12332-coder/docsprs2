# DocuMind IDP - Intelligent Document Processing System

A production-ready, enterprise-grade Intelligent Document Processing (IDP) system with admin-controlled workflows, AI-powered extraction, and full document lifecycle management.

## Architecture

- **Backend**: Python FastAPI + Celery workers
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS + Shadcn UI
- **Database**: PostgreSQL (metadata) + Redis (cache/queue)
- **OCR**: PaddleOCR + Tesseract
- **AI/ML**: Hugging Face Transformers + LLM integration
- **Storage**: Local / S3-compatible (MinIO)
- **Deployment**: Railway-ready with Docker

## Features

- Multi-format document ingestion (PDF, DOCX, XLSX, images)
- AI-powered OCR with pre-processing pipeline
- Intelligent document classification
- Key-value and table extraction
- LLM-powered contextual understanding
- Rule-based and AI validation
- Admin dashboard with full control
- Audit trail and analytics
- REST API with OpenAPI docs
- Webhook integrations
- Role-based access control
- Production-ready deployment

## Quick Start

```bash
# Clone
git clone <repo-url>
cd documind-idp

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Deploy to Railway

See `railway.toml` and deployment docs in `/docs`.

## License

MIT
