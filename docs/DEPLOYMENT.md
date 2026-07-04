# Deploying DocuMind IDP to Railway

## Prerequisites

1. Railway account (https://railway.app)
2. Railway CLI installed (`npm install -g @railway/cli`)

## Step-by-Step Deployment

### 1. Create Railway Project

```bash
railway login
railway init
```

### 2. Add PostgreSQL

- In Railway dashboard, click "+ New" > "Database" > "PostgreSQL"
- Copy the `DATABASE_URL` from the PostgreSQL service variables

### 3. Add Redis

- Click "+ New" > "Database" > "Redis"
- Copy the `REDIS_URL` from the Redis service variables

### 4. Deploy Backend

```bash
cd backend
railway up
```

Set environment variables in Railway dashboard:

```
DATABASE_URL=<from PostgreSQL service, change to postgresql+asyncpg://...>
DATABASE_SYNC_URL=<from PostgreSQL service>
REDIS_URL=<from Redis service>
CELERY_BROKER_URL=<Redis URL>/1
CELERY_RESULT_BACKEND=<Redis URL>/2
SECRET_KEY=<generate with: openssl rand -hex 32>
ALLOWED_ORIGINS=https://your-frontend.railway.app
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong-password>
STORAGE_BACKEND=local
OCR_ENGINE=tesseract
OPENAI_API_KEY=<optional, for LLM features>
```

### 5. Deploy Frontend

```bash
cd frontend
railway up
```

Set environment variables:

```
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

### 6. Deploy Celery Worker (Optional)

Create a new service in Railway for the worker:

```bash
cd backend
railway up --service worker
```

Set the start command to:
```
celery -A app.processing.celery_tasks worker --loglevel=info --concurrency=2
```

Use the same environment variables as the backend.

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | PostgreSQL connection (asyncpg) |
| REDIS_URL | Yes | Redis connection |
| SECRET_KEY | Yes | JWT signing key |
| ALLOWED_ORIGINS | Yes | CORS origins |
| ADMIN_EMAIL | Yes | Default admin email |
| ADMIN_PASSWORD | Yes | Default admin password |
| OPENAI_API_KEY | No | For LLM-powered extraction |
| SENTRY_DSN | No | Error tracking |
| S3_BUCKET | No | S3 storage (if not using local) |

## Local Development

```bash
# Start all services
docker-compose up -d

# Backend only
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev
```

## API Documentation

Once deployed, access:
- Swagger UI: `https://your-backend.railway.app/api/docs`
- ReDoc: `https://your-backend.railway.app/api/redoc`

## Default Login

- Email: `admin@documind.io` (or your ADMIN_EMAIL)
- Password: `admin123456` (or your ADMIN_PASSWORD)

**Change the default password immediately after first login!**
