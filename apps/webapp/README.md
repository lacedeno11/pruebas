# WebApp Frontend

React/Vite frontend application for DERCAS-ONCO-XAI V1 platform.

## Features

### 5 Main Panels

1. **Case Selector** - Create and list patient cases
2. **Image Panel** - Upload, process, and view overlays for histopathological images
3. **EHR Panel** - Ingest, extract, and map Electronic Health Records
4. **Graph Panel** - Visualize knowledge graphs with vis-network
5. **Admin Panel** - Manage ontology proposals and publications

## Authentication

- Keycloak OIDC integration with PKCE flow
- Dev mode fallback for development
- Role-based access control (clinician, admin, auditor)

## Technology Stack

- React 18+ with TypeScript
- Vite for build tooling
- Material-UI or similar component library
- vis-network for graph visualization
- Axios for API integration

## Development

```bash
cd apps/webapp
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Environment Variables

See `.env.example` for required configuration.
