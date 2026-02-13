# 🏢 PEI Platform - DERCAS TO-BE AGÉNTICO

**Plataforma de Coordinación de Equipos de Instalación (PEI)**

A comprehensive, intelligent work order management system for telecommunications installation teams, powered by AI agents and modern web technologies.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [SYSTEM_MODE Configuration](#system_mode-configuration)
- [Use Cases](#use-cases)
- [Agent Architecture](#agent-architecture)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Development](#development)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)

## 🎯 Project Overview

The **PEI Platform** is an intelligent work order coordination system designed for TELCONET's installation teams (cuadrillas). It combines:

- **Real-time Work Order Management**: Drag-and-drop Kanban board for visualizing work order status
- **Geographic Intelligence**: Real-time map visualization of team locations and work orders
- **AI-Powered Automation**: LangGraph-based agent system for intelligent task orchestration
- **Autonomous Governance**: Automated compliance checks, detention alerts, and team optimization

### Key Features

✅ **Drag & Drop Kanban Board** - Visual workflow management with 6 status columns  
✅ **Geographic Visualization** - Real-time map showing OT and team locations  
✅ **AI Assistant Chat** - Conversational interface for system operations  
✅ **Automated Scheduling** - Cron-based governance tasks (detention checks, auto-cancellation)  
✅ **Real-time Updates** - React Query with 30-second refresh intervals  
✅ **Mobile Responsive** - Works seamlessly on desktop, tablet, and mobile  
✅ **Mock & Production Modes** - Seamless switching for development and deployment  
✅ **Professional UI** - TELCONET branding with modern component design  

## 🏗️ Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React/Vite)                       │
│  ┌────────────────┬──────────────┬─────────────────────────┐    │
│  │  Kanban Board  │  Geographic   │   ChatSidebar (AI)      │    │
│  │  (Drag/Drop)   │  Map View     │   (LangGraph)           │    │
│  └────────────────┴──────────────┴─────────────────────────┘    │
│           │                │              │                      │
└───────────┼────────────────┼──────────────┼──────────────────────┘
            │                │              │
     ┌──────▼────────────────▼──────────────▼──────────┐
     │  API Gateway & Proxy (Vite Dev Server)          │
     │  localhost:5173 → http://localhost:8000/api     │
     └──────────────────────────────────────────────────┘
            │
     ┌──────▼──────────────────────────────────────────┐
     │    BACKEND (Python/FastAPI)                      │
     │    ┌──────────────────────────────────────────┐  │
     │    │      FastAPI Application (Port 8000)     │  │
     │    │  ┌──────────────────────────────────┐    │  │
     │    │  │   API Routes                     │    │  │
     │    │  │  • /api/ots                      │    │  │
     │    │  │  • /api/cuadrillas               │    │  │
     │    │  │  • /api/agents                   │    │  │
     │    │  │  • /api/mock (dev)               │    │  │
     │    │  └──────────────────────────────────┘    │  │
     │    │           │                              │  │
     │    │  ┌────────▼──────────────────────────┐   │  │
     │    │  │   LangGraph Agent System          │   │  │
     │    │  │  ┌──────────────────────────────┐ │   │  │
     │    │  │  │ Router Agent → Routes to:     │ │   │  │
     │    │  │  │ • OTS Agent                   │ │   │  │
     │    │  │  │ • Planificación Agent         │ │   │  │
     │    │  │  │ • Gobernanza Agent            │ │   │  │
     │    │  │  │ • Comunicación Agent          │ │   │  │
     │    │  │  └──────────────────────────────┘ │   │  │
     │    │  └────────────────────────────────────┘   │  │
     │    │           │                              │  │
     │    │  ┌────────▼──────────────────────────┐   │  │
     │    │  │   SQLAlchemy ORM                 │   │  │
     │    │  │  • OT Model                      │   │  │
     │    │  │  • Cuadrilla Model               │   │  │
     │    │  │  • LogAgente Model               │   │  │
     │    │  └────────────────────────────────────┘   │  │
     │    │           │                              │  │
     │    │  ┌────────▼──────────────────────────┐   │  │
     │    │  │   Database Layer                 │   │  │
     │    │  │  • SQLite (dev)                  │   │  │
     │    │  │  • PostgreSQL (prod)             │   │  │
     │    │  └────────────────────────────────────┘   │  │
     │    │           │                              │  │
     │    │  ┌────────▼──────────────────────────┐   │  │
     │    │  │   External Services               │   │  │
     │    │  │  • OpenAI API (LLM)               │   │  │
     │    │  │  • TELCOS API (Mock/Real)         │   │  │
     │    │  │  • TelcoDrive API (Mock/Real)     │   │  │
     │    │  │  • Telegram/Email (Notifications)│   │  │
     │    │  └────────────────────────────────────┘   │  │
     │    └──────────────────────────────────────────┘  │
     └──────────────────────────────────────────────────┘
            │
     ┌──────▼──────────────────────────┐
     │  APScheduler Cron Jobs           │
     │  • Detention alerts (09:00 daily)│
     │  • Auto-cancel (00:01 daily)     │
     │  • PREPLANIFICADA checks (6h)    │
     │  • Route optimization (00:00)    │
     └──────────────────────────────────┘
```

## 💻 Technology Stack

### Backend
| Technology | Purpose | Version |
|-----------|---------|---------|
| Python | Language | 3.10+ |
| FastAPI | Web Framework | Latest |
| SQLAlchemy | ORM | 2.0.41 |
| Pydantic | Data Validation | 2.11.5 |
| LangChain | LLM Integration | 0.3.25 |
| LangGraph | Agent Orchestration | Latest |
| APScheduler | Job Scheduling | Latest |
| Uvicorn | ASGI Server | 0.34.2 |

### Frontend
| Technology | Purpose | Version |
|-----------|---------|---------|
| React | UI Framework | ^18 |
| Vite | Build Tool | ^5 |
| @dnd-kit | Drag & Drop | ^6 |
| react-leaflet | Maps | ^4 |
| @tanstack/react-query | Data Fetching | ^5 |
| Axios | HTTP Client | ^1 |
| react-toastify | Notifications | ^10 |

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** with pip
- **Node.js 18+** with npm

### 1. Start Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env if needed (defaults work for dev)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: **http://localhost:8000**  
API Docs: **http://localhost:8000/docs**

### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend available at: **http://localhost:5173**

## 📁 Project Structure

```
.
├── backend/                          # Python/FastAPI backend
│   ├── app/
│   │   ├── core/                    # Configuration & database
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── services/                # API service wrappers
│   │   ├── agents/                  # LangGraph agents
│   │   ├── api/                     # FastAPI routes
│   │   ├── utils/                   # Utilities (geo, scheduler)
│   │   ├── graph.py                 # LangGraph state machine
│   │   └── main.py                  # FastAPI app
│   ├── requirements.txt             # Dependencies
│   ├── .env.example                 # Environment template
│   └── README.md                    # Backend docs
├── frontend/                         # React/Vite frontend
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── hooks/                   # Custom hooks
│   │   ├── services/                # API client
│   │   ├── types/                   # Type definitions
│   │   ├── App.jsx                  # Main component
│   │   ├── App.css                  # Styles
│   │   └── main.jsx                 # Entry point
│   ├── package.json                 # Dependencies
│   ├── vite.config.js               # Build config
│   └── README.md                    # Frontend docs
├── .gitignore                       # Git ignore
└── README.md                        # This file
```

## 🔧 Setup Instructions

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

See `backend/README.md` for detailed instructions.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

See `frontend/README.md` for detailed instructions.

## 🌍 Environment Variables

### SYSTEM_MODE

**MOCK** (Development - Default):
- Uses simulated OT data
- No external API calls
- 500ms latency simulation
- Perfect for testing without dependencies

**PRODUCTION**:
- Connects to real TELCOS API
- Real TelcoDrive integration
- Requires API credentials
- PostgreSQL database

### Key Variables

```env
SYSTEM_MODE=MOCK                        # MOCK or PRODUCTION
DATABASE_URL=sqlite:///./pei.db         # Database connection
OPENAI_API_KEY=sk-...                   # OpenAI LLM API
TELEGRAM_BOT_TOKEN=...                  # Telegram notifications
SMTP_HOST=smtp.gmail.com                # Email notifications
JWT_SECRET=your-secret-key              # Security token
CORS_ORIGINS=http://localhost:5173      # Frontend origin
```

## 📖 Use Cases

### UC-PEI-01: OT Ingestion
- **Actor**: TELCOS System
- **Process**: Automatically fetch and validate new work orders
- **Validation**: Check geographic coordinates, mark errors

### UC-PEI-02: Planning & Assignment
- **Algorithm**: 3-phase (balance, proximity <10km, optimization)
- **Output**: OTs assigned to teams, centroids calculated
- **Logging**: All assignments tracked in audit logs

### UC-PEI-08: Governance & Alerts
- **Detention Checks**: Daily at 09:00
- **Alert Days**: 20, 25, 29 days of detention
- **Auto-Cancel**: >30 days → ANULADA status

### UC-PEI-13: Document Validation
- **Rule**: PUBLICO projects require 29 documents
- **Check**: Before allowing FINALIZADA status
- **Source**: TelcoDrive document count

## 🤖 Agent Architecture

### Agents

1. **Router Agent** - Classifies requests and routes to appropriate agent
2. **OTS Agent** - Ingests and validates work orders
3. **Planificación Agent** - Assigns OTs to teams (3-phase algorithm)
4. **Gobernanza Agent** - Monitors compliance and governance
5. **Comunicación Agent** - Sends notifications (Telegram, Email)

### LangGraph State Machine

```
Message → Router → [Branch based on classification]
                  ├→ OTS → Planificación → End
                  ├→ Gobernanza → Comunicación → End
                  └→ Other → End
```

## 📡 API Endpoints

### Work Orders
- `GET /api/ots` - List with filters
- `GET /api/ots/{id}` - Get specific OT
- `POST /api/ots` - Create new OT
- `PUT /api/ots/{id}/status` - Change status

### Teams
- `GET /api/cuadrillas` - List teams
- `GET /api/cuadrillas/{id}/ots` - Team's OTs

### Agents
- `POST /api/agents/chat` - Chat with AI
- `GET /api/agents/logs` - View agent logs

### Mock (dev only)
- `GET /api/mock/telcos/ots` - Mock OT data
- `GET /api/mock/telcodrive/documents` - Mock documents

## 🚀 Deployment

### Development
- Python 3.10+, Node.js 18+
- SQLite database
- Ports: 8000 (backend), 5173 (frontend)

### Production
- Docker containers
- PostgreSQL database
- Nginx reverse proxy
- HTTPS/TLS required

## 💻 Development

### Adding Features

**Backend**:
1. Create schema in `schemas/`
2. Create model in `models/`
3. Create API handler in `api/`
4. Include in routes

**Frontend**:
1. Create component in `components/`
2. Create hook in `hooks/` if needed
3. Import in parent component
4. Add styling to App.css

## 🤝 Contributing

1. Read this README and project READMEs
2. Follow code style (PEP 8 for Python, ESLint for JS)
3. Write tests for new features
4. Update documentation
5. Submit PR with clear description

## 🐛 Troubleshooting

**Backend won't start**: Ensure Python 3.10+, dependencies installed, port 8000 free

**Frontend connection error**: Check backend is running, verify CORS_ORIGINS in .env

**Database errors**: Remove `pei.db`, will recreate on startup

See `backend/README.md` and `frontend/README.md` for detailed troubleshooting.

---

**PEI Platform v1.0.0 - DERCAS TO-BE AGÉNTICO**

For detailed documentation, see:
- `backend/README.md` - Backend setup and configuration
- `frontend/README.md` - Frontend setup and features
