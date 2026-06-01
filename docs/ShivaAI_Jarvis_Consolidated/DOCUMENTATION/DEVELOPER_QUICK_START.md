# ShivaAI Jarvis — Developer Quick Start Guide

**For:** Engineering team starting development  
**Duration to read:** 10 minutes  
**Next step:** Setup your dev environment  

---

## 🚀 PROJECT AT A GLANCE

| What | Details |
|------|---------|
| **Project** | ShivaAI Jarvis v5+ (Autonomous AI Operating System) |
| **Current Status** | Local MVP implemented |
| **Roadmap Target** | Enterprise-ready AI operating system |
| **Current Goal** | Run and extend the local gateway/web MVP |
| **Implemented Tech** | FastAPI, React, SQLite, Docker Compose |
| **Roadmap Tech** | LangGraph, Qdrant, Neo4j, Kubernetes, enterprise connectors |

---

## 📁 WHERE TO FIND EVERYTHING

### Essential Documents

```
/docs/
├── SHIVAAI_JARVIS_1MONTH_ENTERPRISE_ROADMAP.md ← Development timeline (28 days)
├── SHIVAAI_PROJECT_DOCUMENTATION.md            ← Complete specifications
├── DEVELOPER_QUICK_START.md                    ← You are here
├── PDF_FEATURE_COMPLETION_AUDIT.md             ← Implemented vs future feature audit
├── CAPABILITY_REGISTRY.md                      ← Registry API and executor notes
├── SELF_LEARNING_FEEDBACK.md                   ← Feedback capture notes
└── JARVIS_PROFILE.md                           ← Profile/preference notes

/services/gateway/                              ← Python FastAPI gateway
/apps/web/                                      ← React TypeScript app
/infra/monitoring/                              ← Prometheus config
/scripts/                                      ← Automation scripts
```

### Quick Links

- **Roadmap:** [1-Month Timeline](SHIVAAI_JARVIS_1MONTH_ENTERPRISE_ROADMAP.md)
- **Full Specs:** [Project Documentation](SHIVAAI_PROJECT_DOCUMENTATION.md)
- **Feature Audit:** [PDF Feature Completion Audit](PDF_FEATURE_COMPLETION_AUDIT.md)
- **Architecture:** [System Design](SHIVAAI_PROJECT_DOCUMENTATION.md#3-architecture--system-design)
- **APIs:** [API Specifications](SHIVAAI_PROJECT_DOCUMENTATION.md#5-api-specifications)
- **Database:** [PostgreSQL Schema](SHIVAAI_PROJECT_DOCUMENTATION.md#6-database-schema--design)
- **Security:** [Security & Compliance](SHIVAAI_PROJECT_DOCUMENTATION.md#8-security--compliance)

---

## 🛠️ LOCAL SETUP (30 minutes)

### Prerequisites

```bash
# Required
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- Git
- PostgreSQL 15 (or via Docker)
- Redis 7+ (or via Docker)

# Verify installations
python --version      # 3.12+
node --version        # 18+
docker --version      # 20+
git --version         # 2.40+
```

### 1. Clone Repository

```bash
git clone https://github.com/your-org/shivaai-jarvis.git
cd shivaai-jarvis

# Create main branches
git checkout -b develop origin/develop
```

### 2. Backend Setup

```bash
# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r services/gateway/requirements.txt
pip install -r requirements-dev.txt  # Dev tools

# Create .env file
cp .env.example .env

# Edit .env
nano .env
# Set:
# DATABASE_PATH=data/gateway.db
# LLM_PROVIDER=local
# OPENAI_API_KEY=sk-...
# JWT_SECRET=your-secret-key

# Start backend
cd services/gateway
uvicorn src.main:app --reload --port 8000
# Server running at http://localhost:8000
```

### 3. Frontend Setup

```bash
cd apps/web

# Install dependencies
npm install

# Create .env.local
cp .env.example .env.local
# Set:
# VITE_API_URL=http://localhost:8000
# VITE_WS_URL=ws://localhost:8000

# Start dev server
npm run dev
# App running at http://localhost:5173
```

### 4. Docker Setup (Full Stack)

```bash
# From project root
docker-compose up -d

# Services will be available:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
# - Qdrant: http://localhost:6333
# - Neo4j: http://localhost:7474

# Check logs
docker-compose logs -f gateway

# Stop all services
docker-compose down
```

### 5. Verify Setup

```bash
# Test backend
curl http://localhost:8000/health

# Test frontend loads
curl http://localhost:3000

# Run tests
python -m pytest tests
npm test
```

---

## 👥 TEAM ROLES & QUICK ASSIGNMENTS

### Week 1 Assignments

**Backend Lead + 1 Engineer:**
- [x] Local SQLite schema and repository
- [x] FastAPI auth and gateway
- [x] Local/OpenAI-compatible LLM abstraction
- [x] Basic chat endpoints

**Frontend Lead + 1 Engineer:**
- [x] React app shell
- [x] Auth UI for signup/login/logout
- [x] Chat, memory, document, profile, feedback, and capability panels
- [x] Browser speech-to-text input
- [ ] Streaming response rendering in the UI

**DevOps/Security:**
- [x] Docker Compose local stack
- [x] CI workflow for backend tests and frontend build
- [x] Basic security headers and local JWT-style auth
- [ ] Rate limiting, OAuth2, ABAC, and production secret management

**AI/ML:**
- [x] Local provider and OpenAI-compatible provider
- [x] Deterministic planner capability
- [ ] Embedding pipeline with vector storage
- [ ] LangGraph orchestration and reflection agents

---

## 📊 ARCHITECTURE OVERVIEW (2-min version)

```
User (Chat/Voice/API)
         ↓
  [FastAPI Gateway]
  - Auth (OAuth2/JWT)
  - Rate limiting
  - Routing
         ↓
[Local Capability Executors]
- Planner
- Memory search
- Registry discovery
         ↓
[Memory + Knowledge]
- SQLite memory and document chunks
- Qdrant and Neo4j are available in Docker but not wired into the app yet
         ↓
[Specialized Modules]
- Capability registry foundation
- Trading, Code, Teaching, Predictions, and Workflow remain roadmap modules
         ↓
    [Response Stream]
    (SSE/WebSocket)
         ↓
    User sees result
```

**Key Flow:**
1. Request → Gateway (auth, validate)
2. Local provider or configured OpenAI-compatible provider generates a response
3. Relevant SQLite memories are added to context
4. Chat turns are persisted
5. Episodic memory and feedback can be stored
6. SSE endpoint is available for streaming clients

---

## 📝 COMMON COMMANDS

### Git Workflow

```bash
# Create feature branch
git checkout -b feat/chat-streaming

# Make changes
git add .
git commit -m "feat: add streaming chat responses"

# Push and create PR
git push origin feat/chat-streaming
# Open PR on GitHub

# After review, merge via GitHub UI
```

### Backend Development

```bash
# Run server with auto-reload
cd services/gateway
uvicorn src.main:app --reload --port 8000

# Run specific test
python -m pytest tests/test_gateway_smoke.py::test_streaming_chat_endpoint_returns_sse_events -v

# Run all tests with coverage
python -m pytest tests

# Format code
ruff format services/gateway/src tests

# Lint code
ruff check services/gateway/src tests

# Type check
mypy services/gateway/src
```

### Frontend Development

```bash
# Run dev server
npm run dev

# Run tests
npm test

# Build for production
npm run build

# Format check
npm run format

# Type/lint check
npm run lint
```

### Docker

```bash
# Build image
docker build -t shivaai-jarvis:latest .

# Run container
docker run -p 8000:8000 shivaai-jarvis:latest

# View logs
docker logs -f container_id

# Stop container
docker stop container_id
```

### Database

```bash
# Create migration
alembic revision --autogenerate -m "add user_feedback table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Access database
psql postgresql://user:password@localhost:5432/shivaai
```

---

## 🎯 DAILY STANDUP TEMPLATE

Every morning, post in Slack:

```
:wave: [Your Name]

What I did yesterday:
- Implemented streaming chat endpoint
- Added 15 unit tests

What I'm doing today:
- Add artifact generation
- Review PR #42

Blockers:
- Waiting for OpenAI API key (shared with tech lead)

Help needed:
- How to structure LangGraph state? (ping @backend-lead)
```

---

## 🔍 DEBUGGING TIPS

### Backend Issues

```bash
# Check if server is running
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# View logs
docker-compose logs backend

# Check local database path
python -c "from services.gateway.src.config import get_settings; print(get_settings().database_path)"

# Check Redis connection when Docker Compose is running
redis-cli ping
# Expected: PONG

# Test LLM provider
python -c "from services.gateway.src.config import get_settings; from services.gateway.src.llm import create_llm_provider; print(create_llm_provider(get_settings()).name)"
```

### Frontend Issues

```bash
# Check API connection
curl http://localhost:8000/api/v1/health

# View network requests
# Open Chrome DevTools → Network tab

# Check local storage
# Open Chrome DevTools → Application → Local Storage

# Check browser console for errors
# Open Chrome DevTools → Console
```

### Database Issues

```bash
# Verify local SQLite database file
python -c "from services.gateway.src.storage import ChatRepository; ChatRepository('data/gateway.db'); print('ok')"

# List all tables
python -c "import sqlite3; c=sqlite3.connect('data/gateway.db'); print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")])"

# View query performance
EXPLAIN QUERY PLAN SELECT * FROM conversations;
```

---

## 📚 LEARNING RESOURCES

### For This Project

- **FastAPI:** https://fastapi.tiangolo.com/
- **LangGraph:** https://langchain-ai.github.io/langgraph/
- **React:** https://react.dev/
- **Zustand:** https://github.com/pmndrs/zustand
- **SQLAlchemy:** https://sqlalchemy.org/

### For Concepts

- **Multi-agent systems:** https://arxiv.org/abs/2308.12966
- **RAG:** https://arxiv.org/abs/2005.11401
- **Fine-tuning:** https://platform.openai.com/docs/guides/fine-tuning
- **Voice interfaces:** https://openai.com/research/whisper

---

## 🚨 CRITICAL PATHS (Don't Miss These)

### Current MVP Status

- [x] Basic chat
- [x] Persistent conversations
- [x] Local memory and document chunk search
- [x] Dynamic capability registry
- [x] Feedback capture and profile preferences
- [x] Browser speech-to-text input
- [x] Streaming response rendering in the UI
- [x] Local auth UI and admin user listing
- [x] Local workflow engine foundation
- [x] Deterministic decision scoring and reflection review
- [x] CI smoke tests and frontend build
- [ ] Full LangGraph multi-agent orchestration
- [ ] Full voice assistant service with TTS and continuous sessions
- [ ] Qdrant/Neo4j-backed memory graph
- [ ] Trading AI
- [ ] Code assistant module
- [ ] Production security hardening
- [ ] Kubernetes/Terraform deployment pipeline

### High Risk

- ⚠️ **LLM latency** → Test early, have fallback models
- ⚠️ **Voice lag** → WebRTC optimization critical
- ⚠️ **Database scaling** → Load test by Day 15
- ⚠️ **Fine-tuning feedback** → Start collecting by Day 14

---

## 📞 GET HELP

### Who to Ask

| Question | Ask |
|----------|-----|
| How do I...? | #help Slack channel |
| Architecture decision | @tech-lead |
| API question | @backend-lead |
| UI/Frontend | @frontend-lead |
| Infrastructure | @devops |
| Security concern | @security-lead |

### How to Report Issues

1. Check documentation first
2. Search GitHub issues
3. Ask in #help channel
4. Create GitHub issue with:
   - Clear title
   - What you tried
   - Expected vs actual result
   - Environment (OS, versions)

---

## ✅ LAUNCH CHECKLIST (Week 4)

Before going live:

- [ ] All core features working
- [ ] Tests passing (>80% coverage)
- [ ] Performance targets met
- [ ] Security audit passed
- [ ] Documentation complete
- [ ] Deployment rehearsal successful
- [ ] On-call team trained
- [ ] Monitoring/alerting set up
- [ ] Customer communication ready
- [ ] Incident runbooks prepared

---

## 📊 METRICS TO TRACK

Daily during development:

```
Backend:
- API latency (p50, p95, p99)
- Error rate
- Database query time
- Cache hit rate
- Concurrent users

Frontend:
- Bundle size
- Time to interactive
- Lighthouse score
- Component render time

Overall:
- Feature completion %
- Test coverage %
- Bug count
- Deployment frequency
```

---

## 🎓 NEXT STEPS

1. **Today:** Complete local setup ✓
2. **Tomorrow:** Attend kickoff meeting
3. **This Week:** 
   - Submit first PR (small change)
   - Review teammate's PR
   - Contribute to your assigned module
4. **Week 2:** Advanced modules, testing
5. **Week 3:** Advanced domains, optimization
6. **Week 4:** Polish, deploy, launch

---

## 📖 QUICK REFERENCE

### Port Assignments

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| Backend | 8000 | http://localhost:8000 |
| Database | 5432 | postgresql://localhost:5432 |
| Redis | 6379 | redis://localhost:6379 |
| Qdrant | 6333 | http://localhost:6333 |
| Neo4j | 7474 | http://localhost:7474 |

### Local User Accounts

Create a local account from the web UI or with `POST /api/v1/auth/signup`. Admin users can list
recent users from the sidebar after signing in.

### File Structure

```
shivaai-jarvis/
├── apps/
│   ├── web/                  # React frontend
│   └── desktop/              # Tauri (optional)
├── services/
│   ├── gateway/              # FastAPI main app
│   └── gateway/              # FastAPI main app
├── infra/                    # K8s, Terraform, Docker
├── scripts/                  # Automation
├── tests/                    # Test suites
├── docs/                     # Documentation
└── README.md
```

---

## 🎉 WELCOME TO THE TEAM!

You're helping build the future of AI. Questions? Blockers? Let us know in #help.

**Let's ship something great in 28 days.** 🚀

---

**Last updated:** 2026-05-30  
**Next update:** 2026-06-06 (weekly review)  
**Questions?** Create an issue or ask in Slack.
