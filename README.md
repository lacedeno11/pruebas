# DERCAS PEI - Agentic Work Order Management Platform

A cutting-edge agentic platform for intelligent management of work orders (OTs) in the telecommunications industry, built with TypeScript, React, Node.js, and LLM-powered agents.

## Project Overview

DERCAS PEI (Plataforma de Entorno Inteligente) leverages autonomous agents to optimize work order assignment, planning, governance, and communication. The system integrates geographic analysis, intelligent crew scheduling, and real-time monitoring.

## Quick Start

### Installation & Setup

```bash
# Install all dependencies (root level)
npm install

# Configure environment
cp .env.example .env
# Edit .env with your actual values

# Initialize database
cd backend
npx prisma db push
npm run prisma:seed
cd ..

# Start both backend and frontend
npm run dev:all
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:3000
- **Health Check**: http://localhost:3000/health

## Architecture

```
DERCAS PEI
├── Backend (Node.js + TypeScript + Express)
│   ├── Agent System (6 intelligent agents)
│   ├── REST API with validation
│   ├── Prisma ORM + SQLite Database
│   ├── Mock External APIs (TELCOS, TelcoDrive)
│   └── Scheduled Governance Tasks (cron)
│
└── Frontend (React + TypeScript + Vite)
    ├── Drag-Drop Kanban Board (@dnd-kit)
    ├── Geographic Map View (React Leaflet)
    ├── Agent Chat Sidebar (LLM-powered routing)
    ├── React Query (server state)
    └── Zustand (UI state)
```

## Key Features

- **6-Agent System**: Router, OTS, Planning, Governance, Communication agents
- **3-Phase Planning**: Fair distribution → proximity assignment → nightly optimization
- **Geographic Intelligence**: 10km service zones with centroid-based optimization
- **Document Compliance**: 29-document tracking for public projects
- **Auto-Governance**: Time-based alerts and auto-cancellation for inactive OTs
- **Interactive UI**: Real-time Kanban board with drag-drop validation
- **AI Chat**: LLM-powered agent routing and natural language commands

## NPM Workspace Commands

```bash
# Development
npm run dev:all              # Start backend + frontend
npm run dev:backend         # Backend only (port 3000)
npm run dev:frontend        # Frontend only (port 5173)

# Build
npm run build               # Build both projects
npm run build:backend       # Backend only
npm run build:frontend      # Frontend only

# Backend Commands
cd backend
npm run dev                 # Watch mode
npm run build               # TypeScript compilation
npm run prisma:seed         # Populate database
npx prisma migrate dev      # Apply schema changes
```

## Environment Variables

**Required:**
- `OPENAI_API_KEY` - OpenAI API key for LLM features

**Optional (with defaults):**
- `SYSTEM_MODE` - MOCK (development) or PRODUCTION
- `DATABASE_URL` - SQLite path (default: file:./dev.db)
- `PORT` - Backend port (default: 3000)
- `VITE_API_URL` - Frontend API URL (default: http://localhost:3000)
- `TELEGRAM_BOT_TOKEN` - For Telegram notifications
- `SMTP_HOST/USER/PASS` - Email configuration

## Project Structure

### Backend
```
backend/src/
├── agents/          # 6 autonomous agents
├── routes/          # Express API endpoints
├── services/        # External API integration
├── utils/           # Helpers (geo, validation, logging)
├── lib/             # Prisma client singleton
├── jobs/            # Cron jobs (governance)
└── index.ts         # Server entry point
```

### Frontend
```
frontend/src/
├── components/      # React UI components
├── hooks/           # React Query custom hooks
├── services/        # API client (axios)
├── stores/          # Zustand state management
├── types/           # TypeScript interfaces
└── App.tsx          # Root component
```

## Core Workflows

**OT Ingestion** → OTSAgent validates → Create in DB
**Planning** → Phase1 (balance) → Phase2 (proximity) → Phase3 (optimize)
**Governance** → Monitor DETENIDA/PREPLANIFICADA → Alert/Cancel
**Chat** → RouterAgent classifies → Route to appropriate agent

## Technology Stack

**Backend:** Express, Prisma, OpenAI SDK, node-cron, nodemailer, Zod
**Frontend:** React 18, Vite, TanStack Query, Zustand, Leaflet, @dnd-kit, Tailwind CSS

## Troubleshooting

```bash
# Reset database
rm backend/dev.db
cd backend && npx prisma db push && npm run prisma:seed

# Port conflicts
lsof -i :3000 | grep -v COMMAND | awk '{print $2}' | xargs kill -9
lsof -i :5173 | grep -v COMMAND | awk '{print $2}' | xargs kill -9

# Install dependencies
npm install --force
```

---

**Version:** 0.1.0 | **Status:** Development | **License:** Proprietary
