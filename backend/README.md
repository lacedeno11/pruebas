# PEI Platform Backend

**PEI = Plataforma de Ejecución de Instalaciones** - AI-agentic platform for TELCONET work order (OT) management with LangGraph-based agent orchestration.

## Project Overview

The backend implements a comprehensive AI agent system for automating TELCONET's order-to-installation process. It includes:

- **5 LangGraph Agents** for orchestrating OT lifecycle
- **Mock API Layer** for development without production dependencies
- **Geographic Calculations** for proximity-based planning
- **Business Rule Engine** for governance and automation
- **Async Database Layer** with SQLAlchemy and PostgreSQL
- **RESTful APIs** with FastAPI
- **Scheduled Jobs** with APScheduler for automated governance checks

## Technology Stack

- **Python 3.13** - Runtime
- **FastAPI 0.109.0** - Web framework
- **LangGraph 0.0.50** - Agent orchestration
- **SQLAlchemy 2.0.25** - ORM
- **Pydantic 2.6.0** - Data validation
- **Alembic 1.13.1** - Database migrations
- **APScheduler 3.10.4** - Job scheduling

## Directory Structure

```
backend/
├── src/
│   ├── agents/           # LangGraph agent implementations
│   │   ├── state.py      # Shared PEIState TypedDict
│   │   ├── base_agent.py # Abstract BaseAgent class
│   │   ├── router_agent.py
│   │   ├── ots_agent.py
│   │   ├── planificacion_agent.py
│   │   ├── gobernanza_agent.py
│   │   ├── comunicacion_agent.py
│   │   ├── graph.py      # LangGraph state graph
│   │   └── executor.py   # Agent executor
│   ├── api/              # FastAPI route handlers
│   │   ├── ots_endpoints.py
│   │   ├── cuadrillas_endpoints.py
│   │   ├── agent_endpoints.py
│   │   └── dashboard_endpoints.py
│   ├── models/           # SQLAlchemy models
│   │   ├── base.py       # Declarative base and mixins
│   │   ├── ot.py         # OT model with enums
│   │   ├── cuadrilla.py  # Cuadrilla model
│   │   ├── agent_log.py  # Agent execution logs
│   │   └── __init__.py   # Model exports
│   ├── services/         # Business logic services
│   │   ├── mock_api_service.py    # Mock TELCOS API
│   │   ├── telcos_api_service.py  # Real TELCOS API
│   │   ├── api_factory.py         # API service factory
│   │   └── notification_service.py # Email/Telegram
│   ├── utils/            # Utility functions
│   │   ├── geo_utils.py           # Geographic calculations
│   │   └── business_rules.py      # Business rule validators
│   ├── config/
│   │   └── settings.py   # Pydantic settings with env vars
│   ├── database.py       # Async database setup
│   ├── main.py           # FastAPI app entry point
│   └── scheduler.py      # APScheduler job definitions
├── alembic/              # Database migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
├── tests/                # Test suite
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project metadata
├── .env.example          # Environment variables template
├── run.sh                # Development run script
├── Dockerfile            # Docker container definition
└── README.md            # This file
```

## Setup Instructions

### Prerequisites

- Python 3.13+
- PostgreSQL 16+ (or use Docker)
- pip or poetry for dependency management

### Local Development Setup

1. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database (with Docker):**
   ```bash
   docker run -d \
     --name pei_postgres \
     -e POSTGRES_DB=pei_db \
     -e POSTGRES_USER=pei_user \
     -e POSTGRES_PASSWORD=pei_pass \
     -p 5432:5432 \
     -v pei_postgres_data:/var/lib/postgresql/data \
     postgres:16
   ```

   Or update `.env` with your PostgreSQL connection string.

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start development server:**
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Or use the provided script:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYSTEM_MODE` | `MOCK` | Set to `MOCK` for development, `PROD` for production |
| `DATABASE_URL` | - | PostgreSQL async connection string |
| `OPENAI_API_KEY` | - | OpenAI API key for LLM (GPT-4) |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token for notifications |
| `SMTP_HOST` | `smtp.gmail.com` | Email server host |
| `SMTP_PORT` | `587` | Email server port |
| `MOCK_API_LATENCY_MS` | `500` | Simulated latency for mock API calls |

## System Architecture

### Agent Architecture (LangGraph)

The platform orchestrates 5 specialized agents in a state graph:

```
User Input / System Event
    ↓
[Router Agent] → Classify intent
    ↓
├─→ [OTS Agent] → Ingest OTs (UC-PEI-01)
├─→ [Planificación Agent] → Assign cuadrillas (UC-PEI-02)
├─→ [Gobernanza Agent] → Validate transitions (UC-PEI-08, UC-PEI-13)
└─→ [Comunicación Agent] → Send notifications
    ↓
Database Update + Logs
```

### Database Schema

**ots** table:
- `id` (Primary Key)
- `external_id` (Unique, from TELCOS)
- `status` (Enum: PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA)
- `project_type` (Enum: PUBLICO, PRIVADO, TERCERIZADO)
- `lat`, `long` (Geographic coordinates, nullable)
- `cliente_id`, `login_id` (Customer/service point IDs)
- `is_geo_error` (Flag for missing coordinates)
- `cuadrilla_id` (Foreign Key to cuadrillas)
- `assigned_at` (Assignment timestamp)
- `created_at`, `updated_at` (Timestamps)

**cuadrillas** table:
- `id` (Primary Key)
- `name` (Unique, team name)
- `type` (Enum: PRINCIPAL, RESERVA)
- `last_centroid_lat`, `last_centroid_long` (Geographic center)
- `max_daily_capacity` (Max OTs per day, default 10)
- `current_load` (Currently assigned OTs)
- `created_at`, `updated_at` (Timestamps)

**agent_logs** table:
- `id` (Primary Key)
- `ot_id` (Foreign Key, nullable)
- `agent_name` (Which agent executed)
- `accion` (Action description)
- `resultado` (SUCCESS/FAILURE/WARNING)
- `raw_llm_response` (Raw LLM output, JSON)
- `metadata` (Additional context, JSON)
- `timestamp` (When action occurred, indexed)

## Key Features

### 1. Planning Algorithm (3 Phases)

**Phase 1: Balance** - Assign 1 OT to each cuadrilla for equity
**Phase 2: Proximity** - Assign remaining OTs within 10km of cuadrilla centroid
**Phase 3: Nightly Normalization** - Reoptimize routes at 00:00 UTC

### 2. Geographic Calculations

- **Haversine Formula** - Calculate distance between coordinates
- **Centroid Calculation** - Compute geographic center of assigned OTs
- **Ecuador Bounds Validation** - Lat: -5 to 2, Lon: -81 to -75

### 3. Governance & Auto-Cancellation

- **Detention Tracking** - Alert on days 20, 25, 29; auto-cancel day 30
- **Inactivity Alerts** - PREPLANIFICADA >48hrs triggers high-priority alert
- **Document Validation** - PUBLICO projects require 29 TelcoDrive documents before FINALIZADA

### 4. Mock API Layer

Development mode uses `MockApiService` to simulate:
- OT retrieval with realistic Ecuador coordinates
- 500ms simulated latency to test loading states
- 2-3 error cases (missing coordinates) for ERROR_GEO testing
- 90% success rate for status update operations

## API Endpoints

### OT Management
- `GET /api/ots` - List OTs with filters
- `GET /api/ots/{ot_id}` - Single OT details
- `POST /api/ots/ingest` - Trigger OT ingestion
- `PATCH /api/ots/{ot_id}/status` - Update OT status
- `GET /api/ots/geo-errors` - List OTs with coordinate errors

### Cuadrilla Management
- `GET /api/cuadrillas` - List all cuadrillas
- `GET /api/cuadrillas/{cuadrilla_id}` - Cuadrilla details
- `GET /api/cuadrillas/{cuadrilla_id}/centroid` - Centroid coordinates
- `GET /api/cuadrillas/stats` - Capacity metrics
- `POST /api/cuadrillas` - Create cuadrilla

### Agent Interactions
- `POST /api/agents/execute` - Execute agent command
- `POST /api/agents/plan` - Trigger planning
- `GET /api/agents/logs` - Query agent logs
- `POST /api/agents/validate-transition` - Validate OT transition
- `WebSocket /api/agents/ws/chat` - Real-time chat interface

### Dashboard Analytics
- `GET /api/dashboard/metrics` - Key metrics
- `GET /api/dashboard/kanban` - Kanban board data
- `GET /api/dashboard/map` - Map visualization data
- `GET /api/dashboard/alerts` - Active governance alerts

### System
- `GET /health` - Health check
- `GET /api/config` - Frontend configuration

## Use Cases

### UC-PEI-01: OT Download & Registration
Validates 100% field mapping, marks ERROR_GEO if coordinates missing, notifies PM.

### UC-PEI-02: Automatic Planning
Assigns OTs via 3-phase algorithm, no overload, <10km validation.

### UC-PEI-08: Auto-Cancellation
Day 30 detention auto-cancel with alerts on days 20/25/29.

### UC-PEI-13: Drag & Drop Management
Real-time validation with modal for detention reasons.

## Development Workflow

1. **Mock Mode** - Start with `SYSTEM_MODE=MOCK` for full feature testing
2. **Test Agents** - Use `/api/agents/execute` endpoint with test inputs
3. **Check Logs** - Review agent decisions in `/api/agents/logs`
4. **Monitor Dashboard** - Use frontend Kanban/Map to visualize OTs

## Testing

Run tests with pytest:
```bash
pytest -v tests/
```

Run tests with coverage:
```bash
pytest --cov=src tests/
```

## Deployment

### Docker

```bash
docker build -t pei-backend:latest .
docker run -p 8000:8000 --env-file .env pei-backend:latest
```

### Docker Compose (Full Stack)

From root directory:
```bash
docker-compose up -d
```

This starts:
- PostgreSQL 16 on port 5432
- Backend on port 8000
- Frontend on port 3000

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running: `docker ps | grep postgres`
- Check `.env` DATABASE_URL format: `postgresql+asyncpg://user:pass@localhost:5432/db`
- Run migrations: `alembic upgrade head`

### Mock API Not Working
- Check `SYSTEM_MODE=MOCK` in `.env`
- Verify `MOCK_API_LATENCY_MS` is set (default 500)
- Check logs for API service errors

### Agent Execution Failures
- Check OPENAI_API_KEY is valid
- Review agent_logs table for error details
- Check `/api/agents/logs` endpoint

## Contributing

1. Create feature branch: `git checkout -b feature/agent-name`
2. Make changes following project structure
3. Add tests for new features
4. Run linting: `black src/ && isort src/`
5. Submit pull request

## License

MIT License - See LICENSE file for details

## Contact

For questions or issues, contact the TELCONET development team at dev@telconet.ec

