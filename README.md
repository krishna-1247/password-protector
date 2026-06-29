# PDF Password Protector — Web Application

> Bulk-encrypt thousands of PDFs using passwords from an Excel sheet.
> Modern full-stack web application — no database, no permanent storage.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (Next.js 15 · React 19 · Tailwind · Framer Motion) │
│  Drag-drop upload · Live progress · Download ZIP            │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API
┌───────────────────────▼─────────────────────────────────────┐
│  FastAPI + Uvicorn (Python)                                  │
│  POST /upload · POST /process · GET /status · GET /download  │
│                                                              │
│  Reuses existing modules:                                    │
│  excel_reader · pdf_encryptor · processor · logger · utils  │
└─────────────────────────────────────────────────────────────┘
                        │
              /tmp/job-{uuid}/
              uploads/ · encrypted/ · .zip
              (auto-deleted after 30 min)
```

---

## Project Structure

```
password_protector/
│
├── backend/                    ← FastAPI application
│   ├── app/
│   │   ├── main.py             ← App factory + CORS + lifespan
│   │   ├── routers/jobs.py     ← 5 REST endpoints
│   │   ├── services/
│   │   │   ├── job_store.py    ← In-memory job registry
│   │   │   ├── encryption_service.py
│   │   │   └── zip_service.py
│   │   ├── models/schemas.py   ← Pydantic response models
│   │   └── core/
│   │       ├── config.py       ← Settings from env vars
│   │       └── cleanup.py      ← Background TTL cleanup
│   ├── src/                    ← Existing Python modules (reused)
│   │   ├── excel_reader.py
│   │   ├── pdf_encryptor.py
│   │   ├── processor.py
│   │   ├── logger.py
│   │   └── utils.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                   ← Next.js application
│   ├── app/
│   │   ├── layout.tsx          ← Root layout + Sonner toasts
│   │   ├── page.tsx            ← Main dashboard page
│   │   └── globals.css
│   ├── components/
│   │   ├── layout/Header.tsx
│   │   ├── upload/DropZone.tsx
│   │   ├── upload/ExcelUpload.tsx
│   │   ├── job/ProgressCard.tsx
│   │   ├── job/StatsRow.tsx
│   │   └── job/ActivityLog.tsx
│   ├── lib/
│   │   ├── api.ts              ← Typed API client
│   │   └── types.ts            ← Shared TS interfaces
│   ├── hooks/useJobPoller.ts   ← Auto-polling hook
│   ├── Dockerfile
│   └── .env.local.example
│
├── docker-compose.yml          ← Full-stack local dev
│
└── README.md
```

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Node.js 20+

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # edit as needed

uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# → http://localhost:3000
```

---

## Docker (Full Stack)

```bash
docker-compose up --build
# Frontend → http://localhost:3000
# Backend  → http://localhost:8000
```

---

## REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/upload` | Upload PDFs + Excel; returns `{ jobId }` |
| `POST` | `/api/v1/process/{jobId}` | Start encryption (202 Accepted) |
| `GET`  | `/api/v1/status/{jobId}` | Poll status + progress + stats |
| `GET`  | `/api/v1/download/{jobId}` | Stream encrypted ZIP |
| `DELETE` | `/api/v1/cleanup/{jobId}` | Delete temp files immediately |
| `GET`  | `/health` | Health check |

Full interactive docs: `http://localhost:8000/docs`

### Upload Request
```
POST /api/v1/upload
Content-Type: multipart/form-data

pdfs[]   = <pdf files>
excel    = <xlsx/xls/csv file>
```

### Process Request
```json
POST /api/v1/process/{jobId}
{
  "skip_encrypted": true,
  "overwrite": true,
  "max_workers": 4
}
```

### Status Response
```json
{
  "job_id": "f0e4776a-...",
  "status": "completed",
  "progress": 100,
  "done": 1000,
  "total": 1000,
  "stats": {
    "total": 1000,
    "success": 987,
    "missing": 10,
    "failed": 3,
    "skipped": 0,
    "elapsed_sec": 42.3
  },
  "results": [...]
}
```

---

## Deployment

### Backend → Railway

1. Connect your GitHub repo on [railway.app](https://railway.app)
2. Set root directory to `backend/`
3. Set environment variables:
   ```
   ALLOWED_ORIGINS=["https://your-app.vercel.app"]
   MAX_WORKERS=4
   JOB_TTL_MINUTES=30
   ```
4. Railway auto-detects `Dockerfile` and deploys

### Frontend → Vercel

1. Import repo on [vercel.com](https://vercel.com)
2. Set root directory to `frontend/`
3. Set environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```
4. Deploy

---

## Environment Variables

### Backend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS origins |
| `MAX_UPLOAD_MB` | `500` | Max file size per upload |
| `MAX_PDF_COUNT` | `10000` | Max PDFs per batch |
| `MAX_WORKERS` | `4` | Thread pool size |
| `SKIP_ENCRYPTED` | `true` | Skip already-encrypted PDFs |
| `JOB_TTL_MINUTES` | `30` | Auto-delete after N minutes |
| `CLEANUP_INTERVAL_SECONDS` | `300` | Cleanup check frequency |
| `TMP_ROOT` | OS default | Base temp directory |

### Frontend (`.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend base URL (no trailing slash) |

---

## Security

- File type validation (PDF + Excel only)
- Filename sanitisation (prevents path traversal)
- Configurable upload size limits
- No files permanently stored — all deleted after TTL
- Non-root Docker user
- CORS restricted to configured origins

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript |
| Styling | Tailwind CSS |
| Animations | Framer Motion |
| Toasts | Sonner |
| Backend | FastAPI, Uvicorn |
| PDF | pypdf (AES-256) |
| Excel | pandas + openpyxl |
| Container | Docker + Docker Compose |
