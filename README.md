# PEI Agéntico Platform

**PEI Agéntico** is an intelligent work order management system powered by LangGraph and AI agents. It automates the planning, assignment, and optimization of technical work orders (OTs) across distributed crews in Ecuador, with integrated validation, governance, and communication workflows.

## Overview

The platform uses a multi-agent architecture where specialized LLM-powered agents handle specific functions:

- **Router Agent**: Classifies incoming requests and system events
- **OTS Agent**: Ingests and validates work orders from TELCOS API
- **Planificación Agent**: Implements smart geographic-based crew assignment (3-phase algorithm)
- **Gobernanza Agent**: Enforces business rules, timeouts, and auto-cancellations
- **Comunicación Agent**: Sends notifications via Telegram and email
- **Chat Agent**: Provides conversational interface for users

```
[TELCOS API] → [OTS Ingestion] → [Planning] → [Validation] → [Governance] → [Communication]
                                                    ↓
                                            [Database] ← [Map Visualization]
                                                    ↓
                                            [Crew Assignment] ← [React Frontend]
```

## Prerequisites

- **Python 3.13+** with pip
- **Node.js 24+** with npm
- **SQLite** (included) or PostgreSQL (for production)
- **Git**

## Installation

### Backend Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Key environment variables:**
   - `SYSTEM_MODE`: Set to `MOCK` for development (uses mock API service)
   - `OPENAI_API_KEY`: Your OpenAI API key (for ChatGPT models)
   - `LLM_MODEL`: Model to use (default: `gpt-4`)
   - `DATABASE_URL`: SQLite by default, PostgreSQL for production
   - `TELEGRAM_BOT_TOKEN`: For Telegram notifications (optional)
   - `SMTP_*`: Email configuration for notifications

### Frontend Setup

1. **Install Node dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **No additional configuration needed** - frontend automatically proxies API calls to backend

## Running the Application

### Backend
```bash
cd backend
python run.py
```

The API will start at `http://localhost:8000`

**API Documentation:** Open `http://localhost:8000/docs` in your browser for interactive OpenAPI/Swagger documentation

### Frontend
```bash
cd frontend
npm run dev
```

The UI will start at `http://localhost:5173`

### Both (in separate terminals)
Terminal 1:
```bash
cd backend && python run.py
```

Terminal 2:
```bash
cd frontend && npm run dev
```

Then open your browser to `http://localhost:5173`

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SYSTEM_MODE` | `MOCK` | `MOCK` for testing, otherwise uses real APIs |
| `DATABASE_URL` | `sqlite:///./pei.db` | Database connection string |
| `OPENAI_API_KEY` | — | Required for LLM agents (get from openai.com) |
| `LLM_MODEL` | `gpt-4` | Language model to use |
| `TELCOS_API_URL` | — | External TELCOS API endpoint |
| `TELCOS_API_KEY` | — | Authentication for TELCOS API |
| `TELEGRAM_BOT_TOKEN` | — | For Telegram notifications |
| `TELEGRAM_CHAT_IDS` | — | Comma-separated chat IDs (e.g., `123,456,789`) |
| `SMTP_HOST` | `smtp.gmail.com` | Email server |
| `SMTP_PORT` | `587` | Email port (TLS) |
| `SMTP_USER` | — | Email account for sending notifications |
| `SMTP_PASSWORD` | — | Email password |
| `MAX_DISTANCE_KM` | `10` | Maximum distance for crew assignment (km) |
| `MAX_CUADRILLA_CAPACITY` | `20` | Maximum OTs per crew per day |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed frontend origins |

## API Endpoints

All endpoints are documented at `/docs` when backend is running.

### OT Management
- `GET /api/ots` - List all work orders (with filters)
- `GET /api/ots/{ot_id}` - Get single OT details
- `PATCH /api/ots/{ot_id}/status` - Update OT status (drag & drop)
- `POST /api/ots/sync` - Sync new OTs from TELCOS
- `DELETE /api/ots/{ot_id}` - Soft delete (mark as ANULADA)

### Crew Management
- `GET /api/cuadrillas` - List all crews
- `GET /api/cuadrillas/{cuadrilla_id}` - Get crew details
- `GET /api/cuadrillas/{cuadrilla_id}/ots` - Get crew's assigned OTs
- `POST /api/cuadrillas` - Create new crew
- `PATCH /api/cuadrillas/{cuadrilla_id}` - Update crew details
- `GET /api/cuadrillas/{cuadrilla_id}/centroid` - Get crew's geographic centroid

### Planning
- `POST /api/planning/auto` - Trigger automatic planning algorithm
- `POST /api/planning/assign` - Manual OT assignment to crew
- `POST /api/planning/optimize` - Optimize routes (nightly)
- `GET /api/planning/status` - Planning statistics and metrics

### Validation
- `POST /api/validate/transition` - Validate OT status change
- `GET /api/validate/documents/{ot_id}` - Check document requirements
- `POST /api/validate/assignment` - Validate crew assignment

### Chat
- `POST /api/chat` - Send message to conversational agent

## Architecture Overview

### Backend Stack
- **FastAPI**: REST API framework
- **LangGraph**: Agent orchestration and state management
- **SQLAlchemy**: ORM for database operations
- **Pydantic**: Data validation
- **AsyncIO**: Asynchronous operations
- **Schedule**: Job scheduling for governance rules

### Frontend Stack
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **@dnd-kit**: Drag & drop functionality
- **Leaflet**: Geographic mapping
- **Axios**: HTTP client
- **React Router**: Navigation
- **React Toastify**: Notifications

### Database Schema
- **OT**: Work orders with status, location, project type
- **Cuadrilla**: Field crews with capacity and geographic centroid
- **Assignment**: Links between OTs and crews
- **AgentLog**: Audit trail of all agent actions

## Agent Architecture

### Router Agent
Classifies incoming requests into actions:
- `INGEST`: Download new OTs
- `PLAN`: Assign OTs to crews
- `VALIDATE`: Check business rules
- `NOTIFY`: Send alerts
- `GOVERNANCE`: Check timeouts and auto-cancel
- `CHAT`: Answer questions

### OTS Agent
Ingests and validates work orders:
1. Fetches from TELCOS API (or mock service)
2. Validates geographic coordinates (Ecuador bounds check)
3. Detects duplicates and conflicts
4. Logs errors and warnings
5. Notifies PM of issues

### Planificación Agent (3-Phase Algorithm)

**Phase 1 - Initial Balance:**
- Assigns 1 unplanned OT to each crew with zero assignments
- Prioritizes PÚBLICO projects (highest priority)

**Phase 2 - Centroid Proximity:**
- Calculates each crew's centroid from currently assigned OTs
- For remaining unassigned OTs, finds crews within MAX_DISTANCE_KM (10 km)
- Assigns to crew with most available capacity
- Flags OTs with no nearby crews for manual review

**Phase 3 - Route Optimization (Daily at 00:00 UTC):**
- Recalculates all crew centroids
- Stores new centroids in database
- Generates daily optimization report

### Gobernanza Agent

Enforces business rules on a schedule:

**48-Hour Alert:**
- Flags OTs in PREPLANIFICADA status for >48 hours
- Alerts Coordinator OPU to take action

**DETENIDA Escalation:**
- Day 20: Warning alert
- Day 25: Urgent alert
- Day 29: Final notice alert
- Day 30: Auto-cancels with reason "Exceso de tiempo en estado DETENIDA"

**Document Validation:**
- PÚBLICO projects must have ≥29 documents before FINALIZADA transition
- Checked via TelcoDrive API integration

### Comunicación Agent

Sends notifications through multiple channels:

**Telegram:**
- Real-time alerts with emoji indicators (⚠️ ✅ 🚨)
- OT status updates
- Crew assignments
- Governance alerts

**Email:**
- HTML formatted messages
- Assignment notifications to technicians
- Governance alerts to project managers
- Error notifications to coordinators

## Use Cases

### UC-PEI-01: Automatic Work Order Ingestion
**Description:** System automatically syncs new work orders from TELCOS API

**Acceptance Criteria:**
- New OTs fetched every 15 minutes (configurable)
- Invalid coordinates flagged and logged
- Duplicates detected and ignored
- Geographic bounds validated (Ecuador only)
- PM notified of ingestion errors

### UC-PEI-02: Intelligent Planning Algorithm
**Description:** System auto-assigns OTs to crews based on 3-phase algorithm

**Acceptance Criteria:**
- Phase 1: Each crew gets 1 OT before any gets 2 (equity)
- Phase 2: Assignments respect 10km distance rule
- Crew capacity never exceeds MAX_CUADRILLA_CAPACITY (20)
- PÚBLICO projects prioritized in Phase 1
- Manual assignment available for edge cases

### UC-PEI-08: Geographic Optimization
**Description:** System calculates crew centroids and optimizes routes nightly

**Acceptance Criteria:**
- Centroid calculated from all assigned OT coordinates
- Route optimization runs at 00:00 UTC daily
- New centroids stored for next day's assignments
- Haversine distance calculated accurately (in km)

### UC-PEI-13: Governance and Auto-Cancellation
**Description:** System enforces business rules and auto-cancels stale OTs

**Acceptance Criteria:**
- 48h in PREPLANIFICADA: Alert sent to Coordinator OPU
- 20d in DETENIDA: Warning alert sent
- 25d in DETENIDA: Urgent alert sent
- 29d in DETENIDA: Final notice sent
- 30d in DETENIDA: Auto-cancellation with audit log
- PÚBLICO projects require 29 documents before FINALIZADA

## Development

### Mock Mode
During development, set `SYSTEM_MODE=MOCK` in `.env` to use simulated data:
- MockApiService returns realistic Ecuador coordinates
- 500ms latency simulation for UI testing
- 95% success / 5% error rate for realistic failure testing
- No external API keys needed

### State Machine
OT statuses follow this flow:
```
PREPLANIFICADA → PLANIFICADA → ASIGNADO_TAREA → DETENIDA ↔ PLANIFICADA
    ↓                ↓              ↓                 ↓
  ANULADA         ANULADA        FINALIZADA        ANULADA

Any status → ANULADA (allowed at any time)
```

### Database Reset
To reset the database during development:
```bash
rm backend/pei.db
python backend/run.py
```

The `init_db()` function runs automatically on startup.

## Testing

### Backend Tests
```bash
cd backend
# Install test dependencies (future task)
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Manual Testing Checklist
- [ ] Drag OT between columns updates status
- [ ] DETENIDA transition shows reason modal
- [ ] PÚBLICO + FINALIZADA validates 29 documents
- [ ] Map shows all OTs and crews
- [ ] Chat responds to planning requests
- [ ] Governance auto-cancels at day 30

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Try different port (update frontend proxy if needed)
python -m uvicorn backend.api.main:app --port 8001
```

### Frontend won't start
```bash
# Clear npm cache
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Database locked
```bash
# SQLite can have locking issues; restart backend
# Stop backend (Ctrl+C)
rm backend/pei.db  # WARNING: deletes all data
python backend/run.py
```

### LLM errors
- Check OPENAI_API_KEY is set correctly
- Verify API key has credits/quota
- Try SYSTEM_MODE=MOCK to bypass LLM calls
- Check API rate limits: `tail -f backend/run.log`

### Telegram notifications not sending
- Verify TELEGRAM_BOT_TOKEN is correct
- Ensure TELEGRAM_CHAT_IDS includes your chat ID
- Check bot has permission to send messages
- Enable background scheduler: uncomment `start_scheduler()` in backend/run.py

### Map markers not showing
- Check browser console for errors
- Verify OTs have valid latitude/longitude
- Try refreshing the map (F5)
- Leaflet CSS must load: check Network tab in DevTools

## License

MIT License - See LICENSE file for details

---

**Built with LangGraph and AI agents for intelligent work order management**

For questions or issues, please open a GitHub issue.
