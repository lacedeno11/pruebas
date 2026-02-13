# PEI Platform Backend - DERCAS TO-BE AGÉNTICO

Backend service for the Plataforma de Coordinación de Equipos de Instalación (PEI) using FastAPI, LangGraph, and SQLAlchemy.

## Features

- **FastAPI REST API** for OT (Orden de Trabajo) management
- **LangGraph-based Agent System** for intelligent task orchestration
- **Real-time Scheduling** with APScheduler for automated governance tasks
- **SQLAlchemy ORM** with SQLite for development (PostgreSQL ready for production)
- **CORS Support** for frontend integration
- **Mock API Mode** for development without external dependencies

## Prerequisites

- Python 3.10+
- pip (Python package manager)
- SQLite (included with Python)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - ORM
- `langchain` & `langchain-openai` - LLM integration
- `langgraph` - Agent orchestration
- `apscheduler` - Task scheduling
- `python-telegram-bot` - Telegram notifications
- `pydantic` - Data validation
- And other dependencies

### 2. Configure Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# System Mode: MOCK or PRODUCTION
SYSTEM_MODE=MOCK

# Database
DATABASE_URL=sqlite:///./pei.db

# LLM Configuration
OPENAI_API_KEY=your_actual_key_here

# Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Security
JWT_SECRET=change_this_to_a_secure_random_string

# CORS Origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Running the Server

### Development Mode (with auto-reload)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, access the interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## SYSTEM_MODE Explanation

### MOCK Mode (Default)

In `SYSTEM_MODE=MOCK`, the application:
- Uses simulated OT data from `MockApiService`
- Simulates 500ms latency for each API call
- Generates realistic mock data with 5-10 OTs
- Useful for development and testing without external dependencies
- Does NOT require real TELCOS or TelcoDrive API credentials

**Set this for development:**
```env
SYSTEM_MODE=MOCK
```

### PRODUCTION Mode

In `SYSTEM_MODE=PRODUCTION`, the application:
- Connects to real TELCOS and TelcoDrive APIs
- Requires valid API credentials and endpoints
- Uses actual database with real OT data
- Should be used with PostgreSQL for production reliability

**Set this for production deployment:**
```env
SYSTEM_MODE=PRODUCTION
```

## Architecture Overview

### Project Structure

```
backend/
├── app/
│   ├── core/                    # Core configuration
│   │   ├── config.py           # Settings management
│   │   ├── database.py         # SQLAlchemy setup
│   │   └── __init__.py
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── ot.py               # Orden de Trabajo (Work Order)
│   │   ├── cuadrilla.py        # Team/Crew model
│   │   ├── log_agente.py       # Agent action logs
│   │   └── __init__.py
│   ├── schemas/                 # Pydantic validation schemas
│   │   ├── ot_schema.py        # OT request/response schemas
│   │   ├── cuadrilla_schema.py # Cuadrilla schemas
│   │   ├── log_schema.py       # Log schemas
│   │   └── __init__.py
│   ├── services/                # Business logic services
│   │   ├── mock_api_service.py # Mock TELCOS/TelcoDrive APIs
│   │   ├── telcos_service.py   # TELCOS API wrapper
│   │   ├── telcodrive_service.py # TelcoDrive API wrapper
│   │   └── __init__.py
│   ├── agents/                  # LangGraph agent implementations
│   │   ├── router_agent.py     # Routes requests to appropriate agent
│   │   ├── ots_agent.py        # OT ingestion and management
│   │   ├── planificacion_agent.py # 3-phase assignment algorithm
│   │   ├── gobernanza_agent.py # Governance and compliance checks
│   │   ├── comunicacion_agent.py # Notifications
│   │   └── __init__.py
│   ├── api/                     # FastAPI routes
│   │   ├── ots.py              # /api/ots endpoints
│   │   ├── cuadrillas.py       # /api/cuadrillas endpoints
│   │   ├── agents.py           # /api/agents endpoints
│   │   ├── mock.py             # /api/mock endpoints (MOCK mode only)
│   │   ├── routes.py           # Router aggregation
│   │   └── __init__.py
│   ├── utils/                   # Utility functions
│   │   ├── geo.py              # Geographic calculations (Haversine, centroid)
│   │   ├── scheduler.py        # APScheduler setup for automated tasks
│   │   └── __init__.py
│   └── main.py                  # FastAPI app entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

### Core Components

#### 1. **Models** (ORM Layer)
- **OT (Orden de Trabajo)**: Work orders with status (PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
- **Cuadrilla**: Teams with capacity tracking and geographic centroid
- **LogAgente**: Audit trail for all agent actions

#### 2. **Schemas** (Validation Layer)
Pydantic models for request/response validation:
- `OTCreate`, `OTUpdate`, `OTResponse` for OT operations
- `CuadrillaResponse` with load percentage calculation
- `LogAgenteResponse` for action tracking

#### 3. **Services** (Business Logic)
- **MockApiService**: Simulates TELCOS and TelcoDrive APIs
- **TelcosService**: Factory pattern wrapper for TELCOS integration
- **TelcoDriveService**: Document validation service

#### 4. **Agents** (LangGraph State Machine)
Autonomous agents that perform specific tasks:

- **RouterAgent**: Classifies incoming requests and routes to appropriate agent
- **OTSAgent**: Ingests OTs from TELCOS, validates coordinates, persists to DB
- **PlanificacionAgent**: 3-phase assignment algorithm
  - Phase 1: Balanced assignment (1 OT per cuadrilla)
  - Phase 2: Centroid-based proximity assignment (<10km)
  - Phase 3: Nocturnal optimization
- **GobernanzaAgent**: Governance and compliance
  - Detention alerts (days 20, 25, 29)
  - Auto-cancellation after 30 days
  - PREPLANIFICADA alerts after 48 hours
  - Document validation for PUBLICO projects
- **ComunicacionAgent**: Notifications via Telegram and Email

#### 5. **Scheduler** (APScheduler)
Automated cron jobs:
- `09:00 daily` - Check detained OT alerts
- `00:01 daily` - Auto-cancel OTs detained >30 days
- `Every 6 hours` - Check PREPLANIFICADA alerts
- `00:00 daily` - Nightly route optimization

## API Endpoints

### OT Management
- `GET /api/ots` - List OTs (with filters: status, project_type, cuadrilla_id)
- `GET /api/ots/{id}` - Get specific OT
- `POST /api/ots` - Create/import new OT
- `PUT /api/ots/{id}` - Update OT
- `PUT /api/ots/{id}/status` - Change OT status (with validation)

### Cuadrilla Management
- `GET /api/cuadrillas` - List all cuadrillas
- `GET /api/cuadrillas/{id}` - Get specific cuadrilla
- `GET /api/cuadrillas/{id}/ots` - Get assigned OTs with load info

### Agent Operations
- `POST /api/agents/plan` - Trigger PlanificacionAgent manually
- `POST /api/agents/chat` - Chat interface with LangGraph
- `GET /api/agents/logs` - Query agent action logs

### Mock Endpoints (SYSTEM_MODE=MOCK only)
- `GET /api/mock/telcos/ots` - Get mock OTs
- `POST /api/mock/telcos/update_status` - Update mock OT status
- `GET /api/mock/telcodrive/documents` - Get mock document count

### Health Check
- `GET /` - Root endpoint returns status and system mode

## Database

### SQLite (Development)

Default configuration uses SQLite with auto-creation:
```env
DATABASE_URL=sqlite:///./pei.db
```

The database file (`pei.db`) is created automatically on first run.

### PostgreSQL (Production)

For production, update the database URL:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/pei_db
```

## Scheduling and Background Tasks

The application uses APScheduler to run automated governance tasks:

1. **Detention Alerts**: Triggered at 09:00 daily to notify about OTs detained >20 days
2. **Auto-Cancellation**: Runs at 00:01 daily to cancel OTs detained >30 days
3. **PREPLANIFICADA Alerts**: Runs every 6 hours to alert on OTs stuck in planning >48 hours
4. **Route Optimization**: Runs at 00:00 nightly for optimizing team routes

All scheduler jobs are logged and errors are captured in the application logs.

## Development Tips

### Running Tests

```bash
pytest -v
```

### Database Migrations

For production deployments, use Alembic:
```bash
alembic upgrade head
```

### Debugging

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Restarting from Scratch

To reset the database:
```bash
rm pei.db
```

The tables will be recreated on next server start.

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SYSTEM_MODE` | `MOCK` | `MOCK` or `PRODUCTION` |
| `DATABASE_URL` | `sqlite:///./pei.db` | Database connection string |
| `OPENAI_API_KEY` | - | OpenAI API key for LLM |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token for notifications |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server for email |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | - | Email address for sending |
| `SMTP_PASSWORD` | - | Email password/app password |
| `JWT_SECRET` | - | Secret key for JWT tokens |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins |

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Database Lock Error

SQLite may lock if multiple processes access it simultaneously. For production, use PostgreSQL.

### Import Errors

Ensure you're running from the backend directory and have installed all dependencies:
```bash
pip install -r requirements.txt
```

### ModuleNotFoundError

If you see import errors, the Python path may need adjustment. Run from the project root:
```bash
cd /path/to/backend
python -m uvicorn app.main:app --reload
```

## Performance Optimization

### Mock Mode Latency

The mock service simulates 500ms latency per request. This can be adjusted in `services/mock_api_service.py`:
```python
await asyncio.sleep(0.5)  # Change 0.5 to desired seconds
```

### Database Indexing

The OT model includes indexes on:
- `external_id` (unique)
- `status` (for fast filtering)

For production workloads, consider additional indexes on frequently filtered columns.

## Security Considerations

1. **Never commit `.env` files** - Always use `.env.example` as template
2. **Rotate JWT_SECRET** in production
3. **Use HTTPS** in production deployments
4. **Validate CORS_ORIGINS** for your specific frontend domain
5. **Implement rate limiting** for API endpoints
6. **Use environment-specific secrets** for production

## Contributing

See the main [README.md](../README.md) for contribution guidelines.

## Support

For issues or questions, please refer to the main project documentation or create an issue in the repository.

