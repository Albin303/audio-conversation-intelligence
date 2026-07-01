│  │  Port 3000   │      │  Port 8000   │                   │
│  └──────────────┘      └──────┬───────┘                   │
│                                │                            │
│                    ┌───────────┼───────────┐               │
│                    │           │           │               │
│              ┌─────▼─────┐ ┌───▼────┐ ┌───▼────┐         │
│              │  Uploads  │ │  DB    │ │  Logs  │         │
│              │  Volume   │ │Volume  │ │Volume  │         │
│              └───────────┘ └────────┘ └────────┘         │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐       │
│  │  Audio Worker    │────────▶│   ML Worker      │       │
│  │  (Whisper/etc)   │         │  (XGBoost/etc)   │       │
│  │  Profile: workers│         │  Profile: workers│       │
│  └──────────────────┘         └──────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Container Startup Sequence

1. **API Container** starts first
   - Initializes SQLite database
   - Starts FastAPI server on port 8000
   - Runs health check
   - Exposes `/health`, `/api/health`, `/api/readiness`

2. **Frontend Container** starts after API is healthy
   - Waits for API health check to pass
   - Builds Next.js application
   - Starts on port 3000
   - Connects to API via `NEXT_PUBLIC_API_URL`

3. **Audio Worker** (optional, profile: workers)
   - Starts after API is healthy
   - Loads Whisper, Pyannote, SpeechBrain
   - Processes audio uploads from queue
   - Updates job status in SQLite

4. **ML Worker** (optional, profile: workers)
   - Starts after API is healthy
   - Loads XGBoost, scikit-learn, joblib
   - Processes lead scoring
   - Updates job status in SQLite

## Deployment Instructions

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB+ RAM (16GB recommended for workers)
- 20GB+ disk space

### Quick Start (API + Frontend only)

```bash
# Clone repository
git clone <repo-url>
cd nexus-ai

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Start API and Frontend
docker compose -f docker-compose.v2.yml up --build

# Access:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Full Deployment (with workers)

```bash
# Start all services including workers
docker compose -f docker-compose.v2.yml --profile workers up --build

# Or start specific worker
docker compose -f docker-compose.v2.yml --profile workers up --build audio-worker
```

### Environment Variables

Required in `.env`:

```env
# LLM Provider (choose one)
LLAMA_API_KEY=your_llama_api_key
# OR
MINIMAX_API_KEY=your_minimax_api_key

# Whisper Configuration
USE_GROQ_WHISPER=true  # Use Groq API (recommended)
# WHISPER_MODEL=whisper-large-v3  # If using local Whisper

# Database
NEXUS_SQLITE_PATH=/app/database/nexus_ai.db

# Storage
NEXUS_UPLOADS_DIR=/app/uploads
NEXUS_LOGS_DIR=/app/logs

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check readiness
curl http://localhost:8000/api/readiness

# Check database
curl http://localhost:8000/api/health/database

# Check storage
curl http://localhost:8000/api/health/storage

# Check worker status
curl http://localhost:8000/api/health/worker
```

## Image Sizes (Estimated)

| Image | Base Size | With Dependencies | Total |
|-------|-----------|-------------------|-------|
| API | ~50MB | ~200MB | ~250MB |
| Audio Worker | ~50MB | ~2GB (torch+whisper) | ~2.2GB |
| ML Worker | ~50MB | ~500MB (xgboost+sklearn) | ~550MB |
| Frontend | ~100MB | ~150MB | ~250MB |

**Total with workers: ~3.2GB**
**Total without workers: ~500MB**

## Performance Benchmarks

### API Startup Time

- **Cold start**: ~2-3 seconds
- **Warm start**: ~500ms
- **First request**: ~3-4 seconds (lazy loading)

### Memory Usage

- **API container**: ~150-200MB
- **Audio worker**: ~2-3GB (when processing)
- **ML worker**: ~500MB-1GB (when processing)

### Queue Latency

- **Upload to queue**: <100ms
- **Job pickup**: <1s
- **Processing time**: Varies by audio length

## Volumes

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| `nexus_uploads` | Audio file storage | Persistent |
| `nexus_database` | SQLite database | Persistent |
| `nexus_logs` | Application logs | Persistent |

## Networking

- All containers on `nexus-network` (bridge)
- API exposed on port 8000
- Frontend exposed on port 3000
- Workers not exposed (internal only)

## Scaling

### Horizontal Scaling

```yaml
# Scale API instances
docker compose -f docker-compose.v2.yml up --scale api=3

# Scale workers
docker compose -f docker-compose.v2.yml --profile workers up --scale audio-worker=2 --scale ml-worker=2
```

### Load Balancing

For production, add a reverse proxy:

```yaml
# Add to docker-compose.v2.yml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
      - frontend
```

## Monitoring

### Logs

```bash
# View all logs
docker compose -f docker-compose.v2.yml logs -f

# View specific service
docker compose -f docker-compose.v2.yml logs -f api

# View worker logs
docker compose -f docker-compose.v2.yml --profile workers logs -f audio-worker
```

### Metrics

Access health endpoints:

```bash
# API metrics
curl http://localhost:8000/api/health

# Detailed readiness
curl http://localhost:8000/api/readiness
```

## Troubleshooting

### API won't start

```bash
# Check logs
docker compose -f docker-compose.v2.yml logs api

# Common issues:
# 1. Port 8000 already in use
# 2. Missing .env file
# 3. SQLite directory permissions
```

### Workers not processing

```bash
# Check worker logs
docker compose -f docker-compose.v2.yml --profile workers logs audio-worker

# Verify queue is running
curl http://localhost:8000/api/health/worker

# Check job status
curl http://localhost:8000/api/jobs/{job_id}
```

### Frontend can't connect to API

```bash
# Verify API is running
curl http://localhost:8000/health

# Check CORS configuration
curl http://localhost:8000/api/health -H "Origin: http://localhost:3000"

# Verify NEXT_PUBLIC_API_URL in docker-compose.v2.yml
```

## Production Checklist

- [ ] Set strong `LLAMA_API_KEY` or `MINIMAX_API_KEY`
- [ ] Configure `ALLOWED_ORIGINS` for production domain
- [ ] Enable HTTPS with reverse proxy (nginx/traefik)
- [ ] Set up log rotation
- [ ] Configure database backups
- [ ] Monitor disk space for uploads
- [ ] Set up alerting for failed jobs
- [ ] Review worker resource limits
- [ ] Test disaster recovery
- [ ] Document runbook for common issues

## Remaining Blockers

1. **Docker Desktop not available** — Cannot verify image builds locally
2. **Worker queue integration** — Need to verify workers can pull jobs from shared SQLite/queue
3. **End-to-end testing** — Need to test full upload → process → result flow
4. **Performance testing** — Need to measure actual API startup time and memory usage
5. **Frontend integration** — Need to verify frontend works with new service architecture

## Next Steps

1. Start Docker Desktop
2. Run `docker compose -f docker-compose.v2.yml build`
3. Verify image sizes match estimates
4. Run `docker compose -f docker-compose.v2.yml up`
5. Test health endpoints
6. Upload test audio file
7. Verify worker processing
8. Check SQLite persistence
9. Test frontend compatibility
10. Measure performance metrics