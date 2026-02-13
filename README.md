# PEI - Plataforma de Ejecución de Instalaciones

**An intelligent work order management system powered by autonomous AI agents for optimized crew assignment and governance automation.**

---

## 📋 Project Overview

**PEI** (Plataforma de Ejecución de Instalaciones) is an advanced work order management platform that leverages AI agents, intelligent route planning, and real-time governance to optimize field operations for installation service companies.

### Purpose

The platform addresses critical challenges in field service operations:
- **Manual crew assignment inefficiency**: Automate OT-to-crew matching based on location and capacity
- **Lack of real-time governance**: Auto-enforce business rules (detention alerts, auto-cancellation)
- **Communication bottlenecks**: Multi-channel notifications (Telegram, Email) via AI agents
- **Geographic optimization**: Minimize crew travel using smart centroid calculation

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Kanban Board │ Map View │ Statistics │ Agent Chat Sidebar │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────────┘
                 │ HTTP/REST (Port 5173)
┌────────────────▼────────────────────────────────────────────────┐
│            Backend API (FastAPI + LangGraph)                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  API Routers  │  5 AI Agents  │  Business Logic       │    │
│  │  - OTs        │  - Router     │  - Planning Service   │    │
│  │  - Cuadrillas │  - OTS        │  - Governance        │    │
│  │  - Agents     │  - Planning   │  - Mock APIs         │    │
│  │              │  - Governance │                       │    │
│  │              │  - Comunicación│                       │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────┬─────────────────────────────────────────────┬──┘
             │ SQL (Port 5432)                      │ Scheduled Jobs
             │                                      │ (APScheduler)
┌────────────▼──────────────────────────────────────────────────┐
│              PostgreSQL Database                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  ots  │  cuadrillas  │  asignacion  │  logs_agentes     │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 1. **Multi-Agent Orchestration** (LangGraph)
Five specialized AI agents working in concert:
- **RouterAgent**: Classifies natural language commands into system actions
- **OTSAgent**: Ingests OTs, validates data, flags geo-errors
- **PlanificacionAgent**: Executes 3-phase crew assignment algorithm
- **GobernanzaAgent**: Enforces governance rules, auto-cancellations, alert generation
- **ComunicacionAgent**: Sends multi-channel notifications (Telegram, Email)

### 2. **Intelligent Crew Assignment** (3-Phase Planning)
- **Phase 1 - Balance**: Distribute 1 OT per Principal crew for equity
- **Phase 2 - Proximity**: Assign remaining OTs within 10km of crew centroid
- **Phase 3 - Nocturnal Optimization**: Recalculate crew centroids nightly at 00:00

### 3. **Autonomous Governance** (APScheduler)
- **Detention Alerts**: Day 20, 25, 29 for OTs stuck in DETENIDA status
- **Auto-Cancellation**: Automatically cancel OTs detained > 30 days
- **Pre-Planning Alerts**: High-priority notification for OTs in PREPLANIFICADA > 48 hours

### 4. **Interactive UI** (React + Tailwind)
- **Kanban Board**: Drag-drop OTs between status columns with detention reason modal
- **Real-Time Map**: Leaflet integration showing OT locations and crew centroids
- **Statistics Dashboard**: Key metrics (total OTs, status breakdown, utilization %)
- **Agent Chat Sidebar**: Natural language interface for triggering system actions
- **Advanced Filters**: Status, project type, cuadrilla, date range filtering

### 5. **Development Mode** (Mock APIs)
- Complete mock data generation (15-20 OTs with realistic data)
- No external API dependencies required
- Perfect for testing and demonstration

---

## 🛠 Tech Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | FastAPI | 0.109.0 |
| **Server** | Uvicorn | 0.27.0 |
| **ORM** | SQLAlchemy | 2.0.25 |
| **Migrations** | Alembic | 1.13.1 |
| **AI/Agents** | LangGraph | 0.0.26 |
| **LLM Framework** | LangChain | 0.1.6 |
| **LLM Provider** | OpenAI | 1.12.0 |
| **Geo Calculations** | Geopy | 2.4.1 |
| **Scheduler** | APScheduler | 3.10.4 |
| **Notifications** | python-telegram-bot | 20.7 |
| **Database** | PostgreSQL 15 / SQLite | - |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | React | 18+ |
| **Build Tool** | Vite | Latest |
| **Styling** | Tailwind CSS | 3.4.1 |
| **HTTP Client** | Axios | 1.6.5 |
| **Drag & Drop** | dnd-kit | 6.1.0 |
| **Mapping** | Leaflet + react-leaflet | 4.2.1 |
| **Notifications** | react-toastify | 10.0.4 |
| **Date Handling** | date-fns | 3.3.1 |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| **Containerization** | Docker & Docker Compose |
| **Database** | PostgreSQL 15 |
| **Version Control** | Git |

---

## 📦 Installation

### Prerequisites
- **Docker & Docker Compose** (Recommended for all platforms)
- OR **Python 3.13+**, **Node.js 20+**, **PostgreSQL 15** (for local setup)
- **OpenAI API Key** (optional, required for LLM features)

### Quick Start (Docker Compose - Recommended)

```bash
# 1. Clone repository
git clone https://github.com/lacedeno11/pruebas.git
cd pruebas

# 2. Create environment file (copy from template)
cp backend/.env.example backend/.env

# 3. Add your OpenAI API key (optional, can use mock mode)
# Edit backend/.env and set:
# OPENAI_API_KEY=sk-your-actual-key-here
# SYSTEM_MODE=MOCK  (for development without external APIs)

# 4. Start all services
docker-compose up -d

# 5. Access applications
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs (Swagger): http://localhost:8000/docs
```

### Local Setup (Without Docker)

#### Backend Setup
```bash
# 1. Navigate to backend
cd backend

# 2. Create Python virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with your configuration

# 5. Initialize database (if using PostgreSQL)
alembic upgrade head

# 6. Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start development server
npm run dev
```

---

## ⚙️ Environment Configuration

### Backend Environment Variables (.env)

```ini
# System Mode: MOCK (development) or PRODUCTION (external APIs)
SYSTEM_MODE=MOCK

# Database Configuration
DATABASE_URL=sqlite:///./pei.db
# For PostgreSQL: postgresql://user:password@localhost/pei_db

# OpenAI API (required for agent LLM features)
OPENAI_API_KEY=sk-your-key-here

# External API Endpoints (optional)
TELCOS_API_BASE_URL=http://localhost:8001
TELCODRIVE_API_BASE_URL=http://localhost:8002

# Telegram Notifications (optional)
TELEGRAM_BOT_TOKEN=your-bot-token

# Email Configuration (optional)
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=noreply@yourcompany.com

# Business Rules Configuration
ALERT_DETENTION_DAYS=20,25,29        # Days to trigger detention alerts
AUTO_CANCEL_DAYS=30                  # Days to auto-cancel detained OTs
PREPLANNED_ALERT_HOURS=48            # Hours before pre-planning timeout alert
PROXIMITY_RADIUS_KM=10               # Max distance for crew proximity assignment
```

### Frontend Environment Variables (.env.local)

```ini
# API Backend URL
VITE_API_URL=http://localhost:8000
```

---

## 🔌 API Documentation

### OT Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ots/sync` | Sync OTs from mock/external API |
| `GET` | `/api/ots/` | List all OTs with optional filters |
| `GET` | `/api/ots/{ot_id}` | Get single OT by ID |
| `PUT` | `/api/ots/{ot_id}` | Update OT fields |
| `PUT` | `/api/ots/{ot_id}/status` | Update OT status with validation |
| `DELETE` | `/api/ots/{ot_id}` | Soft delete OT (set status=ANULADA) |

### Cuadrilla Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/cuadrillas/` | Create new cuadrilla |
| `GET` | `/api/cuadrillas/` | List all cuadrillas |
| `GET` | `/api/cuadrillas/{cuadrilla_id}` | Get single cuadrilla |
| `PUT` | `/api/cuadrillas/{cuadrilla_id}` | Update cuadrilla |
| `GET` | `/api/cuadrillas/{cuadrilla_id}/assignments` | Get assigned OTs |
| `PUT` | `/api/cuadrillas/{cuadrilla_id}/centroid` | Recalculate centroid |

### Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/agents/chat` | Send natural language command to router |
| `POST` | `/api/agents/plan` | Trigger planning algorithm |
| `POST` | `/api/agents/govern` | Manually trigger governance checks |
| `GET` | `/api/agents/logs` | Get agent execution logs |

---

## 🤖 Agent System

### RouterAgent
Classifies natural language user inputs into system actions using GPT-4 Turbo with custom prompt template.

**Actions**:
- `sync_ots`: Download/sync work orders from API
- `plan_assignment`: Trigger crew assignment algorithm
- `check_governance`: Review detention alerts and auto-cancellations
- `send_notification`: Communicate with stakeholders
- `query_status`: Get current system state

### OTSAgent
Ingests OTs from MockApiService or external APIs, validates all fields and geographic coordinates, marks OTs with geo_error flag if invalid, persists to database.

### PlanificacionAgent
Executes intelligent 3-phase crew assignment:
- Phase 1: Distribute 1 OT per Principal crew for equity
- Phase 2: Assign remaining OTs within 10km of crew centroid
- Phase 3: Nightly centroid recalculation at 00:00

### GobernanzaAgent
Enforces business governance rules:
- Detention alerts on days 20, 25, 29
- Auto-cancellation of OTs detained > 30 days
- Pre-planning timeout alerts for > 48 hours
- Project-specific validation (29 documents for PUBLICO projects)

### ComunicacionAgent
Sends multi-channel notifications via Telegram (technical staff) and Email (PMs/clients) with LLM-generated contextual messages.

---

## 📐 Business Rules

### OT Status State Machine

```
PREPLANIFICADA → PLANIFICADA → ASIGNADO_TAREA → FINALIZADA
     ↓                ↓              ↓
   ANULADA        DETENIDA → PLANIFICADA/ANULADA
```

### Detention Alert Rules
- Day 20: Alert sent
- Day 25: Alert sent
- Day 29: Critical alert
- Day 30: Auto-cancel to ANULADA

### Crew Assignment Rules
- Initial Balance: 1 OT per Principal crew minimum
- Proximity: Max 10km from crew centroid
- Capacity: current_load < capacity
- Priority: PUBLICO (1) > PRIVADO (2) > TERCERIZADO (3)
- Centroid Recalc: Daily at 00:00 UTC

---

## 🚀 Development Guide

### Running Services Separately

**Backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export SYSTEM_MODE=MOCK
uvicorn app.main:app --reload
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

### Using Mock Mode
Perfect for development without external APIs:
```bash
SYSTEM_MODE=MOCK
OPENAI_API_KEY=sk-test-key  # Placeholder OK
```

### Testing Agent Workflows

```bash
# Sync OTs
curl -X POST http://localhost:8000/api/ots/sync

# Trigger planning
curl -X POST http://localhost:8000/api/agents/plan \
  -H "Content-Type: application/json" \
  -d '{"ot_ids": [1, 2, 3], "force_balance": false}'

# Check governance
curl -X POST http://localhost:8000/api/agents/govern
```

---

## 📡 Deployment

### Docker Compose

```bash
docker-compose up -d        # Start all services
docker-compose down         # Stop services
docker-compose logs -f      # Follow all logs
```

### Production Considerations
- Set `SYSTEM_MODE=PRODUCTION` in .env
- Use PostgreSQL database (not SQLite)
- Configure real API credentials (OpenAI, Telegram, Email)
- Enable HTTPS/TLS for all communications
- Implement API key authentication
- Use environment secrets management
- Set up monitoring, logging, and alerting
- Regular security audits and dependency updates
- Automated backups for database

### Kubernetes Deployment
Deploy using Kubernetes manifests for horizontal scaling, automated healing, and production-grade reliability.

---

## 🤝 Contributing

### Code Style
- **Python**: PEP 8 with Black formatter
- **JavaScript/React**: ESLint + Prettier

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: Feature branches

### Pull Request Process
1. Create feature branch from `develop`
2. Make changes with clear commit messages
3. Submit PR with description
4. Code review by maintainers
5. Merge after approval

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 📞 Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/lacedeno11/pruebas/issues
- Documentation: Comprehensive inline code documentation

---

## 🎯 Roadmap

### Phase 2
- Mobile app (React Native)
- Advanced analytics dashboard
- Machine learning-based crew matching
- Real-time GPS tracking
- WhatsApp notifications

### Phase 3
- IoT sensor integration
- Predictive maintenance
- Customer portal
- Advanced reporting engine
- Custom workflow builder

---

**Built with FastAPI, LangGraph, React, Tailwind CSS, and powered by OpenAI. 🚀**

*Repository: https://github.com/lacedeno11/pruebas*
